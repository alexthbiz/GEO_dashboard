#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_scorer.py
自动打分脚本 —— 对 raw/ 下所有 AI 回答做"原词完全匹配"打分

核心指标：3 个主 GEO tag 组各自命中率
  tag1: 听说先行+拼读进阶（含独家词）
  tag2: 短时高频+螺旋上升
  tag3: 兴趣驱动+学以致用

用法：
    python auto_scorer.py                      # 扫描 raw/ 全部，覆盖写 scoring.csv
    python auto_scorer.py --platform deepseek  # 只打某个平台
    python auto_scorer.py --sample 10          # 抽样校对
"""
from __future__ import annotations
import argparse
import csv
import json
import re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
RAW = ROOT / "raw"
OUT = ROOT / "scoring" / "scoring.csv"

CSV_COLUMNS = [
    "run_id", "date", "platform", "question_id", "question_category",
    "question_text", "trial",
    # 3 个主 GEO tag 组
    "tag1_hit", "tag1_which",   # 听说先行+拼读进阶
    "tag2_hit", "tag2_which",   # 短时高频+螺旋上升
    "tag3_hit", "tag3_which",   # 兴趣驱动+学以致用
    "tags_hit_count",           # 命中的组数（0-3）
    # 品牌
    "brand_mentioned", "brand_position", "brand_method_link",
    # 路径 & 竞品
    "path_explained",
    "competitor_list",
    "raw_path", "notes",
]


def load_rules():
    rules = yaml.safe_load((CONFIG / "scoring_rules.yaml").read_text(encoding="utf-8"))
    questions = yaml.safe_load((CONFIG / "questions.yaml").read_text(encoding="utf-8"))
    q_map = {q["id"]: q for q in questions["questions"]}
    return rules, q_map


def count_hits(text: str, keywords: list[str]) -> list[str]:
    return [kw for kw in keywords if kw in text]


def is_brand_mentioned(text: str, brand_rules: dict) -> bool:
    return any(v in text for v in brand_rules["variants"])


def heuristic_path_explained(text: str, patterns: list[list[str]]) -> int:
    for combo in patterns:
        if all(w in text for w in combo):
            return 1
    return 0


def parse_raw_filename(path: Path) -> dict | None:
    if not path.name.endswith(".md"):
        return None
    m = re.match(r"^([A-Z]\d+)_t(\d+)\.md$", path.name)
    if not m:
        return None
    return {"platform": path.parent.name, "question_id": m.group(1), "trial": int(m.group(2))}


def read_raw(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    meta = {}
    if text.startswith("<!--META:"):
        end = text.find("-->")
        if end > 0:
            try:
                meta = json.loads(text[len("<!--META:"):end].strip())
            except json.JSONDecodeError:
                meta = {}
            text = text[end + 3:].lstrip("\n")
    return meta, text


def score_one(raw_path: Path, rules: dict, q_map: dict) -> dict | None:
    info = parse_raw_filename(raw_path)
    if info is None:
        return None
    meta, body = read_raw(raw_path)
    q = q_map.get(info["question_id"])
    if q is None:
        print(f"[warn] question_id 未找到: {raw_path}")
        return None

    # 3 个主 GEO tag 组打分
    tag_results = {}
    hit_count = 0
    for tag in rules["geo_tags"]:
        hits = count_hits(body, tag["keywords"])
        tag_results[tag["id"]] = hits
        if hits:
            hit_count += 1

    brand = is_brand_mentioned(body, rules["brand_aliases"])

    # 竞品只对路径选择类记录
    comps = count_hits(body, rules["competitors"]) if q["category"] == "path_select" else []

    path_draft = heuristic_path_explained(body, rules["path_explained_patterns"])

    return {
        "run_id": meta.get("run_id", ""),
        "date": meta.get("date", ""),
        "platform": info["platform"],
        "question_id": info["question_id"],
        "question_category": q["category"],
        "question_text": q["prompt"],
        "trial": info["trial"],
        "tag1_hit": int(bool(tag_results.get("tag1"))),
        "tag1_which": "|".join(tag_results.get("tag1", [])),
        "tag2_hit": int(bool(tag_results.get("tag2"))),
        "tag2_which": "|".join(tag_results.get("tag2", [])),
        "tag3_hit": int(bool(tag_results.get("tag3"))),
        "tag3_which": "|".join(tag_results.get("tag3", [])),
        "tags_hit_count": hit_count,
        "brand_mentioned": int(brand),
        "brand_position": "",
        "brand_method_link": "",
        "path_explained": path_draft,
        "competitor_list": "|".join(comps),
        "raw_path": str(raw_path.relative_to(ROOT)),
        "notes": "",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", help="只跑指定平台")
    ap.add_argument("--sample", type=int, help="随机抽样 N 条（校对用）")
    args = ap.parse_args()

    rules, q_map = load_rules()

    scan_root = RAW / args.platform if args.platform else RAW
    files = list(scan_root.rglob("*.md"))

    if args.sample:
        import random; random.seed(42)
        files = random.sample(files, min(args.sample, len(files)))

    rows = [r for f in sorted(files) if (r := score_one(f, rules, q_map))]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fp:
        csv.DictWriter(fp, fieldnames=CSV_COLUMNS).writeheader()
        csv.DictWriter(fp, fieldnames=CSV_COLUMNS).writerows(rows)

    n = len(rows)
    print(f"[ok] 打分完成: {n} 条 -> {OUT.relative_to(ROOT)}")
    if rows:
        t1 = sum(r["tag1_hit"] for r in rows) / n
        t2 = sum(r["tag2_hit"] for r in rows) / n
        t3 = sum(r["tag3_hit"] for r in rows) / n
        any_tag = sum(1 for r in rows if r["tags_hit_count"] > 0) / n
        brand = sum(r["brand_mentioned"] for r in rows) / n
        print(f"     tag1 (听说先行+拼读进阶) 命中率: {t1:.1%}")
        print(f"     tag2 (短时高频+螺旋上升) 命中率: {t2:.1%}")
        print(f"     tag3 (兴趣驱动+学以致用) 命中率: {t3:.1%}")
        print(f"     任一 tag 命中率            : {any_tag:.1%}")
        print(f"     品牌提及率                 : {brand:.1%}")


if __name__ == "__main__":
    main()

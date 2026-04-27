#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
push_weekly_report.py
叽里呱啦 GEO 监控 → 企业微信 Webhook 推送

用法：
    python push_weekly_report.py                  # 推送最新一轮数据
    python push_weekly_report.py --dry-run        # 只打印消息，不发送
    python push_weekly_report.py --label W1       # 指定本轮标签（默认自动）
"""

from __future__ import annotations
import argparse
import csv
import json
import datetime
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=df6b87a2-0711-4433-9bc8-a1f59a302d05"
DASHBOARD_URL = "https://alexthbiz.github.io/GEO_dashboard/"

# T0 基线（2026-04-27）
T0 = {
    "any":    9.5,
    "t1":     2.7,
    "t2":     4.0,
    "t3":     3.8,
    "brand":  13.0,
    "funnel": 16.7,
    "date":   "2026-04-27",
    "n":      630,
}

# T1 目标
T1 = {
    "any":    30.0,
    "t1":     15.0,
    "t2":     15.0,
    "t3":     15.0,
    "brand":  25.0,
    "funnel": 50.0,
}

ROOT = Path(__file__).resolve().parent.parent
SCORING_CSV = ROOT / "baseline_T0" / "scoring" / "scoring.csv"


def load_metrics(csv_path: Path) -> dict:
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    n = len(rows)
    if n == 0:
        return {}

    any_tag = sum(1 for r in rows if int(r["tags_hit_count"]) > 0)
    t1 = sum(int(r["tag1_hit"]) for r in rows)
    t2 = sum(int(r["tag2_hit"]) for r in rows)
    t3 = sum(int(r["tag3_hit"]) for r in rows)
    brand = sum(int(r["brand_mentioned"]) for r in rows)
    tag_rows = [r for r in rows if int(r["tags_hit_count"]) > 0]
    sb = sum(int(r["brand_mentioned"]) for r in tag_rows) if tag_rows else 0

    # 按平台 Tag 命中率
    plat_tag = defaultdict(lambda: [0, 0])
    plat_brand = defaultdict(lambda: [0, 0])
    for r in rows:
        p = r["platform"]
        plat_tag[p][1] += 1
        plat_brand[p][1] += 1
        if int(r["tags_hit_count"]) > 0:
            plat_tag[p][0] += 1
        if int(r["brand_mentioned"]):
            plat_brand[p][0] += 1

    # 找最高/最低 Tag 平台
    plat_tag_rates = {p: h / tot * 100 for p, (h, tot) in plat_tag.items()}
    best_plat = max(plat_tag_rates, key=plat_tag_rates.get)
    worst_plat = min(plat_tag_rates, key=plat_tag_rates.get)

    # 四象限
    s = sum(1 for r in rows if int(r["tags_hit_count"]) > 0 and int(r["brand_mentioned"]) == 1)
    a = sum(1 for r in rows if int(r["tags_hit_count"]) == 0 and int(r["brand_mentioned"]) == 1)
    b_count = sum(1 for r in rows if int(r["tags_hit_count"]) > 0 and int(r["brand_mentioned"]) == 0)

    # 最新日期
    dates = [r["date"] for r in rows if r.get("date")]
    latest_date = max(dates) if dates else datetime.date.today().isoformat()

    return {
        "n":         n,
        "date":      latest_date,
        "any":       round(any_tag / n * 100, 1),
        "t1":        round(t1 / n * 100, 1),
        "t2":        round(t2 / n * 100, 1),
        "t3":        round(t3 / n * 100, 1),
        "brand":     round(brand / n * 100, 1),
        "funnel":    round(sb / len(tag_rows) * 100, 1) if tag_rows else 0.0,
        "s":         s,
        "a":         a,
        "b":         b_count,
        "none":      n - s - a - b_count,
        "best_plat": best_plat,
        "best_rate": round(plat_tag_rates[best_plat], 1),
        "worst_plat": worst_plat,
        "worst_rate": round(plat_tag_rates[worst_plat], 1),
    }


def delta_str(cur: float, base: float) -> str:
    d = round(cur - base, 1)
    if d > 0:
        return f"+{d}pp ↑"
    elif d < 0:
        return f"{d}pp ↓"
    else:
        return "→ 持平"


def traffic_light(cur: float, t1_val: float) -> str:
    pct = cur / t1_val
    if pct >= 0.8:
        return "🟢"
    elif pct >= 0.4:
        return "🟡"
    else:
        return "🔴"


PLAT_LABEL = {
    "deepseek": "DeepSeek",
    "doubao":   "豆包",
    "wenxin":   "文心一言",
    "kimi":     "Kimi",
    "qwen":     "通义千问",
    "zhipu":    "智谱清言",
    "hunyuan":  "混元",
}


def build_markdown(m: dict, label: str) -> str:
    today = datetime.date.today().strftime("%Y-%m-%d")
    best = PLAT_LABEL.get(m["best_plat"], m["best_plat"])
    worst = PLAT_LABEL.get(m["worst_plat"], m["worst_plat"])

    lines = [
        f"## 🧬 叽里呱啦 GEO 周报 · {label}",
        f"> 采集日期：{m['date']}  |  {m['n']} 条 · 7 平台 · 30 题",
        "",
        "**📊 核心指标（对比 T0 基线）**",
        "",
        f"{traffic_light(m['any'], T1['any'])} 任一Tag命中率：**{m['any']}%**  ←T0 {T0['any']}%  `{delta_str(m['any'], T0['any'])}`  目标 {T1['any']}%",
        f"　├ Tag1 听说先行：{m['t1']}%  `{delta_str(m['t1'], T0['t1'])}`",
        f"　├ Tag2 短时高频：{m['t2']}%  `{delta_str(m['t2'], T0['t2'])}`",
        f"　└ Tag3 兴趣驱动：{m['t3']}%  `{delta_str(m['t3'], T0['t3'])}`",
        "",
        f"{traffic_light(m['brand'], T1['brand'])} 品牌提及率：**{m['brand']}%**  ←T0 {T0['brand']}%  `{delta_str(m['brand'], T0['brand'])}`  目标 {T1['brand']}%",
        f"{traffic_light(m['funnel'], T1['funnel'])} 品牌承接率：**{m['funnel']}%**  ←T0 {T0['funnel']}%  `{delta_str(m['funnel'], T0['funnel'])}`  目标 {T1['funnel']}%",
        "",
        "**🗂 四象限分布**",
        f"> S档(品牌+Tag)：**{m['s']}**  |  A档(仅品牌)：{m['a']}  |  B档(仅Tag)：{m['b']}  |  未命中：{m['none']}",
        "",
        "**🏆 平台表现**",
        f"> Tag最高：{best} {m['best_rate']}%  |  Tag最低：{worst} {m['worst_rate']}%",
        "",
        f"[📈 查看完整看板]({DASHBOARD_URL})",
    ]
    return "\n".join(lines)


def send_webhook(text: str, dry_run: bool = False) -> bool:
    payload = {"msgtype": "markdown", "markdown": {"content": text}}
    payload_json = json.dumps(payload, ensure_ascii=False)

    if dry_run:
        print("=== DRY RUN — 消息内容 ===")
        print(text)
        print("=========================")
        return True

    # 用 curl subprocess 避免 SSL 问题
    cmd = [
        "curl", "-s", "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", payload_json,
        WEBHOOK_URL,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    try:
        resp = json.loads(result.stdout)
        if resp.get("errcode") == 0:
            print(f"[ok] 推送成功: {resp}")
            return True
        else:
            print(f"[error] 推送失败: {resp}")
            return False
    except Exception as e:
        print(f"[error] 解析响应失败: {e}\n stdout={result.stdout}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只打印消息不发送")
    ap.add_argument("--label", default="", help="本轮标签，如 W1 / W2（留空自动用日期）")
    ap.add_argument("--csv", default=str(SCORING_CSV), help="scoring.csv 路径")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"[error] 找不到 scoring.csv: {csv_path}")
        sys.exit(1)

    m = load_metrics(csv_path)
    if not m:
        print("[error] scoring.csv 为空")
        sys.exit(1)

    label = args.label or m["date"]
    text = build_markdown(m, label)
    ok = send_webhook(text, dry_run=args.dry_run)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

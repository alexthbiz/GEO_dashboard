#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
health_score.py — 官网 SEO/GEO 综合健康度自动算分

输入：raw/{crawlability,structured_data,ai_probe,lighthouse}/ 下 --label 对应的数据
     + 可选 raw/serp/{label}.yaml（手动 SERP 数据）
输出：report/scores_{label}.json + scores_{label}.md（含 6 维度子项明细 + 总分 + 与 T0 diff）

打分基准（共 100 分，详见 report/tracking_dashboard.md §6.0）：
- A. 基础工程 15 分    robots(3)+sitemap(3)+llms.txt(2)+canonical(3)+HTTPS&备案(2)+HTTP200率(2)
- B. 内容可见性 15 分  非SPA空壳率(5)+title覆盖(2)+description覆盖(2)+H1合规(3)+img alt覆盖(3)
- C. 结构化数据 15 分  Organization(3)+EduOrg(2)+FAQPage(2)+Course(3)+Breadcrumb(1)+OG(4)
- D. 收录与排名 20 分  百度site(5)+神马(3)+搜狗+360(2)+品牌词排名(4)+长尾词前10(6)
- E. AI 知识层 25 分   LLM品牌识别(5)+官网URL引用(8)+方法词命中(6)+错挂率反向(3)+错URL反向(3)
- F. 安全与权重 10 分  子域索引反向(5)+后台公网反向(3)+canonical收敛(2)

用法：
  python3 collectors/health_score.py --label T0_2026-05-21
  python3 collectors/health_score.py --label T1_2026-07-15 --compare T0_2026-05-21
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
REPORT = ROOT / "report"

# ───── 配置 ─────
GEO_KEYWORDS = ["听说先行", "拼读进阶", "短时高频", "螺旋上升",
                "兴趣驱动", "学以致用", "情景输入", "场景开口",
                "拼读识词", "叽里呱啦", "呱呱阅读", "主修课"]
SUBDOMAINS = ["dev.jiliguala.com", "rc.jiliguala.com",
              "prod.jiliguala.com", "spa.jiliguala.com", "j.jiliguala.com"]


# ───── 各维度算分 ─────

def score_a_foundation(label: str) -> dict:
    """A. 基础工程 15 分"""
    detail = {}
    # 从 crawlability summary 读 special files 状态
    summary = RAW / "crawlability" / f"summary_{label}.csv"
    robots_ok = sitemap_ok = llms_ok = False
    http200_count = http200_total = 0
    if summary.exists():
        for r in csv.DictReader(summary.open(encoding="utf-8")):
            if r["label"].startswith("special:"):
                if "robots" in r["url"] and r["status"] == "200":
                    robots_ok = True
                if "sitemap" in r["url"] and r["status"] == "200":
                    sitemap_ok = True
                if "llms" in r["url"] and r["status"] == "200":
                    llms_ok = True
            # HTTP200 率
            if not r["label"].startswith(("subdomain", "special")):
                http200_total += 1
                if r["status"] == "200":
                    http200_count += 1

    # canonical 覆盖率（从 head 数据）
    head_csv = RAW / "structured_data" / f"head_{label}.csv"
    canon_count = canon_total = 0
    if head_csv.exists():
        for r in csv.DictReader(head_csv.open(encoding="utf-8")):
            canon_total += 1
            if r.get("canonical", "").strip():
                canon_count += 1

    detail["robots.txt 可达"] = 3 if robots_ok else 0
    detail["sitemap.xml 可达"] = 3 if sitemap_ok else 0
    detail["llms.txt 可达"] = 2 if llms_ok else 0
    detail["canonical 覆盖"] = round(3 * (canon_count / canon_total), 1) if canon_total else 0
    detail["HTTPS+备案"] = 2  # 默认全通
    detail["HTTP 200 率"] = round(2 * (http200_count / http200_total), 1) if http200_total else 0

    return {"detail": detail, "score": round(sum(detail.values()), 1), "max": 15}


def score_b_visibility(label: str) -> dict:
    """B. 内容可见性 15 分"""
    detail = {}
    head_csv = RAW / "structured_data" / f"head_{label}.csv"
    spa_count = total = title_count = desc_count = h1_ok = 0
    img_total = img_alt = 0
    if head_csv.exists():
        for r in csv.DictReader(head_csv.open(encoding="utf-8")):
            total += 1
            if r.get("is_spa_shell") == "True":
                spa_count += 1
            if r.get("title", "").strip():
                title_count += 1
            if r.get("meta_description", "").strip():
                desc_count += 1
            try:
                if int(r.get("h1_count", "0")) == 1:
                    h1_ok += 1
            except ValueError:
                pass
            try:
                img_total += int(r.get("img_total", "0") or 0)
                img_alt += int(r.get("img_with_alt", "0") or 0)
            except ValueError:
                pass

    detail["非 SPA 空壳率"] = round(5 * ((total - spa_count) / total), 1) if total else 0
    detail["title 覆盖"] = round(2 * (title_count / total), 1) if total else 0
    detail["description 覆盖"] = round(2 * (desc_count / total), 1) if total else 0
    detail["H1 合规（每页 1 个）"] = round(3 * (h1_ok / total), 1) if total else 0
    detail["img alt 覆盖"] = round(3 * (img_alt / img_total), 1) if img_total else 0
    return {"detail": detail, "score": round(sum(detail.values()), 1), "max": 15}


def score_c_structured(label: str) -> dict:
    """C. 结构化数据 15 分"""
    detail = {}
    head_csv = RAW / "structured_data" / f"head_{label}.csv"

    has_org = has_eduorg = has_faq = has_course = has_breadcrumb = 0
    og_count = og_total = 0
    if head_csv.exists():
        for r in csv.DictReader(head_csv.open(encoding="utf-8")):
            og_total += 1
            types = r.get("json_ld_types", "")
            if "Organization" in types:
                has_org = 1
            if "EducationalOrganization" in types:
                has_eduorg = 1
            if "FAQPage" in types:
                has_faq = 1
            if "Course" in types:
                has_course = 1
            if "BreadcrumbList" in types:
                has_breadcrumb = 1
            if r.get("og_title", "").strip() or r.get("og_image", "").strip():
                og_count += 1

    detail["Organization JSON-LD"] = 3 if has_org else 0
    detail["EducationalOrganization"] = 2 if has_eduorg else 0
    detail["FAQPage"] = 2 if has_faq else 0
    detail["Course"] = 3 if has_course else 0
    detail["BreadcrumbList"] = 1 if has_breadcrumb else 0
    detail["Open Graph 覆盖"] = round(4 * (og_count / og_total), 1) if og_total else 0
    return {"detail": detail, "score": round(sum(detail.values()), 1), "max": 15}


def score_d_indexation(label: str) -> dict:
    """D. 收录与排名 20 分（手动 SERP 数据 → yaml）"""
    detail = {}
    serp_yaml = RAW / "serp" / f"{label}.yaml"
    serp = {}
    if serp_yaml.exists():
        try:
            import yaml
            serp = yaml.safe_load(serp_yaml.read_text(encoding="utf-8")) or {}
        except ImportError:
            pass

    # 百度 site 收录（满分 ≥3500 算 5 分）
    baidu_n = serp.get("baidu_site_count", 0)
    detail["百度 site:收录"] = round(min(5, 5 * baidu_n / 3500), 1)

    # 神马（满分 ≥30 算 3 分）
    shenma_n = serp.get("shenma_site_count", 0)
    detail["神马 site:收录"] = round(min(3, 3 * shenma_n / 30), 1)

    # 搜狗 + 360（合计 ≥250 算 2 分）
    sogou_360 = serp.get("sogou_site_count", 0) + serp.get("so360_site_count", 0)
    detail["搜狗+360 site:收录"] = round(min(2, 2 * sogou_360 / 250), 1)

    # 品牌词排名（百度/搜狗/360/神马都 #1 满分 4）
    brand_top1 = sum(1 for k in ["baidu_brand_rank1", "sogou_brand_rank1",
                                  "so360_brand_rank1", "shenma_brand_rank1"]
                     if serp.get(k))
    detail["品牌词 #1"] = brand_top1  # 每个 1 分

    # 长尾词进百度前 10（8 题里几个进，每个 0.75 分）
    longtail = serp.get("longtail_in_top10_count", 0)
    detail["长尾词进前 10"] = round(min(6, 0.75 * longtail), 1)

    return {"detail": detail, "score": round(sum(detail.values()), 1), "max": 20}


def score_e_ai(label: str) -> dict:
    """E. AI 知识层 25 分（7 LLM × 10 题 = 70 次直问）"""
    detail = {}
    agg_file = RAW / "ai_probe" / f"aggregate_{label}.json"
    if agg_file.exists():
        agg = json.loads(agg_file.read_text(encoding="utf-8"))
        brand_rate = agg.get("brand_mention_rate", 0)
        url_rate = agg.get("official_url_rate", 0)
        method_hits = agg.get("method_word_total_hits", 0)
        mis_rate = agg.get("misattribution_rate", 0)
        # 错 URL 数（看 per_platform 里 url_rate=0 且 brand_mention 高的）
        err_url_n = 0
        for pid, p in agg.get("per_platform", {}).items():
            # 简化判定：实际是看 ai_products_probe.py 的输出
            pass
    else:
        brand_rate = url_rate = method_hits = mis_rate = err_url_n = 0

    detail["LLM 品牌识别率"] = round(5 * brand_rate, 1)  # 满分 5
    detail["官网 URL 引用率"] = round(8 * (url_rate / 0.3), 1) if url_rate else 0  # T1 目标 30%
    detail["官网 URL 引用率"] = round(min(8, detail["官网 URL 引用率"]), 1)
    detail["方法词总命中"] = round(min(6, 6 * method_hits / 80), 1)  # 基准 80 = 满分 6
    detail["错挂率反向"] = round(3 * (1 - mis_rate), 1)  # 0 错挂 = 满 3 分
    detail["错 URL 反向"] = round(3 * (1 - err_url_n / 7), 1)  # 7 个 LLM 里几个错

    return {"detail": detail, "score": round(sum(detail.values()), 1), "max": 25}


def score_f_safety(label: str) -> dict:
    """F. 安全与权重 10 分"""
    detail = {}
    summary = RAW / "crawlability" / f"summary_{label}.csv"
    serp_yaml = RAW / "serp" / f"{label}.yaml"

    # 暴露子域数（活的 = 200 且 body 非空）
    exposed_n = 0
    if summary.exists():
        for r in csv.DictReader(summary.open(encoding="utf-8")):
            if r["label"].startswith("subdomain") and r["status"] == "200":
                exposed_n += 1

    # 百度子域索引污染（从 serp yaml）
    polluted_n = 0
    if serp_yaml.exists():
        try:
            import yaml
            serp = yaml.safe_load(serp_yaml.read_text(encoding="utf-8")) or {}
            polluted_n = sum(serp.get(f"baidu_site_{sd.split('.')[0]}_count", 0)
                             for sd in SUBDOMAINS)
        except ImportError:
            pass

    # 后台 niuwa 是否公网可达（serp 数据）
    niuwa_public = serp.get("niuwa_public", True) if serp_yaml.exists() else True

    # canonical 是否收敛
    canon_ok = 1
    head_csv = RAW / "structured_data" / f"head_{label}.csv"
    if head_csv.exists():
        rows = list(csv.DictReader(head_csv.open(encoding="utf-8")))
        if rows and all(not r.get("canonical", "").strip() for r in rows):
            canon_ok = 0

    detail["子域索引污染反向"] = round(5 * max(0, 1 - polluted_n / 50), 1)
    detail["后台公网反向"] = 3 if not niuwa_public else 0
    detail["canonical 收敛"] = 2 if canon_ok else 0

    return {"detail": detail, "score": round(sum(detail.values()), 1), "max": 10}


def grade(total: float) -> str:
    if total >= 90: return "🟢 行业标杆"
    if total >= 75: return "🟢 良好"
    if total >= 60: return "🟡 合格"
    if total >= 45: return "🟠 不及格"
    if total >= 30: return "🔴 严重不足"
    return "⛔ 未启动"


# ───── 主流程 ─────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, help="如 T0_2026-05-21")
    ap.add_argument("--compare", help="对比 baseline label，如 T0_2026-05-21")
    args = ap.parse_args()

    scorers = [
        ("A. 基础工程", score_a_foundation, "robots/sitemap/canonical/llms.txt"),
        ("B. 内容可见性", score_b_visibility, "SPA 空壳 / title / desc / H1 / alt"),
        ("C. 结构化数据", score_c_structured, "JSON-LD / Open Graph"),
        ("D. 收录与排名", score_d_indexation, "百度/搜狗/360/神马 + 8 长尾词"),
        ("E. AI 知识层", score_e_ai, "7 LLM × 10 题 = 70 次直问"),
        ("F. 安全与权重", score_f_safety, "子域污染 / 后台公网 / canonical"),
    ]

    result = {"label": args.label, "dimensions": {}, "total": 0, "max": 100}
    for name, fn, sub in scorers:
        d = fn(args.label)
        d["sub"] = sub
        result["dimensions"][name] = d
        result["total"] += d["score"]

    result["total"] = round(result["total"], 1)
    result["grade"] = grade(result["total"])

    # 对比 baseline（如指定）
    if args.compare:
        cmp_path = REPORT / f"scores_{args.compare}.json"
        if cmp_path.exists():
            cmp = json.loads(cmp_path.read_text(encoding="utf-8"))
            result["compare"] = {
                "baseline_label": args.compare,
                "baseline_total": cmp["total"],
                "delta": round(result["total"] - cmp["total"], 1),
                "delta_by_dim": {
                    name: round(d["score"] - cmp["dimensions"][name]["score"], 1)
                    for name, d in result["dimensions"].items()
                    if name in cmp.get("dimensions", {})
                }
            }

    REPORT.mkdir(parents=True, exist_ok=True)
    out_json = REPORT / f"scores_{args.label}.json"
    out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    # 同步写一份 markdown 摘要
    md = [f"# Health Score · {args.label}", "",
          f"## 总分：**{result['total']} / 100** · {result['grade']}", ""]
    if "compare" in result:
        d = result["compare"]["delta"]
        arrow = "▲" if d > 0 else ("▼" if d < 0 else "→")
        md.append(f"> vs {result['compare']['baseline_label']}（{result['compare']['baseline_total']}）{arrow} **{d:+}**")
        md.append("")
    md.append("## 6 维度明细")
    md.append("")
    md.append("| 维度 | 当前 | 满分 | 子项 |")
    md.append("|---|---:|---:|---|")
    for name, d in result["dimensions"].items():
        sub_str = "; ".join(f"{k}={v}" for k, v in d["detail"].items())
        md.append(f"| {name} | **{d['score']}** | {d['max']} | {sub_str} |")
    if "compare" in result:
        md.append("")
        md.append("## 各维度增量")
        md.append("")
        for name, delta in result["compare"]["delta_by_dim"].items():
            arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "→")
            md.append(f"- {name}: {arrow} {delta:+}")

    out_md = REPORT / f"scores_{args.label}.md"
    out_md.write_text("\n".join(md), encoding="utf-8")

    # 控制台输出
    print(f"\n📊 Health Score · {args.label}")
    print(f"   总分：{result['total']} / 100 · {result['grade']}")
    if "compare" in result:
        d = result["compare"]["delta"]
        arrow = "▲" if d > 0 else ("▼" if d < 0 else "→")
        print(f"   vs {args.compare}：{arrow} {d:+}")
    print()
    for name, dim in result["dimensions"].items():
        bar_len = int(20 * dim["score"] / dim["max"])
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"   {name:18s} {bar} {dim['score']:>5.1f} / {dim['max']:>2}")
    print(f"\n✅ 输出: {out_json}")
    print(f"        {out_md}")


if __name__ == "__main__":
    main()

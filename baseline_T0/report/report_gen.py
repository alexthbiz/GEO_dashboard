#!/usr/bin/env python3
"""
T0 基线报告生成器
读 scoring.csv + yaml 配置 → 输出 baseline_T0_report.md

用法：
    python report/report_gen.py
    python report/report_gen.py --output report/baseline_T1_report.md   # 用于 T1 复测
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent   # baseline_T0/


def pct(n, d):
    return f"{100 * n / d:.1f}%" if d else "—"


def load_config():
    with open(ROOT / "config/scoring_rules.yaml", encoding="utf-8") as f:
        rules = yaml.safe_load(f)
    with open(ROOT / "config/questions.yaml", encoding="utf-8") as f:
        questions = yaml.safe_load(f)["questions"]
    return rules, questions


def section_overview(df, rules):
    """① 聚合指标总览"""
    total = len(df)
    if total == 0:
        return "## ① 聚合指标总览\n\n_无数据_\n"

    t1 = df["tag1_hit"].sum()
    t2 = df["tag2_hit"].sum()
    t3 = df["tag3_hit"].sum()
    any_tag = (df["tags_hit_count"] > 0).sum()
    brand_mentioned = df["brand_mentioned"].sum()
    path_explained = df["path_explained"].sum()

    bp = df["brand_position"]
    bp_valid = bp[bp.notna() & (bp != "")]
    bp_mean = f"{pd.to_numeric(bp_valid, errors='coerce').mean():.2f}" if len(bp_valid) else "待人工补录"

    bml = df["brand_method_link"]
    bml_valid = bml[bml.notna() & (bml != "")]
    bml_rate = pct(pd.to_numeric(bml_valid, errors="coerce").sum(), len(bml_valid)) if len(bml_valid) else "待人工补录"

    lines = [
        "## ① 聚合指标总览",
        "",
        f"**样本总数**：{total} 条（{df['platform'].nunique()} 平台 × {df['question_id'].nunique()} 题）",
        "",
        "| 指标 | 当前值 | 说明 |",
        "|---|---|---|",
        f"| **tag1 命中率**（听说先行+拼读进阶） | {pct(t1, total)} | 组内任一词命中（脚本） |",
        f"| **tag2 命中率**（短时高频+螺旋上升） | {pct(t2, total)} | 组内任一词命中（脚本） |",
        f"| **tag3 命中率**（兴趣驱动+学以致用） | {pct(t3, total)} | 组内任一词命中（脚本） |",
        f"| **任一 tag 命中率** | {pct(any_tag, total)} | 3 组中至少 1 组命中 |",
        f"| **品牌提及率** | {pct(brand_mentioned, total)} | 回答含品牌词（脚本） |",
        f"| **路径解释率** | {pct(path_explained, total)} | 启蒙顺序逻辑完整度（启发式） |",
        f"| **决策引导率** | {bml_rate} | 品牌与方法同段共现（人工） |",
        f"| **品牌关联质量分** | {bp_mean} | brand_position 均值（人工，0–4） |",
        "",
    ]
    return "\n".join(lines)


def section_platform_x_question(df):
    """② 问题 × 平台 热力图（3 tag 组命中率 / 品牌提及率）"""
    if df.empty:
        return ""

    df = df.copy()

    def render(mat, title):
        out = [f"### {title}", "", "| 题目 | " + " | ".join(mat.columns) + " | 行均值 |", "|---|" + "---|" * (len(mat.columns) + 1)]
        for qid, row in mat.iterrows():
            cells = [f"{v*100:.0f}%" if v > 0 else "·" for v in row]
            out.append(f"| {qid} | " + " | ".join(cells) + f" | **{row.mean()*100:.0f}%** |")
        col_mean = mat.mean()
        out.append("| **列均值** | " + " | ".join(f"**{v*100:.0f}%**" for v in col_mean) + f" | **{mat.values.mean()*100:.0f}%** |")
        return "\n".join(out)

    parts = ["## ② 问题 × 平台 热力图\n"]
    tag_labels = [("tags_hit_count", "② a  任一 tag 命中率"), ("brand_mentioned", "② b  品牌提及率")]
    for col, title in tag_labels:
        hm = df.pivot_table(index="question_id", columns="platform", values=col, aggfunc=lambda x: (x > 0).mean()).fillna(0)
        parts.append(render(hm, title))
    return "\n\n".join(parts) + "\n"


def section_tag_ranking(df, rules):
    """③ 3 个主 GEO tag 组命中率 + 组内原词明细"""
    if df.empty:
        return ""
    total = len(df)
    lines = [
        "## ③ 主 GEO Tag 命中率",
        "",
        "| Tag 组 | 组命中率 | 命中条数 | 组内词明细 |",
        "|---|---|---|---|",
    ]
    tag_col_map = {"tag1": ("tag1_hit", "tag1_which"), "tag2": ("tag2_hit", "tag2_which"), "tag3": ("tag3_hit", "tag3_which")}
    for tag in rules["geo_tags"]:
        hit_col, which_col = tag_col_map[tag["id"]]
        hit_n = int(df[hit_col].sum())
        # 各原词出现次数
        word_counts = {}
        for kw in tag["keywords"]:
            n = df[which_col].fillna("").apply(lambda s: kw in str(s).split("|")).sum()
            if n > 0:
                word_counts[kw] = n
        detail = "、".join(f"{k}({v})" for k, v in sorted(word_counts.items(), key=lambda x: -x[1])) or "—"
        lines.append(f"| **{tag['name']}** | {pct(hit_n, total)} | {hit_n} | {detail} |")
    return "\n".join(lines) + "\n"


def section_brand_position_dist(df):
    """④ brand_position 分布"""
    bp = pd.to_numeric(df["brand_position"], errors="coerce").dropna()
    if bp.empty:
        return "## ④ brand_position 分布\n\n_待人工补录后生成_\n"
    dist = bp.value_counts().sort_index()
    lines = [
        "## ④ brand_position 分布",
        "",
        "| 分值 | 含义 | 条数 | 占比 |",
        "|---|---|---|---|",
    ]
    label = {0: "未提及", 1: "列表末", 2: "列表中", 3: "前三", 4: "首推/独推"}
    total = len(bp)
    for v in [0, 1, 2, 3, 4]:
        n = int(dist.get(v, 0))
        lines.append(f"| {v} | {label[v]} | {n} | {pct(n, total)} |")
    return "\n".join(lines) + "\n"


def section_path_vs_competitor(df, rules):
    """⑤ 路径选择 4 题 品牌 vs 竞品提及"""
    ps = df[df["question_category"] == "path_select"].copy()
    if ps.empty:
        return "## ⑤ 路径选择类品牌 vs 竞品\n\n_无 path_select 样本_\n"

    # 竞品归并：同根词合并，如 斑马|斑马英语|斑马AI课 → 斑马
    comp_groups = {
        "斑马": ["斑马", "斑马英语", "斑马AI课"],
        "瓜瓜龙": ["瓜瓜龙", "瓜瓜龙英语"],
        "ABCmouse": ["ABCmouse", "abcmouse", "ABCreading"],
        "伴鱼": ["伴鱼", "伴鱼绘本", "伴鱼英语"],
        "励步": ["励步", "励步英语", "励步启蒙"],
        "VIPKID": ["VIPKID", "vipkid"],
        "鲸鱼": ["鲸鱼外教", "鲸鱼小班"],
        "阿卡索": ["阿卡索"],
        "51Talk": ["51Talk"],
    }

    total = len(ps)
    rows = [("叽里呱啦", int(ps["brand_mentioned"].sum()))]
    for group_name, variants in comp_groups.items():
        hit = ps["competitor_list"].fillna("").apply(
            lambda s: any(v in str(s).split("|") for v in variants)
        ).sum()
        rows.append((group_name, int(hit)))

    rows.sort(key=lambda r: -r[1])
    lines = [
        "## ⑤ 路径选择类 品牌 vs 竞品",
        "",
        f"path_select 样本数：{total} 条",
        "",
        "| 品牌 | 提及条数 | 提及率 |",
        "|---|---|---|",
    ]
    for name, n in rows:
        marker = " 👈" if name == "叽里呱啦" else ""
        lines.append(f"| {name}{marker} | {n} | {pct(n, total)} |")
    return "\n".join(lines) + "\n"


def _read_raw_body(raw_path):
    """读 raw 文件，去掉 META 头返回正文"""
    path = ROOT / raw_path
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    if text.startswith("<!--META:"):
        end = text.find("-->")
        if end > 0:
            text = text[end + 3:].lstrip("\n")
    return text


def _extract_snippet(text, keywords, radius=80):
    """以命中的第一个关键词为中心，取前后 radius 个字符。多命中时按最早出现位置。"""
    if not text or not keywords:
        return ""
    positions = []
    for kw in keywords:
        idx = text.find(kw)
        if idx >= 0:
            positions.append((idx, kw))
    if not positions:
        return ""
    positions.sort()
    idx, kw = positions[0]
    start = max(0, idx - radius)
    end = min(len(text), idx + len(kw) + radius)
    snippet = text[start:end].replace("\n", " ").strip()
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    # 高亮命中词
    for _, k in positions:
        snippet = snippet.replace(k, f"**{k}**")
    return f"{prefix}{snippet}{suffix}"


def _tag_keywords_by_id(rules):
    return {t["id"]: t["keywords"] for t in rules["geo_tags"]}


def section_hit_cases(df, rules):
    """⑧ 曝光案例明细：按"价值密度"分层展示原文片段"""
    if df.empty:
        return ""

    tag_kws = _tag_keywords_by_id(rules)
    brand_kws = rules["brand_aliases"]["variants"]

    # 分层：S=品牌+tag共现，A=仅品牌，B=仅tag
    df = df.copy()
    df["layer"] = "B"
    df.loc[df["brand_mentioned"] == 1, "layer"] = "A"
    df.loc[(df["brand_mentioned"] == 1) & (df["tags_hit_count"] > 0), "layer"] = "S"

    def render_case(r):
        body = _read_raw_body(r["raw_path"])
        # 命中词列表
        hit_words = []
        for tid in ["tag1", "tag2", "tag3"]:
            w = r.get(f"{tid}_which", "")
            if pd.notna(w) and w:
                hit_words.extend(str(w).split("|"))
        if r["brand_mentioned"]:
            hit_words.extend([v for v in brand_kws if v in body])
        # 片段：以品牌词或第一个 tag 词为中心
        center_kws = [v for v in brand_kws if v in body] if r["brand_mentioned"] else hit_words
        snippet = _extract_snippet(body, center_kws, radius=100)
        hits_str = "、".join(sorted(set(hit_words))) or "—"
        return (
            f"- **{r['platform']} / {r['question_id']} / t{r['trial']}**  "
            f"命中：`{hits_str}`\n"
            f"  > {snippet}"
        )

    out = ["## ⑧ 曝光案例明细（带原文片段）", ""]

    # S 档：品牌+tag 共现（最高价值）
    s = df[df["layer"] == "S"].sort_values(["question_id", "platform"])
    out.append(f"### S 档：品牌 + tag 共现（{len(s)} 条）— **最有价值的 GEO 成果**")
    out.append("")
    if len(s) == 0:
        out.append("_无_")
    else:
        for _, r in s.iterrows():
            out.append(render_case(r))
    out.append("")

    # A 档：仅品牌提及
    a = df[df["layer"] == "A"].sort_values(["question_id", "platform"])
    out.append(f"### A 档：仅品牌提及、无 tag 承接（{len(a)} 条）— **品牌出现但方法论缺位**")
    out.append("")
    if len(a) == 0:
        out.append("_无_")
    else:
        for _, r in a.iterrows():
            out.append(render_case(r))
    out.append("")

    # B 档：仅 tag 命中，按 tag 组分组
    b = df[df["layer"] == "B"].sort_values(["question_id", "platform"])
    out.append(f"### B 档：仅 tag 命中、无品牌承接（{len(b)} 条）— **占位成功但品牌承接失败**")
    out.append("")
    for tag in rules["geo_tags"]:
        tid = tag["id"]
        sub = b[b[f"{tid}_hit"] == 1]
        out.append(f"#### {tag['name']}（{len(sub)} 条）")
        out.append("")
        if len(sub) == 0:
            out.append("_无_")
        else:
            for _, r in sub.iterrows():
                out.append(render_case(r))
        out.append("")

    return "\n".join(out) + "\n"


def section_content_grid(questions):
    """⑥ 内容平台占位网格（C 档数据暂缺时返回占位）"""
    path = ROOT / "scoring/manual_content.csv"
    if not path.exists():
        return "## ⑥ 内容平台占位率\n\n_C 档（小红书/抖音/知乎/B 站）数据待人工补录到 `scoring/manual_content.csv`_\n"

    mc = pd.read_csv(path)
    if mc.empty:
        return "## ⑥ 内容平台占位率\n\n_C 档数据为空_\n"

    platforms = ["xhs", "douyin", "zhihu", "bilibili"]
    grid = mc.pivot_table(index="question_id", columns="platform", values="has_brand_content", aggfunc="max").fillna(0)
    lines = [
        "## ⑥ 内容平台占位率",
        "",
        "| 题目 | " + " | ".join(platforms) + " |",
        "|---|" + "---|" * len(platforms),
    ]
    for qid in sorted(grid.index):
        row = [f"{int(grid.loc[qid].get(p, 0))}" for p in platforms]
        lines.append(f"| {qid} | " + " | ".join(row) + " |")
    total = len(grid)
    for p in platforms:
        has = (grid.get(p, 0) > 0).sum() if p in grid.columns else 0
        lines.append(f"- **{p}** 占位率：{pct(has, total)}")
    return "\n".join(lines) + "\n"


def section_platform_ranking(df):
    """额外：平台维度综合排名"""
    if df.empty:
        return ""
    agg = df.groupby("platform").agg(
        samples=("run_id", "count"),
        tag_any=("tags_hit_count", lambda s: (s > 0).mean()),
        tag1=("tag1_hit", "mean"),
        tag2=("tag2_hit", "mean"),
        tag3=("tag3_hit", "mean"),
        brand=("brand_mentioned", "mean"),
        path=("path_explained", "mean"),
    ).reset_index()
    agg = agg.sort_values("tag_any", ascending=False)
    lines = [
        "## ⑦ 平台综合排名",
        "",
        "| 平台 | 样本 | 任一tag | tag1 | tag2 | tag3 | 品牌提及 | 路径解释 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for _, r in agg.iterrows():
        lines.append(f"| {r['platform']} | {r['samples']} | {r['tag_any']*100:.1f}% | {r['tag1']*100:.1f}% | {r['tag2']*100:.1f}% | {r['tag3']*100:.1f}% | {r['brand']*100:.1f}% | {r['path']*100:.1f}% |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(ROOT / "scoring/scoring.csv"))
    ap.add_argument("--output", default=str(ROOT / "report/baseline_T0_report.md"))
    ap.add_argument("--label", default="T0", help="报告标签，如 T0 / T1 / T2")
    args = ap.parse_args()

    df = pd.read_csv(args.input)
    rules, questions = load_config()

    header = [
        f"# 叽里呱啦 GEO 基线测评 {args.label} 报告",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 数据源：`{Path(args.input).name}`（{len(df)} 条样本）",
        f"- 平台范围：{df['platform'].nunique()} 个（A 档 API）+ B 档 / C 档待补",
        f"- 问题范围：{df['question_id'].nunique()} 题",
        "",
        "---",
        "",
    ]

    body = [
        section_overview(df, rules),
        section_platform_x_question(df),
        section_tag_ranking(df, rules),
        section_brand_position_dist(df),
        section_path_vs_competitor(df, rules),
        section_platform_ranking(df),
        section_hit_cases(df, rules),
        section_content_grid(questions),
    ]

    out = "\n".join(header) + "\n\n".join(b for b in body if b)
    Path(args.output).write_text(out, encoding="utf-8")
    print(f"[ok] 报告已生成: {args.output}")
    print(f"     样本 {len(df)} 条 / 平台 {df['platform'].nunique()} 个 / 题目 {df['question_id'].nunique()} 题")


if __name__ == "__main__":
    sys.exit(main())

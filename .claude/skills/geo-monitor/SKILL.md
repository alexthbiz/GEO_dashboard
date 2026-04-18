---
name: geo-monitor
description: 对叽里呱啦品牌的 GEO（生成式引擎优化）效果做定期监控复测。执行采集→打分→生成报告的端到端流程，产出可与历史轮次直接对比的量化数据。用户说"跑 T1/T2 基线"、"做 GEO 复测"、"季度/月度 GEO 监控"、"GEO 现状诊断"时触发。
---

# GEO 监控评测 Skill

叽里呱啦 GEO 基线测评的**标准化复测流程**。每一轮（T0/T1/T2…）都用同一把尺子，结果可直接对比。

## 触发场景

| 场景 | 用户可能的说法 | 跑什么 |
|---|---|---|
| 月度快测 | "跑一下 T1 快测" / "月度监控" | `tier 1` 4 题 × 6 平台 × 3 轮 = 72 条 |
| 季度全量 | "跑 T2 全量基线" / "季度复测" | 21 题 × 6 平台 × 3 轮 = 378 条 |
| 首轮基线 | "做 GEO 现状诊断" | 同全量 |
| 单平台复查 | "只跑 kimi 看下" | 指定 `--platform` |

## 关键路径

- 配置（**只读，不要改**）：`baseline_T0/config/{questions.yaml, scoring_rules.yaml, platforms.yaml}`
- 采集器：`baseline_T0/collectors/api_runner.py`（A 档 6 平台，并行）
- 打分器：`baseline_T0/scoring/auto_scorer.py` → 写到 `scoring/scoring.csv`
- 报告器：`baseline_T0/report/report_gen.py` → 写到 `report/baseline_{LABEL}_report.md`
- 原文存档：`baseline_T0/raw/{platform}/{qid}_t{trial}.md`

## 标准执行流程

### Step 0：环境自检

跑之前先确认 6 个 API key 环境变量都在：

```bash
for k in DEEPSEEK_API_KEY MOONSHOT_API_KEY DASHSCOPE_API_KEY ZHIPUAI_API_KEY ARK_API_KEY QIANFAN_API_KEY; do
  eval "echo $k=\${${k}:-MISSING}"
done
```

如果某个是 MISSING，让用户用 `exec zsh -i -c "..."` 加载 `.zshrc`，或重新配置。
**执行 Python 时必须用** `exec zsh -i -c "python ..."`，否则子进程读不到环境变量。

### Step 1：采集

```bash
cd baseline_T0

# 月度快测
exec zsh -i -c "python -u collectors/api_runner.py --tier 1 --force"

# 季度全量
exec zsh -i -c "python -u collectors/api_runner.py --force"

# 单平台
exec zsh -i -c "python -u collectors/api_runner.py --platform kimi --force"
```

**并行模式下**所有 6 平台同时跑，全量约 5-7 分钟。后台运行，等完成通知。

**关键参数**：
- `--force`：覆盖已有 raw 文件（复测必须加，否则会跳过）
- `--dry-run`：只列计划不调用
- `--tier 1`：只跑 4 核心题
- `--platform <id>`：单平台

### Step 2：打分

```bash
exec zsh -i -c "python scoring/auto_scorer.py"
```

脚本自动完成 7 个字段（tag 匹配、品牌词、竞品列表、路径启发式）。

**人工补录 3 列**（打开 `scoring/scoring.csv`）：
- `brand_position` 0–4（参见 `scoring_rules.yaml.brand_position_rules`）
- `brand_method_link` 0/1（品牌词与 tag 是否同段）
- `path_explained` 脚本已给草稿，需人工复核

如果这一轮不做人工复核，报告里会显示"待人工补录"占位，不影响脚本打分。

### Step 3：生成报告

```bash
# T0 首轮
exec zsh -i -c "python report/report_gen.py --label T0 --output report/baseline_T0_report.md"

# T1 复测
exec zsh -i -c "python report/report_gen.py --label T1 --output report/baseline_T1_report.md"
```

报告包含 7 张视图：
1. 5 大聚合指标总览（方法语义引用率 / 品牌提及率 / 路径解释率 / 决策引导率 / 品牌关联质量分）
2. 问题 × 平台 热力图（tag 命中率 + 品牌提及率）
3. tag 原词出现率排序（9 个原词：5 非独家 + 4 独家）
4. brand_position 分布
5. 路径选择类 品牌 vs 竞品（P1-P4 路径选择题）
6. 内容平台占位率（C 档数据）
7. 平台综合排名

### Step 4（可选）：轮次对比

对比 T1 vs T0 时，把两个报告里的"聚合指标总览"表并列展示，重点标出：
- **上升** → 优化有效
- **持平** → 需继续累积或调整内容策略
- **下降** → 回溯排查（是某个平台变化？还是采集质量问题？）

## 目录约定

**raw 文件不要手动改。** 每轮复测都会 `--force` 覆盖，如需保留历史，先归档整个 `raw/` 到 `raw_T{n-1}/`。

建议每轮前备份：

```bash
cp -r baseline_T0/raw baseline_T0/raw_T0_archive_$(date +%Y%m%d)
cp baseline_T0/scoring/scoring.csv baseline_T0/scoring/scoring_T0_$(date +%Y%m%d).csv
```

## 扩展点

- **B 档平台**（腾讯元宝 / 百度 AI 搜索 / 夸克 AI / 微信搜一搜）：走 `collectors/browser_runner.py` Playwright（尚未落地）
- **C 档内容平台**（小红书 / 抖音 / 知乎 / B 站）：人工采集，按 `collectors/manual_template.md` 填到 `scoring/manual_content.csv`

## 铁律（来自 core_info）

1. **原词完全匹配**：tag 命中严禁语义近似（见 `core_info/GEO_内容创作执行指南.md` 第 2 节）
2. **打分尺不改**：`scoring_rules.yaml` 一旦定了不要动。若必须改，新建 `scoring_rules_v2.yaml` 并在报告标注
3. **单条回答不改**：raw 文件一旦生成不要改内容，便于事后审计
4. **时间戳留痕**：raw 文件 META 有 `date`，复测对比按 date 分组

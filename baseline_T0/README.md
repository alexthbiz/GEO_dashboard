# 叽里呱啦 GEO 基线测评 T0

本目录是 GEO 优化的"**那把尺子**"：固定的问题、固定的打分规则、固定的输出结构，保证 T0（基线）→ T1 → T2 … 每一轮复测数据可直接对比。

---

## 目录结构

```
baseline_T0/
├── README.md                       # 本文件
├── config/
│   ├── questions.yaml              # 20 核心问题（含 tier 分级、category）
│   ├── scoring_rules.yaml          # tag 原词、品牌别名、竞品清单
│   └── platforms.yaml              # 14 平台配置 + 采集参数
├── collectors/
│   ├── api_runner.py               # A 档 6 平台 API 批量调用
│   ├── browser_runner.py           # B 档 Playwright 半自动
│   └── manual_template.md          # C 档人工采集模板
├── raw/{platform_id}/{qid}_t{n}.md # 所有 AI 回答原文留档
├── scoring/
│   ├── auto_scorer.py              # 自动打分（tag 原词匹配）
│   ├── scoring.csv                 # 主打分表（含人工列）
│   └── manual_content.csv          # C 档内容平台占位表
└── report/
    ├── baseline_T0_report.md       # 基线报告（采集完成后生成）
    └── dashboards/                 # 热力图、饼图等
```

---

## 一次完整 T0 跑法

### 0. 环境准备
```bash
cd baseline_T0
pip install openai zhipuai dashscope requests pyyaml playwright pandas
playwright install chromium
```
申请并设置 6 个 A 档 API 的环境变量（详见 `config/platforms.yaml` 中的 `api_key_env` 字段）：
```bash
export ARK_API_KEY=...
export DEEPSEEK_API_KEY=...
export MOONSHOT_API_KEY=...
export ZHIPUAI_API_KEY=...
export DASHSCOPE_API_KEY=...
export QIANFAN_API_KEY=...
```

### 1. 采集（20 题 × 14 平台）

**A 档（6 平台，自动）**
```bash
python collectors/api_runner.py --dry-run          # 先看计划
python collectors/api_runner.py                    # 全量
# 或单平台：python collectors/api_runner.py --platform deepseek
```

**B 档（3 平台 Playwright，首次需登录）**
```bash
python collectors/browser_runner.py --login yuanbao       # 保存登录态
python collectors/browser_runner.py --platform yuanbao    # 采集
# baidu_ai / quark_ai 同理
# wechat_search 走手工
```

**C 档（4 平台，人工）**
按 `collectors/manual_template.md` 流程操作，把结果填到 `scoring/manual_content.csv`，截图放 `raw/{platform}/screenshots/`。

### 2. 打分
```bash
python scoring/auto_scorer.py                      # 生成 scoring.csv
```
CSV 里脚本填了客观字段，**打开 Excel 人工补 3 列**：
- `path_explained`  （0/1，回答是否出现完整"听说先行→拼读进阶"逻辑；脚本给了草稿值，人工复核）
- `brand_position`  （0–4，参见 `scoring_rules.yaml` 中 `brand_position_rules`）
- `brand_method_link`（0/1，品牌词与 tag 是否同段）

抽检 10% 校对脚本：
```bash
python scoring/auto_scorer.py --sample 60
```

### 3. 生成报告
报告生成脚本下个版本补。目前 T0 按 `scoring.csv` 用 Excel/pandas 手动出 6 张视图：
1. 5 大聚合指标总览
2. 问题 × 平台 热力图
3. 6 个非独家 tag 原词的出现率排序
4. brand_position 分布直方图
5. 路径选择 4 题的品牌 vs 竞品提及
6. 内容平台占位网格

存到 `report/baseline_T0_report.md`，未来 T1/T2 用同模板另存。

---

## 每月复测（快测）

```bash
python collectors/api_runner.py --tier 1            # tier 1 的 4 题
# B 档同理加 --tier 1
python scoring/auto_scorer.py
```
预计 150 条样本，半天出结果。

---

## 关键原则

1. **原词完全匹配**：tag 命中严禁语义近似（与 `GEO_内容创作执行指南.md` 第 2 节铁律一致）
2. **单条回答不改**：raw 文件一旦生成不要改内容，便于事后审计
3. **打分尺不改**：`scoring_rules.yaml` 一旦定了不要动；如果确实要改，新建 `scoring_rules_v2.yaml` 并在报告里标注
4. **时间戳留痕**：每个 raw 文件首行 META 里有 `date`，复测对比时按 date 分组即可

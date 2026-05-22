## ⓪ 官网 SEO/GEO 基线专栏 🌐 (Web Channel · T0 = 2026-05-21)

> 频道 B 主入口。完整明细：`../baseline_T0_web/report/tracking_dashboard.md`
> 复测脚本与数据归档：`../baseline_T0_web/`
> ⚠️ 本节由 `report_gen.py` 在生成报告时自动注入，源文件：`report/web_channel_section.md`，独立维护。

### ⓪.1 综合健康度评分

# 🔴 **36.5 / 100** · 严重不足

| 维度 | 权重 | T0 | T1 目标 | 等级 |
|---|---:|---:|---:|---|
| A. 基础工程（robots/sitemap/canonical/llms.txt） | 15 | **4.0** | 13 | 🔴 |
| B. 内容可见性（SPA 空壳 / H1 / alt） | 15 | **9.5** | 12 | 🟠 |
| C. 结构化数据（JSON-LD / OG） | 15 | **0.0** | 12 | ⛔ |
| D. 收录与排名（百度/搜狗/360/神马 + 8 长尾词） | 20 | **8.4** | 12 | 🟠 |
| E. AI 知识层 GEO（7 LLM × 10 题）| 25 | **11.6** | 12 | 🟠 |
| F. 安全与权重（子域污染 / 后台公网） | 10 | **3.0** | 6 | 🔴 |
| **总分** | **100** | **36.5** | **62** | 🔴 → 🟡 |

**等级标尺**：90+ 行业标杆 / 75-89 良好 / 60-74 合格 / 45-59 不及格 / **30-44 严重不足 ← 当前** / <30 未启动

### ⓪.2 T0 → T3 跟踪曲线

| 时点 | 目标分 | 主要动作 |
|---|---:|---|
| T0 2026-05-21 | **32** 🔴 | 基线已固化 |
| T1 第一波 +4 周 | **62** 🟡 | robots/JSON-LD/预渲染/子域 noindex |
| T2 +半年 | **75** 🟢 | 站外内容矩阵铺开，长尾排名进前 10 |
| T3 +一年 | **85** 🟢 | AI 引用率破 30%，方法词稳定占位 |

### ⓪.3 五大量化基线（技术层）

| # | 指标 | T0 | T1 目标 |
|---|---|---|---|
| 1 | SPA 空壳页数 / 总公开页 | 2/6 (mabout, download) | 0/14 |
| 2 | 全站 JSON-LD 实体总数 | **0** | ≥12 |
| 3 | 全站 body 文本 GEO 方法词总命中 | **0** | ≥50 |
| 4 | 暴露的内部子域数 | **5** | 0 |
| 5 | robots.txt + sitemap.xml + llms.txt 可达 | **0/3** | **3/3** |

### ⓪.4 AI 知识层三大基线（7 LLM × 10 题 = 70 次直问 API 自动）

| 指标 | T0 | T1 目标 |
|---|---|---|
| 国内 7 LLM "叽里呱啦"品牌识别率 | **56.7%** (38/67) | ≥80% |
| 国内 7 LLM 官网 URL 引用率 | **6.0%** (4/67) ⚠️ | ≥30% |
| 国内 7 LLM GEO 方法词总命中 | **16** 次 | ≥80 |
| 错挂竞品率 | 0% ✅ | <5% 维持 |
| 错 URL 数（如混元给 jiligua.com） | **1** | **0** |

### ⓪.5 SERP 收录层三大基线（百度浏览器实测 + WebFetch）

| 指标 | T0 | T1 目标 |
|---|---|---|
| 百度 site:jiliguala.com 总收录 | **2,990** | ≥3,500 |
| 神马搜索 jiliguala.com 收录 | **0** ⚠️ | ≥30 |
| 百度子域索引污染(dev+rc+prod+spa+j) | **83 条**（spa 占 75）| **0** |
| 8 个核心长尾词官网进百度前 10 | **0/8** ⚠️ | ≥4/8 |
| 百度 AI 摘要回答"叽里呱啦"含官网 URL | ❌ | ✅ |
| 百度 AI 摘要回答"启蒙 app 哪个好"提到叽里呱啦 | ❌ | ✅ 进前 3 |

### ⓪.6 T0 十大震撼发现（给老板汇报）

1. 🚨 **腾讯混元给出错误官网 URL** `jiligua.com`（缺 la）—— 实体识别错误
2. 🚨 **DeepSeek + 豆包**直接拒答"叽里呱啦官网是哪个" —— 无可靠语料
3. 🚨 通义/文心/混元被问"叽里呱啦是什么" **全部回答"拟声词"** —— 不识别为品牌
4. 🚨 **百度 AI 摘要回答"启蒙 app 哪个好"完全漏掉叽里呱啦** —— 推荐了洪恩/多邻国/斑马/咕噜
5. 🚨 **百度索引 spa.jiliguala.com 75 条 URL** —— 移动 H5 app 子页面被深度抓取
6. 🚨 神马搜索 **0 条**收录 —— 百度+神马垄断 80% 国内移动搜索的另一半完全没占
7. 🚨 **8 个核心长尾问题词官网在百度前 10 全部 0 命中**
8. 🚨 百度搜"叽里呱啦官网"前 10 出现 **4 个不同 URL 入口**（jiliguala.com / spa.jiliguala.com / **t24.jilgl.cn** / 应用宝）—— 实体混乱
9. 🚨 全中文互联网搜"叽里呱啦 听说先行" **0 关联** —— 方法语义和品牌完全脱钩
10. 🚨 全站 body 文本 12 个 GEO 核心词命中 **0 次** —— 官网作为权威锚点 = 0

### ⓪.7 与频道 A（LLM 答题）的联动逻辑

```
官网（频道 B）= AI 引用的"权威锚点"
    ↓
当前锚点 = 空白（GEO 词 0 命中 + JSON-LD 0 + 子域污染 83）
    ↓
导致频道 A 看到的"LLM 答题"质量低（tag 命中率 15.3%、品牌提及率 5%）
    ↓
GEO 改造策略 = 同时改两端
    · 频道 B（官网）做权威锚点 → 第一波 P0+SEC 上线
    · 频道 A（站外）持续生产内容矩阵 → content_ops/ 排期
```

两个频道分数同时上扬，才能证明"GEO 改造投入 → 品牌资产产出"的因果链成立。

### ⓪.8 数据归档与复测命令

```bash
# 频道 B 完整复测（T1/T2/T3）
PY=/Library/Frameworks/Python.framework/Versions/3.11/bin/python3
cd /Users/alex/Projects/GEO_Claude/baseline_T0_web
$PY collectors/crawlability.py --label T1_$(date +%Y-%m-%d)
$PY collectors/structured_data.py --label T1_$(date +%Y-%m-%d)
exec zsh -i -c "$PY collectors/ai_products_probe.py --label T1_$(date +%Y-%m-%d)"
# Lighthouse + 浏览器 SERP（用 Claude in Chrome）参考 tracking_dashboard.md §5 §3
```

完整跟踪表（含 T1/T2/T3 待填列）：`../baseline_T0_web/report/tracking_dashboard.md`
完整 T0 详细报告：`../baseline_T0_web/report/baseline_T0_web_report.md`

---

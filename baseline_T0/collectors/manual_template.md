# C 档内容平台人工采集模板

**适用于：** 小红书 / 抖音 / 知乎 / B站（`platforms.yaml` 里 tier=C 的平台）

**采集规则：**
- 每题 × 每平台搜 1 次（**不**做多轮）
- 记录**搜索结果前 10 条**
- 判断每条是否为「叽里呱啦官号」或「第三方但同时提到叽里呱啦 + 某个 tag 原词」
- 截图存到 `baseline_T0/raw/{platform_id}/screenshots/{question_id}.png`
- 填写下方表格，每个平台复制一份

---

## 填表示例（一个题目一张小表）

### 平台：xhs  |  问题：M1 (3-8岁英语启蒙顺序是什么？)

| 排名 | 标题 | 账号 | 是否叽里呱啦官号 | 正文是否含"叽里呱啦" | 含哪些非独家 tag 原词 | 备注 |
|---|---|---|---|---|---|---|
| 1 | xxx | 某大V | N | N | 听说先行 | — |
| 2 | xxx | 叽里呱啦官方号 | Y | Y | 听说先行 / 拼读进阶 | 置顶帖 |
| … | | | | | | |
| 10 | | | | | | |

**本题占位打分（填入 scoring.csv 补充表）：**
- `has_brand_content` = 0 / 1（前 10 条里是否出现含品牌的内容）
- `has_official_account` = 0 / 1
- `top3_account_list` = ["账号1", "账号2", "账号3"]

---

## 合并汇总表（manual_content.csv）

采集完 20 题 × 4 平台后，请把以上每张小表的「占位打分」汇总到一张 CSV：

```
platform,question_id,has_brand_content,has_official_account,top3_accounts,notes
xhs,M1,1,1,"叽里呱啦官方|宝妈X|英语老师Y",置顶是官方号
xhs,M2,0,0,"...",前10条没有品牌出现
...
```

路径：`baseline_T0/scoring/manual_content.csv`

---

## 采集提示（加速技巧）

1. 使用各平台的**无痕/隐身模式**，减少个性化推荐干扰
2. 搜索词使用 `questions.yaml` 里的 `prompt` **原词**
3. 知乎按"综合排序"，小红书按"最热"（默认），抖音按"综合"，B站按"综合排序"
4. 如前 10 条已出现 3 条以上叽里呱啦相关，可在 `notes` 标注「强占位」
5. 搜索时间：尽量 20 题集中 1 天内完成，减少算法推荐漂移

---

## 平台搜索快捷链接（填入 prompt 即可使用）

- 小红书: `https://www.xiaohongshu.com/search_result?keyword={prompt}`
- 抖音: `https://www.douyin.com/search/{prompt}`
- 知乎: `https://www.zhihu.com/search?q={prompt}&type=content`
- B站: `https://search.bilibili.com/all?keyword={prompt}`

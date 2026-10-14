# V1.2 Human Story 验收

最新 Story Mining 阶段另见 [V1.3 验收](STORY_MINING_ACCEPTANCE.md)。本文件保留 V1.2 的历史运行记录。

本记录由 scripts/write_acceptance.py 读取实际 run report、JSON 与 manifest 生成。内部验收材料含真实来源；日常摘要与公开简报另行检查平台名。没有自动发布，也没有伪造人工审美反馈。

## 本地真实完整链

运行时间：2026-10-14T07:24:38.274496+00:00。

| 指标 | 实际数量 |
|---|---|
| Raw | 232 |
| 本轮去重 | 227 |
| Stage A | 38 |
| Stage B | 10 |
| Deep | 1 |
| Human Review Queue | 0 |
| Deep packets / public briefs | 1 / 1 |
| Human Review packets | 0 |

本轮 Editorial live/cache：0/38；Human Trigger live/cache：0/38。缓存只复用完全一致的来源证据和问题定义。

## 当前真实 Deep：1 条

| Rank | Editorial | Human Trigger | Viral | Strongest Trigger | Human Title Seed |
|---|---|---|---|---|---|
| 1 | 59.73 | 50.91 | 49.67 | identity + fear_loss | 单个案例待核：每天盯着流量做内容的人，还能靠访问量判断有没有人看吗？ |

### 1. 场景、身份与标题

claim_scope：single_case；semantic_status：assessed；Human gate：B。

读者身份：每天看流量、经营网站或独立作品的创作者（读者代入假设，不代表国内已发生）

Concrete Scene（来源原句）：

```json
{
  "who": "I posted to HN, and then my website was flooded with AI bot traffic",
  "where": "my website was flooded with AI bot traffic",
  "action": "I posted to HN",
  "unexpected_result": "my website was flooded with AI bot traffic",
  "human_consequence": "my website was flooded with AI bot traffic"
}
```

Reversal：NONE；原文没有充分给出期待与结果的两段对照，不补造期待。

三个不同角度的调查标题：

- scene [single_case]：单个案例待核：发布一条内容后，网站多出来的访问来自哪里？
- reversal [single_case]：单个案例待核：访问量涨了，真实读者却未必变多：这些访问来自哪里？
- identity_interest [single_case]：单个案例待核：每天盯着流量做内容的人，还能靠访问量判断有没有人看吗？

自然讨论入口：个人经历（是假设入口，不是已取得评论）。

## 冻结真实候选回测：8 条

使用 fixtures 中保存的真实原始标题、必要摘录、链接、时间与来源，不补写人物经历。算法中没有这些标题/品牌的得分分支。

| 原始题目 | Editorial | Human | Viral | 场景 | Gate | 降级原因 |
|---|---|---|---|---|---|---|
| Google DeepMind and Singapore Government announce new AI tool to protect citizens against scams | 55.6 | 15.5 | 29.55 | False | NONE | NO_STORY, LOW_HUMAN_TRIGGER |
| Epic Games reportedly pivoting to "AI first" game development model | 61.98 | 17.69 | 33.09 | False | NONE | LOW_HUMAN_TRIGGER |
| I posted to HN, and then my website was flooded with AI bot traffic | 60.08 | 50.91 | 49.77 | True | B | 无 |
| Pluto Security raises $42M as AI gives enterprise security teams a new headache | 59.14 | 16.88 | 32.09 | False | NONE | LOW_HUMAN_TRIGGER |
| Disney offers $20M for Character.AI’s scandal-plagued chatbot tech | 49.73 | 14.39 | 27.18 | False | NONE | LOW_HUMAN_TRIGGER |
| Science Corporation implants its vision-restoring chip in its first Stargardt disease patient | 46.77 | 16.9 | 27.86 | False | NONE | LOW_HUMAN_TRIGGER |
| Facebook is giving users more control over their algorithm | 47.08 | 10.6 | 25.05 | False | NONE | LOW_HUMAN_TRIGGER |
| Higgsfield takes AI video from 1 minute to over 10 | 49.17 | 11.87 | 25.1 | False | NONE | LOW_HUMAN_TRIGGER |

机器人流量明显高于没有具体员工经历的 B2B 安全融资材料。高编辑价值不再保证进入 Deep；官方防诈、AI-first、交易、医疗、推荐控制与视频长度仍需具体人、实际行为和后果，不能把标题扩写成已经发生的故事。

## 合成测试样本的真实语义回测

以下是显式标注的测试文本，不是新闻，不入生产库。pytest 的受控判断只验证组合逻辑；这里另外调用实际语义服务。

| Fixture | Human | 预期 | 实际门槛 |
|---|---|---|---|
| fixture-parameter | 3.83 | low | LOW_HUMAN_TRIGGER |
| fixture-investment | 4.19 | low | LOW_HUMAN_TRIGGER |
| fixture-funding | 2.71 | low | LOW_HUMAN_TRIGGER |
| fixture-api | 4.78 | low | LOW_HUMAN_TRIGGER |
| fixture-junior | 78.54 | high | A |
| fixture-bot | 73.97 | high | A |

回测脚本自动断言四个负样本 <30、两个强样本 ≥65，且机器人场景高于无具体人的 B2B 材料；语义不完整则失败，不报告通过。

## 测试与一致性

- pytest：103 passed。ruff check / format --check 通过。
- 覆盖触发加分、无场景降级、正负样本、范围与标题约束、不同标题角度、读者代入、评论路由、缺key/超时/陈旧判断清除、人工队列和数量篡改。
- LIKE / MAYBE / DISLIKE 及新旧 reason codes 兼容；未把任何自动判断写成人工标签。
- verify-outputs 读取真实文件，验证标题数量、表格行、JSON、候选身份、packet、公开简报、别名页与 run report；任一不一致失败。
- 本地审稿摘要与全部 public briefs 通过禁止平台名与 Show 海外 / Ask 海外 / 海外 post 机械表达检查；原始专名只保留在内部证据。

## GitHub Actions 与实际 artifact

[完整手动 workflow / checks 与采集通过](https://github.com/wanggenAi/xiaohongshu-content-engine/actions/runs/38530788846)。已下载该 run artifact 并独立读取、核对文件。

| Cloud raw | Stage A | Stage B | Deep | Human Review Queue | Review packets |
|---|---|---|---|---|---|
| 232 | 38 | 0 | 0 | 10 | 10 |

artifact 内 editorial_review.md 含实际候选、原始证据包链接和明确状态，verify-outputs 通过。
本次云端未取得语义判断：队列全部标记 NEEDS_HUMAN_REVIEW / semantic_status=unavailable，Human/Viral=null。实际验证无 API 仍产生可读候选，不宣称云端完成语义筛选，也没有转移本地凭证。

## 实际限制

当前真实 Deep 只有 1 条，数量与 JSON、Markdown、manifest、证据包一致，不为了得到四个故事而补齐。现有来源多为短摘录/标题，部分高价值新闻尚不能支撑人的具体经历；此层会把缺失显式暴露给编辑。

尚无独立交叉核验、真实评论采集或中文饱和度审计。情绪与受众是明确标注的调查假设，Viral Potential 不等于确定会爆。

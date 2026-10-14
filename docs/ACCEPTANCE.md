# V1.1 选题质量验收 — 2026-10-14（Asia/Shanghai）

本记录对应仓库 `main` 的 V1.1 实现。没有自动发布小红书，也没有把语义判断写成事实。

## 真实运行

- 采集：raw **232**，本轮保守去重 **227**；数据库现存 **234**，全部去重后 **229**。
- Stage A Discovery：**37**（来源上限只用于覆盖面）。
- Stage B Editorial Screening：**17**。
- Deep Candidates：**8**；没有为了凑数补入内容。
- Editorial Packets / public briefs：**8 / 8**。
- TypeSafe 请求：live **1**、cache **36**；token 使用记录在 `run_report.json`，凭证未写入日志或输出。
- `pytest`：59 passed；`ruff check` 与 `ruff format --check` 通过。
- 公开简报全部通过平台名检查，未发现 `Show 海外`、`Ask 海外`、`海外 post` 等机械替换。

启用来源审计：

| 来源 | 状态 | 条数 | 原因 |
|---|---|---:|---|
| hacker_news | ok | 60 |  |
| github_search | ok | 15 |  |
| github_releases | ok | 9 |  |
| openai_blog | ok | 20 |  |
| deepmind_blog | ok | 20 |  |
| google_ai_blog | ok | 20 |  |
| microsoft_ai_blog | ok | 10 |  |
| meta_ai_blog | skip | 0 | Publisher RSS returned 404; use manual URLs until a stable official feed/API is verified. |
| nvidia_blog | ok | 18 |  |
| huggingface_blog | ok | 20 |  |
| techcrunch | ok | 20 |  |
| ars_technica | ok | 20 |  |
| anthropic_blog | skip | 0 | No configured stable publisher RSS/API; use manual URLs until one is verified. |
| telegram | skip | 0 | missing TELEGRAM_BOT_TOKEN |
| manual_inbox | empty | 0 |  |

主要入口是 [editorial_review.md](../outputs/editorial_review.md)，只含 Deep Candidates、编辑价值分数、Verdict、中文 title seed、Core Story、Why It Matters、缺证据和调查问题。

## 当前真实 Top 8

1. **71.94 / POSSIBLE** — Google DeepMind：AI能帮我们识别诈骗，但它需要看到多少私人对话？
2. **65.80 / POSSIBLE** — Epic Games：当创作流程开始要求AI优先，手写代码和手工美术会放在什么位置？
3. **62.92 / POSSIBLE** — 看起来访问量涨了，来的却可能是机器人：创作者该怎么算真实关注？
4. **62.60 / POSSIBLE** — Pluto Security：把AI交给每个人使用之后，公司最难管理的会是什么？
5. **62.07 / POSSIBLE** — Disney：陪伴型聊天产品进入商业合作时，谁来承担关系与安全的责任？
6. **60.30 / POSSIBLE** — Science Corporation：辅助技术走到了具体患者身上：它究竟能恢复哪些日常能力？

这些都是 `POSSIBLE`，没有候选达到 `STRONG` 门槛。它们是调查候选，不是已核实事实或最终文案；编辑页逐条保留作者、时间、摘录、原始 URL、证据缺口和不确定性。

## 冻结的 V1 Top 20 回测

旧排序（同一份 `data/v1_top20_snapshot.json`）：

| 旧排名 | discovery score | 标题 |
|---:|---:|---|
| 1 | 47.17 | Science Corporation implants its vision-restoring chip in its first Stargardt disease patient |
| 2 | 45.51 | Facebook is giving users more control over their algorithm |
| 3 | 44.40 | Show HN: Parsimony – an open-source benchmark for how much code AI models add |
| 4 | 43.96 | Launch HN: Consus (YC F24) – LLM gateway for companies handling sensitive data |
| 5 | 43.60 | Pluto Security raises $42M as AI gives enterprise security teams a new headache |
| 6 | 43.45 | I posted to HN, and then my website was flooded with AI bot traffic |
| 7 | 42.58 | We turned EmbeddingGemma 2 into a speech-to-text model |
| 8 | 42.25 | I built a tool to track what AI leaders say and how their views change on video |
| 9 | 41.11 | NVIDIA Announces New Investments in France’s Startups |
| 10 | 39.69 | All Systems Go: Global PC App Ecosystem Ready for NVIDIA RTX Spark |
| 11 | 35.80 | Google DeepMind and Singapore Government announce new AI tool to protect citizens against scams |
| 12 | 32.52 | Disney offers $20M for Character.AI’s scandal-plagued chatbot tech |
| 13 | 32.10 | Industrial Next wants factory robots to switch tasks in minutes, not weeks |
| 14 | 30.64 | Flox Intelligence is building AI to keep wildlife away from trains, airports, and roads |
| 15 | 30.11 | Gemini 4 Argon begins rolling out in Gemini app and Antigravity, but only if you pay |
| 16 | 30.07 | Epic Games reportedly pivoting to "AI first" game development model |
| 17 | 29.68 | Higgsfield takes AI video from 1 minute to over 10 |
| 18 | 25.90 | NVIDIA, Microsoft Kick Off a New Beginning for Windows PCs With RTX Spark and AI Agents |
| 19 | 25.62 | Martin Shkreli livestreamed himself violating lifetime pharma ban, FTC says |
| 20 | 24.20 | Gemini 4 Argon: Built to solve your hardest problems |

V1.1 新排序（同一批内容先走 Stage A，再经过语义筛选；Deep 上限 10）：

| 新排名 | Verdict | editorial score | editorial title seed |
|---:|---|---:|---|
| 1 | POSSIBLE | 71.94 | Google DeepMind：AI能帮我们识别诈骗，但它需要看到多少私人对话？ |
| 2 | POSSIBLE | 65.80 | Epic Games：当创作流程开始要求AI优先，手写代码和手工美术会放在什么位置？ |
| 3 | POSSIBLE | 62.92 | 看起来访问量涨了，来的却可能是机器人：创作者该怎么算真实关注？ |
| 4 | POSSIBLE | 62.60 | Pluto Security：把AI交给每个人使用之后，公司最难管理的会是什么？ |
| 5 | POSSIBLE | 62.07 | Disney：陪伴型聊天产品进入商业合作时，谁来承担关系与安全的责任？ |
| 6 | POSSIBLE | 60.30 | Science Corporation：辅助技术走到了具体患者身上：它究竟能恢复哪些日常能力？ |

- **明显降级/剔除：** 普通 LLM gateway、NVIDIA 普通投资、NVIDIA PC 生态宣传、Embedding 模型转换被 `NO_HUMAN_ANGLE`、`PR_ONLY`、`LOW_CHINA_RELEVANCE`、`BORING` 等原因拦截；原本高 discovery 分数不能绕过编辑门槛。
- **进入前列：** 防诈骗与隐私、AI 优先创作流程、机器人流量、工作场景的 AI 安全风险、陪伴型聊天产品的责任、具体患者辅助技术。它们分别有可调查的安全取舍、工作变化、异常流量、关系/责任或具体人物入口；并没有因为“AI”一词自动加分。
- **被保留但仍待核实：** Facebook 推荐控制、视频长度提升等具备受众入口，但证据、效果和中国适用性仍不足，所以是 `POSSIBLE` 而非 `STRONG`。
- 冻结回测数量：Stage A **20**、Stage B **9**、Deep **6**。

## 反馈与限制

人工审美反馈表和 CLI 已落地：`review add` 接收 `LIKE` / `MAYBE` / `DISLIKE` 与 reason，写入 SQLite。当前仓库没有真实的五条人工 DISLIKE 记录，因此没有伪造人工标签；后续应由 ChatGPT/用户对 Deep Candidates 逐条补录。

当前仍没有自动评论采集、中文覆盖审计、独立事实交叉核验或真实发布表现。没有 `TYPESAFE_API_KEY` 时，候选会标记 `awaiting_review`，不会被假装成 Deep Candidate；GitHub Actions 已加入可选同名 secret。

下一步最值得做：对这 8 条 Deep Candidates 补充原始页面核验、独立报道和真实不同观点，再由 ChatGPT 标注 LIKE/MAYBE/DISLIKE；只有之后才调整权重。

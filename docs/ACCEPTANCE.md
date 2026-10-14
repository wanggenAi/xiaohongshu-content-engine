# V1 真实数据验收 — 2026-10-14（Asia/Shanghai）

运行时间：2026-10-14T03:57:55.738216+00:00（UTC）；采集真实公开 API/RSS。没有生成或自动发布小红书最终文章。

- 本轮 raw items：232；本轮去重：227。
- 当前数据库存储：234；数据库去重后：229（包含此前运行仍有效的条目）。
- Top candidates：20；内部 Editorial Packets：20。
- 公开候选简报：20；全部通过平台名检查。内部数据库/packets 保留真实来源。
- pytest：30 passed；ruff check 与 ruff format --check 通过。
- GitHub Actions：[push CI](https://github.com/wanggenAi/xiaohongshu-content-engine/actions/runs/38509076828) 与 [完整采集验收](https://github.com/wanggenAi/xiaohongshu-content-engine/actions/runs/38509095330) 均 success。
- 已下载并检查线上 artifact：从空数据状态采集 232 条、去重后 227 条，Top 20、20 份内部素材包和 20 份通过检查的公开简报；各启用来源均 ok，Telegram/受限 adapter 正常 skip。线上运行时间 2026-10-14 12:00（Asia/Shanghai）。

## 来源审计

| 来源 | 状态 | 本轮条数 | 跳过/错误原因 |
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

## Top 20 与评分

| # | 分数 | 类型初筛 | 标题 | 内部来源 |
|---|---:|---|---|---|
| 1 | 47.17 | HUMAN_AI_STORY | Science Corporation implants its vision-restoring chip in its first Stargardt disease patient | [techcrunch](https://techcrunch.com/2026/10/13/science-corporation-implants-its-vision-restoring-chip-in-its-first-stargardt-disease-patient/) |
| 2 | 45.51 | INTERESTING_INTERNET | Facebook is giving users more control over their algorithm | [techcrunch](https://techcrunch.com/2026/10/13/facebook-is-giving-users-more-control-over-their-algorithm/) |
| 3 | 44.40 | AI_PRODUCT | Show HN: Parsimony – an open-source benchmark for how much code AI models add | [hacker_news](https://parsimony.lasu.dev/) |
| 4 | 43.96 | AI_PRODUCT | Launch HN: Consus (YC F24) – LLM gateway for companies handling sensitive data | [hacker_news](https://news.ycombinator.com/item?id=50073471) |
| 5 | 43.60 | TECH_SHIFT | Pluto Security raises $42M as AI gives enterprise security teams a new headache | [techcrunch](https://techcrunch.com/2026/10/13/pluto-security-raises-42m-as-ai-gives-enterprise-security-teams-a-new-headache/) |
| 6 | 43.45 | TECH_SHIFT | I posted to HN, and then my website was flooded with AI bot traffic | [hacker_news](https://www.sammystraus.com/) |
| 7 | 42.58 | AI_PRODUCT | We turned EmbeddingGemma 2 into a speech-to-text model | [hacker_news](https://eg2.haku.sh/) |
| 8 | 42.25 | DEVELOPER_STORY | I built a tool to track what AI leaders say and how their views change on video | [hacker_news](https://blumify.io/people) |
| 9 | 41.11 | BUSINESS_SIGNAL | NVIDIA Announces New Investments in France’s Startups | [nvidia_blog](https://blogs.nvidia.com/blog/france-ecosystem-agentic-computing/) |
| 10 | 39.69 | INTERESTING_INTERNET | All Systems Go: Global PC App Ecosystem Ready for NVIDIA RTX Spark | [nvidia_blog](https://blogs.nvidia.com/blog/local-ai-rtx-spark-laptops-software-updates/) |
| 11 | 35.80 | TECH_SHIFT | Google DeepMind and Singapore Government announce new AI tool to protect citizens against scams | [deepmind_blog](https://deepmind.google/blog/on-device-ai-scam-detection-mddi/) |
| 12 | 32.52 | TECH_SHIFT | Disney offers $20M for Character.AI’s scandal-plagued chatbot tech | [ars_technica](https://arstechnica.com/tech-policy/2026/10/disney-offers-20m-for-character-ais-scandal-plagued-chatbot-tech/) |
| 13 | 32.10 | TECH_SHIFT | Industrial Next wants factory robots to switch tasks in minutes, not weeks | [techcrunch](https://techcrunch.com/2026/10/13/industrial-next-wants-factory-robots-to-switch-tasks-in-minutes-not-weeks/) |
| 14 | 30.64 | TECH_SHIFT | Flox Intelligence is building AI to keep wildlife away from trains, airports, and roads | [techcrunch](https://techcrunch.com/2026/10/13/flox-intelligence-is-building-ai-to-keep-wildlife-away-from-trains-airports-and-roads/) |
| 15 | 30.11 | INTERESTING_INTERNET | Gemini 4 Argon begins rolling out in Gemini app and Antigravity, but only if you pay | [ars_technica](https://arstechnica.com/ai/2026/10/gemini-4-argon-begins-rolling-out-in-gemini-app-and-antigravity-but-only-if-you-pay/) |
| 16 | 30.07 | AI_PRODUCT | Epic Games reportedly pivoting to "AI first" game development model | [ars_technica](https://arstechnica.com/gaming/2026/10/report-epic-games-goes-all-in-on-ai-for-disney-collaboration/) |
| 17 | 29.68 | TECH_SHIFT | Higgsfield takes AI video from 1 minute to over 10 | [openai_blog](https://openai.com/index/higgsfield-longer-videos-voice) |
| 18 | 25.90 | AI_PRODUCT | NVIDIA, Microsoft Kick Off a New Beginning for Windows PCs With RTX Spark and AI Agents | [nvidia_blog](https://blogs.nvidia.com/blog/local-ai-rtx-spark-microsoft-windows-event/) |
| 19 | 25.62 | INTERESTING_INTERNET | Martin Shkreli livestreamed himself violating lifetime pharma ban, FTC says | [ars_technica](https://arstechnica.com/health/2026/10/martin-shkreli-livestreamed-himself-violating-lifetime-pharma-ban-ftc-says/) |
| 20 | 24.20 | INTERESTING_INTERNET | Gemini 4 Argon: Built to solve your hardest problems | [google_ai_blog](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-argon/) |


## 证据包

至少 5 份实际生成的内部素材包留在 [samples/2026-10-14](samples/2026-10-14) 供代码审查。
本地完整 20 份在 outputs/editorial/2026-10-14；日常数据、SQLite 和输出不提交 Git。

## 当前限制

Telegram 自动消息未配置 token/频道，真实状态是 skip；人工入口与 Bot API 的白名单、消息编辑、偏移持久化、保护内容、缺凭证和失败隔离已通过测试。自动源需配置后再做消息接收验收，不声称已采集 Telegram 真实消息。

Meta 与 Anthropic 暂为 restricted adapter，通过人工链接补充。没有评论抓取、独立交叉核验、中文报道饱和度或可靠增长速度。公开输出是编辑候选简报，不是已审核的最终稿。所有工程分数只用于初筛；不得把标题/摘要当成已核实事实。数据反馈结构与录入 CLI 已落地，尚未积累真实发布反馈。

下一步最值得做：请 ChatGPT 对这 20 个候选逐条标注想发/不想发和原因，确认真实中国受众价值后再调整权重、配额及来源。

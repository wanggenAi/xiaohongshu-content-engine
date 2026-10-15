# xiaohongshu-content-engine

> 当前选题目标：每天帮中国用户找到海外 AI、科技、互联网世界最值得点开的东西。Story Mining 只是六条赛道之一。
>
> **禁止 Best-of-Bad-Batch。** Deep Candidate 不代表允许发布。先跑 `uv run python -m xhs_content_engine publish-candidates`，查看 `outputs/publish_candidates.md`，再用 `check-publish-gate CANDIDATE_ID` 检查全部绝对门槛。没有合格题就 `NO_PUBLISH_TODAY`。本次纠正没有发布新帖，也没有删除原帖。
>
> 多赛道、热点主动搜索、公开 Telegram、人物监控、真实 DISLIKE 与闸门说明见 [CONTENT_SELECTION_V2.md](docs/CONTENT_SELECTION_V2.md)。

V1.5沿用六赛道主线，加入可解释Stop Scroll、claim边界、20标题赛马、真实互动参照库和Blind Top 5。当前修正轮只生成内部候选报告，禁止自动发布。


持续发现海外 AI、科技、人物观点、工作变化和互联网讨论，生成供 ChatGPT 与用户判断的高质量候选素材。工程初筛不替代最终编辑判断，不自动发布小红书。

`SOURCE → COLLECT → NORMALIZE → DEDUPE → DISCOVERY → STORY MINING → EVIDENCE → HUMAN TRIGGER → EDITORIAL PACKET`

## 使用

Python 3.12，建议在仓库根目录使用 uv：

```bash
uv sync --python 3.12 --extra dev
uv run python -m xhs_content_engine collect
uv run python -m xhs_content_engine rank --limit 20
uv run python -m xhs_content_engine export --limit 20
uv run python -m xhs_content_engine run --limit 20
uv run python -m xhs_content_engine inbox add 'https://example.com/story' \
  --title '实际标题' --note '必要短摘录' --published-at '2026-10-14T08:00:00+08:00'
uv run python -m xhs_content_engine check-public /absolute/path/to/draft.md
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

也可 `python3.12 -m venv .venv`，激活后 `pip install -e '.[dev]'`，直接运行 `python -m xhs_content_engine run`。`--root` 可指定包含 `config/` 的目录；数据和输出写入该目录。需要审核最终稿时主动运行 `check-public`；项目不连接发布平台。

## 内容源

- Hacker News 官方 Firebase API：标题、短摘录、讨论 URL、作者、发布时间和公开 points/comments。Story Search 使用公开搜索索引查询配置中的经历组合，并用官方 API 读取有限的 ranked comments 与回复；不抓外部文章全文，不推测评论共识或争议程度。
- 个人博客/创作者 RSS：Simon Willison、Armin Ronacher、Ethan Mollick 的公开 publisher feeds，标为 Tier S。普通产品更新仍须满足人物、行动和实际结果门槛。
- GitHub 官方 API：最近 30 天创建的 AI 仓库按 stars 排序，以及配置中仓库的 releases。stars 是快照，不宣称 fast-growing；未抓 trending HTML。无 token 尝试公开 API，有 `GITHUB_TOKEN` 时使用，超限隔离。
- 公司官方 RSS：OpenAI、DeepMind、Google AI、Microsoft 官方博客、NVIDIA、Hugging Face；媒体 RSS：TechCrunch、Ars Technica。链接和条目可能失效，逐源记录 error/empty，不绕过限制。
- Anthropic、Meta AI：保留 restricted adapter；前者尚无已验证稳定配置，后者 RSS 实测 404，通过 Manual Inbox 录入。
- Manual URL Inbox：接受任意 HTTP(S) 内容链接，用户可补充真实标题、时间和必要摘录。不访问需登录的平台；URL-only 记录不假装已取得正文。
- Telegram：人工消息链接 + 官方 Bot API 可选接入。需专用 bot、授权加入的公开频道白名单和 token。见 [接入方法与边界](docs/TELEGRAM.md)。

增加 RSS 只需修改 `config/sources.yaml`。受限来源可以配置 `type: restricted_adapter` 和 skip reason；未来合法 API 的 collector 注册到 `ADAPTERS` 即可，不影响现有来源。


## Human Story funnel（V1.3）

`STORY-RICH SOURCES → Fast Story Filter（≤50）→ Story Mining Semantic Pass → Candidates（≤20 进入后续语义）→ Human Trigger / Editorial → Deep（≤10）`

三个分数分开保留：Discovery 判断素材是否值得进入候选池；Editorial 判断内容价值；Human Trigger 判断真实事件的人性张力。最终排序采用 `viral_potential = human × 0.55 + editorial × 0.30 + evidence_quality × 0.15`（evidence 换算为 0–100）。这是内部排序信号，不承诺爆款。

`config/human_triggers.yaml` 配置十个触发维度、证据门槛、可追溯加分与场景/评论缺失降级。场景和反转只选取来源片段；没有具体故事时，不由 AI、公司名、融资额或技术参数自动加分。详见 [Human Trigger 规则](docs/HUMAN_TRIGGERS.md)。

## Story Mining（V1.3）

V1.3 在复杂语义判断前增加 `config/story_mining.yaml` 的确定性 Fast Story Filter，优先处理 30～50 条有本地故事信号的素材。轻量 Story Mining 再选来源片段，验证真实个人经历、实际结果、前后变化和冲突；不足证据进人工队列。只有满足人物＋行动＋结果且 Story Richness ≥40 的记录才成为 `StoryCandidate`，最多 20 条进入现有 Human/Editorial 语义。来源权威度不再控制 Story Mining 的准入，分别记录 `source_authority` 与 `story_value`。

`story_richness_score` 描述故事原料，`fallback_story_score` 只控制成本和人工队列顺序，绝不冒充 Human Trigger。评论来源保留作者、URL、父回复与必要摘录；独立字段只从一个选定的个人叙述中选取，不能拼接甲的行动与乙的后果。受限平台进入 restricted adapter 或 Manual Inbox。多个明确不同作者的案例可以标为 `multiple_cases`，不能自动称为趋势。

`outputs/story_candidates.json` 保存完整有证据候选，`story_candidates.md` 展示最多十条及证据缺口；`editorial_review.md` 顶部区分 Assessed Stories 与 Human Review Queue，并显示 Person、Action、Result、Before/After、Conflict、Claim Scope、Evidence Status。查询组合和普通读者身份分别配置在 `story_mining.yaml` 与 `reader_identities.yaml`。测试集包含 30 条明确标注的合成示例和 8 条冻结真实素材。

有 `TYPESAFE_API_KEY` 时，各语义阶段按完整来源证据和问题定义缓存。Story Mining 不可用时直接输出 `NEEDS_HUMAN_REVIEW` 队列，跳过复杂 Human/Editorial 请求，Human/Viral 分数为 null。如果整批都被降级且没有 Deep，也保留带原降级原因的人工复核素材；无来源材料时保留采集错误审计。

日常入口为 `outputs/editorial_review.md`：顶部 Today’s Human Stories 显示排名、三个编辑信号、最强触发器和具体读者身份；每条 Deep 包含场景、反转、讨论入口和三个不同角度的调查标题。原文、真实平台与证据保留在内部 packet；审稿摘要和公开简报通过平台名/机械替换检查。

```bash
uv run python scripts/backtest_human.py  # 八个冻结真实素材 + 六个明确标注的合成测试样本
uv run python -m xhs_content_engine verify-outputs
uv run python -m xhs_content_engine review add feedback.json
```

反馈继续兼容 LIKE / MAYBE / DISLIKE，增加 strong_reversal、strong_identity、strong_scene、strong_money、strong_job_angle、strong_fear、strong_desire、strong_fairness、too_news_like、no_human_tension、no_scene 等 reasons；旧 reasons 也保留。不自动训练，不伪造人工标签。

[验收记录](docs/ACCEPTANCE.md)对应真实运行。日常数据和输出仍不入 Git；Actions artifacts 保存完整队列与证据包。导出后自动检查 Markdown 标题、表格、JSON、packet、public briefs 和 run report 的数量与候选身份；工作流再独立运行 verify-outputs。

## 输出与持久化

- `data/content.sqlite3`：统一 ContentItem、Manual Inbox、Telegram cursor 和 content_performance。
- `outputs/collection_audit.json` / `run_report.json`：每个来源的状态、原始数量、存储数量、去重数量及错误原因。
- `outputs/top_candidates.md` / `.json`：Human Stories 审稿页别名 / Deep 完整候选对象（最多 10 条）。
- `outputs/story_candidates.json`：Story Mining 提取的原料、来源证据、故事类型、聚类和独立案例。
- `outputs/human_review_queue.json` 与 `human_review/YYYY-MM-DD/*.md`：按 Fallback Story Score 排序、明确状态的人工队列及原始证据。
- `outputs/export_manifest.json`：当前导出数量，供数量一致性检查。
- `outputs/editorial/YYYY-MM-DD/*.md`：内部证据包（Asia/Shanghai 日期）。真实来源、全部去重 provenance、不同事实核实问题、3 个编辑角度、风险和版权说明。
- `outputs/public_briefs/YYYY-MM-DD/*.md`：来源泛化且经检查的公开候选简报。不是最终文案，也不自动翻译或编造文章。

`collect` 本身完成 normalization 并 upsert，`rank` 去重、评分、排序，`export` 使用当下排名输出。`run` 串起完整流程。canonical URL + 长标题精确匹配进行保守去重，合并后保存全部来源和原始互动快照。未知发布时间保留但不默认入 Top；未来时间排除。旧闻超过 7 天默认排除，数据库自动清理 30 天未再采集的非人工记录；每源每次读取有上限。

评分配置：`config/scoring.yaml`，七维权重 25/15/20/15/10/5/10。输出每维、命中关键词、权重贡献、扣分和未知项。对重复只选一个代表，不再给重复本身额外扣分；重复、广告、标题党、中文已饱和、参数升级、来源不明、版权风险等显式 flags 可触发对应 penalty。规则初筛的 novelty/relevance 不代表已验证的新颖性或中国受众价值，中文报道饱和度和事实独立核验留给编辑。

编辑规则：`config/editorial_style.yaml` 和 [编辑哲学](docs/EDITORIAL_PHILOSOPHY.md)。内部数据绝不隐藏真实来源；公开候选文本禁用平台品牌名（包括 Telegram）。不保存第三方全文、不默认拥有图像/视频转载权、不伪造共识。全流程只处理链接和必要摘录。

## 发布反馈

创建 JSON 记录后运行：

```bash
uv run python -m xhs_content_engine performance add /absolute/path/to/performance.json
```

记录包含 `id`, `published_at`, `topic`, `content_type`, `title`, `internal_source`, `public_source_label` 和 `views/likes/saves/comments/shares/follows`，以及 `metrics_2h`, `metrics_24h`, `metrics_72h`（指标字典）。样例见 [performance-example.json](docs/performance-example.json)。目前只存储真实反馈，不训练或宣称优化了推荐。

## GitHub Actions

Content Engine workflow：push/PR 跑 pytest 与 ruff；每天 UTC 00:17、03:17…每 3 小时和手动触发跑完整流程。GitHub 调度可能延迟。没有 Telegram secret 时跳过；单个来源挂掉不阻断。所有来源都失败时仍输出审计和空候选，必须看 `run_report.json` 判断采集质量，工作流绿灯只证明流程执行成功。

SQLite 通过 Actions cache 跨运行恢复，候选与审计通过 artifacts 保存 14 天，不提交日常数据到 Git，不无限膨胀仓库。cache 不是永久数据库备份，可能被驱逐；本地 inbox 和数据库不会自动同步到云端，长期运行建议持久化 SQLite 于自己的主机。不要把私密原文或密钥放入公开素材配置或 artifacts。

## 当前限制与下一步

系统只处理合法公开摘录，不绕过登录、验证码、robots 或私人数据；没有合法评论数据时不会把评论数量写成观点。不做独立交叉核验、中文饱和度检测或历史增长估计，不自动生成最终文案。来源健康状态和真实数据验收见 [验收记录](docs/ACCEPTANCE.md)。下一步：由 ChatGPT/用户对 Story Candidates 标注真实审美反馈，并补足原作者记录、实际行为变化和核验材料。

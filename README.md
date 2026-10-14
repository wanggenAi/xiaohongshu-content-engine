# xiaohongshu-content-engine

持续发现海外 AI、科技、人物观点、工作变化和互联网讨论，生成供 ChatGPT 与用户判断的高质量候选素材。工程初筛不替代最终编辑判断，不自动发布小红书。

`SOURCE → COLLECT → NORMALIZE → DEDUPE → SCORE → RANK → EDITORIAL PACKET`

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

- Hacker News 官方 Firebase API：标题、短摘录、讨论 URL、作者、发布时间和公开 points/comments；不抓评论或外部文章正文。
- GitHub 官方 API：最近 30 天创建的 AI 仓库按 stars 排序，以及配置中仓库的 releases。stars 是快照，不宣称 fast-growing；未抓 trending HTML。无 token 尝试公开 API，有 `GITHUB_TOKEN` 时使用，超限隔离。
- 公司官方 RSS：OpenAI、DeepMind、Google AI、Microsoft 官方博客、NVIDIA、Hugging Face；媒体 RSS：TechCrunch、Ars Technica。链接和条目可能失效，逐源记录 error/empty，不绕过限制。
- Anthropic、Meta AI：保留 restricted adapter；前者尚无已验证稳定配置，后者 RSS 实测 404，通过 Manual Inbox 录入。
- Manual URL Inbox：接受任意 HTTP(S) 内容链接，用户可补充真实标题、时间和必要摘录。不访问需登录的平台；URL-only 记录不假装已取得正文。
- Telegram：人工消息链接 + 官方 Bot API 可选接入。需专用 bot、授权加入的公开频道白名单和 token。见 [接入方法与边界](docs/TELEGRAM.md)。

增加 RSS 只需修改 `config/sources.yaml`。受限来源可以配置 `type: restricted_adapter` 和 skip reason；未来合法 API 的 collector 注册到 `ADAPTERS` 即可，不影响现有来源。


## Editorial quality funnel (V1.1)

Each run preserves the original `discovery_score` and adds a separate semantic `editorial_score`. The bounded funnel is:

`RAW → Stage A Discovery (up to 40, source caps) → Stage B Editorial Screening (up to 20) → Deep Candidates (up to 10)`.

Stage A uses the existing deterministic discovery score. Stage B uses seven independently described dimensions: human relevance, curiosity gap, story strength, discussion potential, China audience relevance, novelty and evidence quality. Hard rejects include `TOO_TECHNICAL`, `PR_ONLY`, `MINOR_UPDATE`, `NO_HUMAN_ANGLE`, `NO_STORY`, `LOW_CHINA_RELEVANCE`, `SATURATED`, `WEAK_EVIDENCE` and `BORING`. `SATURATED` is only accepted with an actual Chinese-coverage audit; missing evidence is not treated as proof of an information gap.

When `TYPESAFE_API_KEY` is present, a bounded structured judgment evaluates only Stage A and is cached by exact evidence plus rubric. The provider receives source text as quoted, untrusted evidence and cannot write final copy. If the key is absent or the provider fails, candidates stay `awaiting_review` and do not enter Deep Candidates. The workflow accepts an optional repository secret of the same name.

The primary daily entry is `outputs/editorial_review.md`. It contains only Deep Candidates with `STRONG`, `POSSIBLE`, `WEAK` or `REJECT`, a Chinese editorial title seed, concrete core story, why it may work/fail, story signals copied from evidence, missing evidence, investigation questions, ten deep-candidate fields and specific angles. The page is a research brief, not a final post. Human feedback can be stored with `python -m xhs_content_engine review add feedback.json`, using `LIKE`, `MAYBE` or `DISLIKE` plus reasons.

`docs/ACCEPTANCE.md` records the V1.1 backtest and live run. `outputs/v1_vs_v11_backtest.json` is a local generated comparison of the frozen V1 Top 20; daily SQLite/output artifacts remain ignored.

## 输出与持久化

- `data/content.sqlite3`：统一 ContentItem、Manual Inbox、Telegram cursor 和 content_performance。
- `outputs/collection_audit.json` / `run_report.json`：每个来源的状态、原始数量、存储数量、去重数量及错误原因。
- `outputs/top_candidates.md` / `.json`：内部 Top 20 标题、得分、来源和完整候选对象。
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

V1 不抓评论、不做独立交叉核验、中文饱和度检测或历史增长估计，不自动生成最终文案。来源健康状态和首次真实数据验收见 [验收记录](docs/ACCEPTANCE.md)。最值得做的下一步：让 ChatGPT 对 Top 20 标出想发/不想发及原因，再据此调整评分和来源配额，避免仅凭工程关键词提高“新闻感”。

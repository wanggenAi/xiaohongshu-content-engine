# V1.6 — 中国普通人为什么点

普通人评分：钱、工作、关系、隐私、惊讶中最强的真实触发占45%，生活关联25%，具体人物/处境冲突15%，具体事件15%。不要求每条内容同时有钱、关系和惊讶，知名品牌不单独加分。另有零背景惊讶路径：惊讶70% + 具体事件20% + 去术语后兴趣10%；普通人分取两条路径的较高值，让纯视觉/WTF不因缺少个人利益或人物故事而被封死。

最终分：Ordinary Person Appeal 32%，独立3秒卡片Stop Strength 22%，最强Human Trigger 15%，Personal Relevance 12%，Story/Conflict 7%，核验视觉6%，有证据的中国信息差3%，实际Source Heat 3%。Evidence Fitness仅形成事实适配闸门，不贡献吸引力分。旧Mass、Viral Similarity与科技重要性保留作背景审计。

去科技词测试展示删除后的文本，评判不知道这些词还能否觉得有意思；低于60为FAIL。首页3秒请求仅含标题+封面，返回STOP/MAYBE/SCROLL及强度；不能看来源、原文、技术意义或算法分数。标题变更后重新判断实际卡片。普通人点击理由从有边界的事实包中选择，允许NONE，不凭空生成恐慌和收益。理由挑选是另一独立请求，吸引力/事实评分的请求不包含这些编辑理由，避免解释写得好反过来抬分。没有泛泛好奇心兜底句。

合格Top 5：事实/范围/安全/编造/标题/封面均PASS，普通人吸引力至少60，去术语PASS，有具体点击理由，3秒不能SCROLL或UNKNOWN。合格不足5条则盲排不可完成且禁止自动成稿。多样性只在合格候选内、分差不超过3时为重复超过2条的触发方向找新方向；保护第一名，不用差题凑类型。

自动资格继续要求最终分至少75、普通人吸引力至少70、卡片强度至少70、3秒STOP、事实硬闸门全过、标题潜力和标题强度至少70，且原有新鲜度、20候选、独立盲排、标题Tournament、DISLIKE等门槛成立。证据足够不等于推荐发布。70–74.99编辑审核，其余未达条件仅研究/审核或NO_PUBLISH。阈值是未获真实CTR校准的编辑规则，模型偏好不是用户行为证明。

来源支持检验覆盖实际标题与封面。曾被否决的其他标题不会覆盖候选的事实边界；Tournament不能用高偏好分绕过标题事实闸门。每次换标题需要重评该卡，最多收敛3轮；仍变化则标UNKNOWN、禁止自动发布。证据已通过的无聊题仍可淘汰；标题未知的好题可留作核验，但不进合格Top 5。

以下V1.5内容保留为历史说明；与V1.6冲突以以上规则和当前代码为准。

# 多赛道竞争与绝对发布闸门

本轮只修系统和跑候选，未发布、未删除任何小红书内容。

## V1.5 当前实现

V1.4多赛道、Mass Appeal、Human Trigger、Viral保持主线；下面的10月14日记录是历史审计。V1.5只校准软闸门、证据适配、标题和爆帖参照，不降低75总门槛。

- 硬闸门为Evidence、Scope、Safety、Fabrication及最终标题claim。E0无来源、E1匿名/未验证转述不能自动发；E2可信有归因报道、E3原始/官方来源、E4一手加已核验独立交叉来源。URL数量不等于E4。E3足够报道公司宣布，不能自动证明用户效果。
- `max_publishable_claim`从已读事实包或完整原句取得。Evidence Fitness判断来源是否支持这个claim；Scope检查该claim有没有把可能说成已经、指控说成定罪，而非要求一句话复述原文所有限制。硬失败为NO_PUBLISH，未知为待审。
- Stop Scroll的六个0–100维度权重为25/20/20/15/10/10；两种独立评估视角分别判断，再取均值并保存原始输出。75以上显示PASS、60–74显示BORDERLINE、60以下FAIL；发布质量线仍按用户要求70。差异超过25的软项需要复核。同一模型的两次评估不是不同模型的独立验证。
- Non-tech、Programmer Bias、负模式匹配各有正确方向的等级描述。分数分布集中于相邻等级时不会因为confidence偏低直接否决；低端和高端同时有显著概率的双峰分布需要复核。
- Topic Strength保留原Publishability供回测；Headline Strength是具体标题强度。Title Potential衡量事实支持的标题机会。一个临时标题弱不等于题差；确定捏造的标题不参与潜力加分，待核验的标题不准用于发布。
- 标题由事实包中的编辑备选和事实钩子组合产生，缺少事实不会凭空补20条。十类标题结构按实际分类，不硬造不存在的名人/数字/利益。榜首20标题做190对比较，输出Top 5；点击偏好和claim核验分开，最终必须选择事实通过且强度至少70的标题。
- 首页Blind Top 5另起请求，只包含洗牌后的标题、封面一句话和受众；不传来源、分数、算法排名。算法第一落到盲排4/5时暂停自动资格并暴露冲突。它是模型编辑偏好测试，不是实测用户点击率。
- Viral Reference Library持久化到`data/viral_references.jsonl`，按真实平台指标入库，保留30天；当前采样用最近7天，用户DISLIKE永不进入Positive Reference。没有取得的views/likes/shares/增长窗口保持null。传播结构和why-it-worked是待回测假设，不冒充互动因果。
- 评估服务不可用时保留历史已学习结构及其原观测时间，新互动另存一条观测；不能用不可用结果清空历史学习，也不能将旧结构冒充新一次语义评估。
- Viral Pattern Similarity比较结构标签，按多个不同事件聚合，不比较文本。只有知名实体这一项不能匹配；少于3个结构参照最高60。不能用一条名人爆帖推导某人物永久加分。负模式相似另给`NEGATIVE_PATTERN_MATCH`警告，用户反馈有否决权。
- Visual Asset Strength只认有URL和核验时间的素材。100要求核验过关键动作的原始视频，80为相关官方图片/演示，60为可据事实制作的信息图，20为文字卡。仿真演示不能冒充实机7连中视频。
- 每次主动搜索分别检查24h、72h、7d。超过72h的候选要有近期观测到的强热度或已记录国内信息差才能留在发布竞争池。原始发布日期不因重新核验而更新。

最终优先级权重：Mass .30、Viral .15、Stop .15、Title Potential .10、Social Heat .10、Viral Similarity .10、Evidence Fitness .05、Visual .05。Mass仍最大；视觉权重从建议公式中的Viral分出5%，并未提高Human Trigger权重。未知热度显示null，计算不加热度信用。硬证据失败的线索留在审计池，不占据有证据候选的优先位置。

AUTO资格要求所有硬闸门通过；Mass≥70、Stop≥70、Title Potential≥70、具体标题强度≥70、Final Priority≥75；Viral≥60，或实测Heat≥80，或结构Similarity≥80且大众入口≥75；非技术入口、无强程序员偏见；至少20个实评不同事件；扫描≤6h；完成榜首标题赛马和首页盲测。70–74.99为EDITOR_REVIEW_REQUIRED；低于60、硬失败或用户DISLIKE为NO_PUBLISH。其他不完整条件为REVIEW_ONLY。AUTO资格不是本轮发布授权，本轮仍禁止发布。

本轮真实数据和校准结果见`docs/selection_runs/2026-10-15/`。输出包含`publish_candidates.md/json`、`viral_reference_report.md`、`viral_reference_library.json`、`blind_top5.md/json`及永久DISLIKE回放。

## 已核对的真实状态与失败根因

开始修改前，远端 main 与本地 HEAD 均为 `64446964ecc600f0d79fb0f88a10c85fc96ebc25`。最新有输出 artifact 的 Actions 是 [38565125461](https://github.com/wanggenAi/xiaohongshu-content-engine/actions/runs/38565125461)，artifact ID `11895160566`，创建于 2026-10-14 12:37:41 UTC，运行提交为 `f0744a7`；之后的 push 检查没有新候选 artifact。该云端运行的 Story Fast Filter 为50，Story Candidate为0，待评50。不能把这份无语义评分的云端 artifact 当成后来本地的8个 Story Candidates。

最近真实发布记录是《他的网站变慢了，来的却未必是读者》，2026-10-14 21:14 +08:00，Story Richness 60，Human Trigger 38.52，Viral Potential 39.58。[已发布笔记](https://www.xiaohongshu.com/explore/6acf8021000000001303f32e)及原始发布账本保留。开始修正时，本地最新 Story Mining 为378条原始输入、50条快速筛选、8个语义 Story Candidates、1个Deep Candidate。

它被选中的原因是：旧流程先以人物、行动、结果和故事完整度限制入口，再在这8条里寻找较易解释、可以补证据的题；人工把这一批的相对第一当成发布理由。没有大众兴趣绝对门槛，没有至少20个跨赛道题的竞争，官方重大变化也可能因为不是故事或被归为普通公司新闻而提早退出。核验一个小网站的真实遭遇，只证明事情发生了，并不证明普通中国用户有点击欲望。

用户原话“一点都不吸引人。”已存为正式 DISLIKE，写入 `data/editorial_feedback.jsonl` 并同步反馈数据库。七个原因有正式定义。新语义判断读取真实负例；同一原始事件关联原candidate ID，不能通过换source ID逃开。每次竞争输出 `negative_training_replay.json`，旧候选明确 NO_PUBLISH，不虚构它没有测过的 Mass Appeal。

## 实现

- `content_lanes.yaml` 定义六条赛道，人物故事没有全局优先权。旧 `source_priority.yaml` 的 S/A/B/C 只影响 Story Mining。
- `hot_scan.py` 主动执行8类新闻搜索、8位人物搜索、公开讨论搜索、官方RSS和公开Telegram页面采集。新闻先24h，空结果扩到72h、7d。搜索命中只是线索，搜索摘录和未核验转述不能作为发布证据。
- `watch_people.yaml` 保存人物及检查范围。查询成功、出现名字，不等于有实质性可发事件。
- `telegram_channels.yaml` 配置本次公开搜索确认可读的 `aipost`，不是冒充用户给过的名单，也不是官方事实源。历史附件没有具体频道URL。支持公开频道、单条公开post URL、Manual URL Inbox。无需bot token；旧bot通道改为可选禁用。拒绝私群、邀请链接、服务地址、重定向或登录页面；不下载频道专有媒体，不绕登录或验证码。
- `publish_selection.py` 在最近7天输入中合并同一事件，保留每条赛道的检索机会，最多实评40条；至少20个实际取得语义判断的不同候选才能放行。不是把20条重复报道或未评分线索凑成20个题。
- Mass Appeal使用8项固定权重。各维度有自己的评分等级；计算和硬规则在代码，语义强度由TypeSafe Score判断。Viral/Human不依赖第一人称或Story Richness。平台互动使用真实取得的指标分别标准化，未知保持null；国内传播没有对照检索时信息差最多3.5/10。
- Stop Scroll、妈妈测试、程序员偏见、证据、标题分别判断。HOT_NEWS与PURE_NEWS另作判断，不因为是公司公告就自动降为普通新闻。
- 榜首的20个标题单独盲测：请求只包含标题和普通读者设定，不含来源、事实包、候选分数。这是编辑判断，未冒充真实用户点击实验。

`docs/live_scans/2026-10-14.json` 保存本次公开阅读后的事实摘要、中文入口、限制和真实来源；部分条目明确仍是待核验线索。常规采集可自动发现新题，准备发布时仍需为新题补核验与中文入口，不能拿一个英文新闻标题直接发布。旧证据包超过7天会退出竞争，不冒充当天新题。

## V1.4 历史发布闸门与运行

Mass Appeal ≥70；Viral ≥60或实测Social Heat ≥85；Stop Scroll、Non-tech、Evidence、Title PASS；程序员偏见检查通过；评分与赛道判断有足够置信度；Publishability ≥75；至少20个已评不同候选；主动扫描不超过6小时；没有用户DISLIKE；最终有20标题盲测。任何条件缺失都不会AUTO。

Publishability <60或未知为NO_PUBLISH；60以上但缺少硬条件为REVIEW_ONLY。75不是绕过其他条件的通行证。研究Deep榜和文案校验不代表发布资格。本项目这轮没有执行发帖工具。

```sh
uv run python -m xhs_content_engine run
uv run python -m xhs_content_engine publish-candidates
uv run python -m xhs_content_engine verify-publish-candidates
uv run python -m xhs_content_engine check-publish-gate CANDIDATE_ID
```

`publish-candidates --reuse-scan`可复核同一批证据，过期扫描仍会被拦。输入公开Telegram URL可用 `inbox add https://t.me/aipost/POST_ID`，或编辑公开频道配置。

输出 `outputs/publish_candidates.md/json` 包含Top20、Top10、所有实评候选、各项分数、停留理由、证据状态、中文标题、每项失败原因、人物与Telegram审计。Actions常规run也执行新竞争及输出校验，summary改为新榜单。云端缺少TypeSafe凭证时评分显示UNKNOWN，安全停在NO_PUBLISH，不沿用旧故事第一名来发帖。

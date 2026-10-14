# 多赛道竞争与绝对发布闸门

本轮只修系统和跑候选，未发布、未删除任何小红书内容。

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

## 发布闸门与运行

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

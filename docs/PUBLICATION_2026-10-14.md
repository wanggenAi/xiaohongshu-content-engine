# 首次真实发布记录

已完成公开发布，已发布列表中存在该笔记，并打开实际笔记详情核验。没有把成功提交等同于平台推荐承诺。

- 标题：他的网站变慢了，来的却未必是读者
- 帖子：https://www.xiaohongshu.com/explore/6acf8021000000001303f32e
- 平台显示发布时间：2026-10-14 21:14（Asia/Shanghai，精度为分钟）
- 候选：story-457a1ac27774d000c352270a；Story Richness 60；Human Trigger 38.52；Viral Potential 39.58。这些内部信号不是流量预测。
- 发布前 main：84f2f3a48047114837af17b9dad17f97865f21f3；最新 Actions 38565523597 成功；已读取当日 Story Candidates、编辑总览、人工队列及相应证据包。
- 四张 1200×1600 原创 Pillow 信息卡；手机预览顺序 01→02→03→04，未搬运原作者图片或截图。
- 当前发布页面限制：标题20字（本标题16字）；正文1000字（实际页面323，含平台话题计算）。
- 五个实际话题：ai、人工智能、独立开发、互联网、内容创作。
- 已选择平台“笔记含AI合成内容”声明；取消话题自动关联的无关活动。
- 真正发布记录：data/published_posts.jsonl；实际页面凭证留在本机 outputs/publication/2026-10-14/published-note.png，未将浏览器账户页面提交到公开仓库。

## 候选选择

已逐条查看当前八条候选及人工队列。预算工具使用失败的故事目前是截断评论；自用产品收费案例没有独立收入凭证；原生 SSH 工具与三个常规工具发布需要较多技术背景；乐谱工具的实际结果较小。网站变慢的案例有具体开发者、分享行为、反差与普通创作者容易理解的问题。最初只有标题的证据缺口已通过原作者文章补查；没有为了分数改动筛选阈值。

## 事实核验与界限

| 类型 | 查证结果 | 公开处理 |
|---|---|---|
| Confirmed Fact | 原作者网站确实刊载了这段经历；可访问 Sprinklz 阅读工具网站；此前发布帖由同一 sammy0910 账号分享同一工具 | 只确认公开记录与工具存在，不把记录存在当作日志证实 |
| Author Claim | 分享后网站持续变慢、活跃登录用户不多、负载高、近半流量来自一个自动摘要服务、屏蔽来源与限流 | 正文使用“按照他的说法”；第三张图标注“作者称”及比例未独立核实 |
| Inference | 访问次数不必然等于真人关注，停留/回访/具体问题可能更有解释力 | 写成“这件事让我想到”“对我来说”，没有声称整个行业已发生变化 |
| Evidence Gap | 未取得服务器日志；服务方未具名；没有独立报道或第三方审计支持近半比例 | 不命名被屏蔽服务，不写全部访问为机器人，不写获客、盈利、损失金额或性能改善已经证实 |

内部原始来源：

- 作者原文：https://www.sammystraus.com/#i-posted-to-hn-and-then-my-website-was-flooded-with-ai-bot-traffic
- 产品：https://sprinklz.io/
- 公开讨论：https://news.ycombinator.com/item?id=50073221
- 此前工具发布：https://news.ycombinator.com/item?id=49660482 （官方公开 API 核对账号及工具 URL）

前三项已用 Chrome 浏览器打开。评论不作为作者服务器流量的独立证明，未摘用其他评论者的大数字。公开正文及四图无来源平台专名、URL、内部字段或 Markdown。十个内部标题候选与最终中文稿见 docs/publication/2026-10-14/。

## 表现记录

发布后已发布列表真实显示：浏览4、评论0、赞0、收藏0、分享0。数据可能包含本次页面查看，不代表独立真人读者；展示量、涨粉均未取得，保留 null。观察时间记录于本机 performance.json；未到观察点的三个快照保留空对象。

- 2h：2026-10-14 23:14（Asia/Shanghai）
- 24h：2026-10-15 21:14
- 72h：2026-10-17 21:14

复用 `performance add` 将真实数值写入本机数据库；加入 impressions、observed_at、measurement_source 与 snapshot_observed_at。未测量默认 null；快照只放实际取得的非负指标，允许观测到的0。记录每次真实读取时间，不补造准点数据。

重建图片：`uv run --with Pillow python scripts/render_story_cards.py docs/publication/2026-10-14/cards.json outputs/publication/2026-10-14/images --font /System/Library/Fonts/STHeiti\ Medium.ttc`。其他操作系统通过 --font 传入有中文字符的字体。

自动跟进创建未成功：工具三次均未创建任何 automation，不能声称已经安排自动读取。上述观察点保留为真实后续读取计划。

验证：120 项 pytest 通过；ruff 检查、格式检查与 git diff --check 通过。

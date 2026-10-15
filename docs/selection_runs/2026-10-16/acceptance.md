# V1.6 实测验收

最终候选生成：2026-10-15T23:22:56.157767+00:00（UTC；上海时间加8小时）。本轮无小红书发布、无删除。

## 当前裁判

普通人吸引力32% + 独立卡片停留强度22%，人性触发15%，生活关联12%，故事冲突7%，已核验视觉6%，中国信息差3%，实际海外热度3%。证据不参与吸引力加分，只决定事实闸门。3秒SCROLL、去术语FAIL、无点击理由或事实不足不得进入合格Top 5。

真实采集 352 条；Live Hot Scan 539 条线索；24h去重池 197，72h池 558，7天合格池 575。40条完成语义+普通人评估；Story Mining 10；8位名人；公开Telegram读取15条。

最高分 74.33 < 75；最终 NO_PUBLISH_TODAY。Top 5 全部STOP，无SCROLL。20个标题190对Tournament已完成；独立Blind Top 5第一是“这次敲键盘，居然是在弹吉他”。盲排与算法排名保留分歧，没有改权重让两者相同。

## 改造前后

最新初始云端artifact有40条输入但0条实评，不冒充有效榜单。最近有效V1.5本机榜首：苹果家庭屏幕，78.56且AUTO_PUBLISH_ELIGIBLE。新榜仍保留其家庭隐私入口，但以74.33降为编辑审核，不能靠证据强/海外程序员热度变成自动资格。

键盘吉他由旧榜12进入新榜前3：既有裁判变化，也补核了官方可读产品页；同池V1.5影子分留在JSON，不能把全部提升归因换权重。会议室录音题从公司名变成纸裹录音器这一检方材料细节，保留指控未定罪边界。机器人由旧榜2下降，强视觉并不自动等于强生活关联。

## 发布判断

本轮没有真正建议立即发布的三条，允许继续编辑的优先方向是：家庭共用设备的隐私、卫生纸遮录音器的会议室指控、免费键盘吉他。它们分别对应家庭代入、隐私与离谱反差、低门槛免费娱乐；全部仍未达到75。

## 被降级的真实科技线索

- AI视频从约1分钟走向10分钟以上：Ordinary=65.96，3秒=SCROLL，去术语=PASS；https://openai.com/index/higgsfield-longer-videos-voice。
- Anthropic重做开发版本管理流程：Ordinary=31.17，3秒=SCROLL，去术语=FAIL；https://simonwillison.net/2026/Oct/13/redesigning-source-control-at-anthropic/。
- 苹果研究用空闲设备组成分布式算力：Ordinary=16.64，3秒=SCROLL，去术语=FAIL；https://machinelearning.apple.com/research/distributed-gpu-cloud。
- 💰 Anthropic’s revenue is soaring, but its $2 trillion valuation is in doubt Anthropic reportedly generated $16.8 billion in Q3 revenue, up nearly 50%, and remained profitable on an：Ordinary=22.77，3秒=SCROLL，去术语=FAIL；https://t.me/aipost/8494。
- Show HN: Turbo Lisp – A Common Lisp IDE for macOS and the Terminal：Ordinary=13.0，3秒=SCROLL，去术语=FAIL；https://gitlab.com/patchwork1-ai/turbolisp。

降级原因依次为：视频参数不等于生活收益；版本控制工具属于研发流程；算力架构没有具体普通人遭遇；公司估值不等于个人财富且仅为未核验转述；编程IDE为开发者专用。

## 验证与限制

pytest全套172通过；最后行为修改后的相关52项通过；ruff check/format通过；完整生产run、verify-outputs、verify-publish-candidates通过。用户原始DISLIKE与已发布帖子记录不变，负样本NO_PUBLISH。

这些分数是模型模拟编辑判断，尚无真实CTR提升证明；不能只凭测试绿灯宣称选题已经讨所有用户喜欢。新增生活搜索有空结果，保留empty审计；没有伪造来源、互动或新鲜度。Top 6-10中若标题/封面事实闸门UNKNOWN，仅供核验，不得直接发出。

[首页Top 10](consumer_candidates.md) · [完整Top 20](publish_candidates.md) · [盲排](blind_top5.md) · [可复核分数与同池旧分](run_summary.json)

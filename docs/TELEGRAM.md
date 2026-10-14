# Telegram 内容源

Telegram 已纳入统一 normalization、dedupe、scoring 和 editorial pipeline。它是可选来源，不影响其他来源运行。

## 人工消息链接（立即可用）

```bash
uv run python -m xhs_content_engine inbox add 'https://t.me/channel_name/123' \
  --title '你实际看到的标题' --note '必要的短摘录或核实线索' \
  --author '已知作者' --published-at '2026-10-14T08:00:00+08:00'
uv run python -m xhs_content_engine run
```

URL-only 也可录入，但不抓取页面，不伪造标题、作者、时间或统计。原始发布时间未知的条目保存在数据库中，默认不进入“新鲜内容”排名。补充标题、短摘录和真实时间后再次 collect 即可。同一消息的 `telegram.me`、`t.me`、`/s/` 和 embed 参数合并为同一 canonical URL；不同消息 ID 不合并。

## 官方 Bot API 自动采集

1. 使用你自己的专用 bot，由频道管理员授权加入目标公开频道。不要依赖普通用户的登录会话。
2. 在 `config/sources.yaml` 的 `telegram.channels` 填入频道 username（可带 `@`）。仅接收频道白名单；不采集私聊、群聊、私有频道、受保护消息或纯媒体无文字的消息。
3. 将 bot token 放在本地环境变量 `TELEGRAM_BOT_TOKEN`，或 GitHub repository secret 的同名变量中。不要写入 YAML、日志、命令参数或仓库。
4. 此 bot 必须专用于这个 pipeline。不要让另一个程序消费同一更新队列，也不要同时配置 webhook。不会自动删除已有 webhook；409 会记录为来源错误，其他来源继续。

只调用 `getUpdates` 接收新 `channel_post` 与 `edited_channel_post`，不发送任何消息。每批最多 100 updates，默认最多 5 批，每批条目与 offset 在同一 SQLite 事务中持久化后才读下一批。频道编辑覆盖同一消息 ID，保留原始消息时间和编辑时间。转发记录为待核实，需要追溯原作者；不捏造转发来源、views、likes、订阅人数。

Bot API 不是任意频道历史搜索 API。bot 仅接收它已加入的频道消息；服务器未消费更新最多保存 24 小时。每三小时的调度减少丢失风险，但停机超过窗口仍可能漏消息。GitHub cache 可被驱逐；偏移丢失可能重读仍在队列中的消息，稳定 ID 避免同一数据库内重复入库，不能恢复已过期消息。

缺凭证或空白名单：`skip` 并记录原因。没有新消息：`empty`。API 错误仅保存异常类型和 HTTP 状态，避免 token 通过 URL 泄漏。自动接入的实际权限和消息需要配置后再做 live 验收；离线测试验证偏移、白名单、编辑、保护内容、缺凭证和错误隔离。

内部来源 `source=telegram` 与原始消息 URL 始终保留；公开 label 默认“海外社区”。独立公开候选简报经过 banned platform name policy 检查。

官方参考：[Bot API getUpdates](https://core.telegram.org/bots/api#getupdates)、[消息接收范围](https://core.telegram.org/bots/faq#what-messages-will-my-bot-get)、[更新保存窗口](https://core.telegram.org/bots/api#getting-updates)。

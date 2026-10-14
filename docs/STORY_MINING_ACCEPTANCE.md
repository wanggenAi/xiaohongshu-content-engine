# V1.3 Story Mining 验收

本记录从实际导出生成。合成测试样本不进入生产数据库；原句是来源自述，尚非独立核验。

采集时间：2026-10-14T12:19:50.299608+00:00；筛选时间：2026-10-14T12:38:19.232961+00:00。

| 指标 | 本地真实运行 |
|---|---:|
| Raw items | 337 |
| Fresh discovery | 245 |
| Fast Story Filter | 50 |
| Story Candidates | 8 |
| 后续语义输入 | 8 |
| Deep | 1 |
| Human Review Queue | 1 |

本轮保留原 Human/Editorial 门槛。每天 3～8 条 Deep 的目标尚未证明；找到故事原料与通过最终编辑门槛是不同结果。

## 来源采集

- simon_willison：ok，20 条；公开评论摘录 0 段。
- armin_ronacher：ok，10 条；公开评论摘录 0 段。
- ethan_mollick：ok，10 条；公开评论摘录 0 段。
- human_story_search：ok，65 条；公开评论摘录 93 段。

## Top 10 Story Candidates（实际 8 条）

### 1. Show HN: Pulse Local, a Mac budgeting app whose AI models run on your machine

- Who: > How it works: you import a CSV from any bank, in any currency. I dropped the CSV from my bank and only got 2 fields. I fixed the CSV and suddenly the IBAN BE12 3456 7890 123 became BE12 in Pulse First operation I did was switch it to Belgium. "type to search" Didn't work. Saving after manually setting it was a really long beach ball. Can't say I'm impresse
- Did what: > How it works: you import a CSV from any bank, in any currency. I dropped the CSV from my bank and only got 2 fields. I fixed the CSV and suddenly the IBAN BE12 3456 7890 123 became BE12 in Pulse First operation I did was switch it to Belgium. "type to search" Didn't work. Saving after manually setting it was a really long beach ball. Can't say I'm impresse
- What happened: > How it works: you import a CSV from any bank, in any currency. I dropped the CSV from my bank and only got 2 fields. I fixed the CSV and suddenly the IBAN BE12 3456 7890 123 became BE12 in Pulse First operation I did was switch it to Belgium. "type to search" Didn't work. Saving after manually setting it was a really long beach ball. Can't say I'm impresse
- Before: 未取得 / 未评估
- After: 未取得 / 未评估
- Conflict: 未取得 / 未评估
- Story Richness: 75.0
- Fallback Story Score: 65.0
- Human Trigger: 57.21
- Viral Potential: 56.84
- Claim Scope: single_case
- Evidence Gaps: ['Missing: before_state', 'Missing: after_state', 'Firsthand account is not independently verified']

### 2. Show HN: Proofsource. Find where AI leaves you out. And Fix it

- Who: I built Proofsource as an internal tool to help my finance ERP product , Rivane, to gain visibility into AI engines like ChatGPT, Claude, Perplexity, Google AI mode and such.
- Did what: I built Proofsource as an internal tool to help my finance ERP product , Rivane, to gain visibility into AI engines like ChatGPT, Claude, Perplexity, Google AI mode and such.
- What happened: And now proofsource had 5 paying customers(paying $1500pm in total) in the first week itself and more than 60 brands used it to get their visibility since we launched out of beta last week.
- Before: 未取得 / 未评估
- After: 未取得 / 未评估
- Conflict: 未取得 / 未评估
- Story Richness: 70.0
- Fallback Story Score: 75.0
- Human Trigger: 40.82
- Viral Potential: 41.79
- Claim Scope: single_case
- Evidence Gaps: ['Missing: before_state', 'Missing: after_state', 'Firsthand account is not independently verified']

### 3. Show HN: Tern – Native macOS SSH Client in Rust/GPUI (76 MB vs. Tabby's 580 MB)

- Who: So i built my own simple ssh client with a little bit of my taste added, it has vault, password manager, repo sync, background gallery etc.
- Did what: So i built my own simple ssh client with a little bit of my taste added, it has vault, password manager, repo sync, background gallery etc.
- What happened: So i built my own simple ssh client with a little bit of my taste added, it has vault, password manager, repo sync, background gallery etc.
- Before: 未取得 / 未评估
- After: 未取得 / 未评估
- Conflict: 未取得 / 未评估
- Story Richness: 70.0
- Fallback Story Score: 75.0
- Human Trigger: 54.85
- Viral Potential: 50.99
- Claim Scope: single_case
- Evidence Gaps: ['Missing: before_state', 'Missing: after_state', 'Firsthand account is not independently verified']

### 4. llm-gemini 0.35

- Who: Release: llm-gemini 0.35 I added support to llm-gemini for the new Gemini 4 Argon model, made available today via the Gemini API and for customers of their $100/month subscription plan.
- Did what: Release: llm-gemini 0.35 I added support to llm-gemini for the new Gemini 4 Argon model, made available today via the Gemini API and for customers of their $100/month subscription plan.
- What happened: Release: llm-gemini 0.35 I added support to llm-gemini for the new Gemini 4 Argon model, made available today via the Gemini API and for customers of their $100/month subscription plan.
- Before: 未取得 / 未评估
- After: 未取得 / 未评估
- Conflict: 未取得 / 未评估
- Story Richness: 70.0
- Fallback Story Score: 75.0
- Human Trigger: 38.18
- Viral Potential: 38.85
- Claim Scope: single_case
- Evidence Gaps: ['Missing: before_state', 'Missing: after_state', 'Firsthand account is not independently verified']

### 5. ttok 1.0

- Who: Release: ttok 1.0 I released ttok 0.4 , ran uv tool upgrade ttok , piped a file into the new version... and realized that it was defaulting to the GPT-4 tokenizer when it should very clearly default to GPT-5/GPT-6 instead!
- Did what: Release: ttok 1.0 I released ttok 0.4 , ran uv tool upgrade ttok , piped a file into the new version... and realized that it was defaulting to the GPT-4 tokenizer when it should very clearly default to GPT-5/GPT-6 instead!
- What happened: I figured switching the default was a reasonable excuse to finally ship a 1.0.
- Before: Release: ttok 1.0 I released ttok 0.4 , ran uv tool upgrade ttok , piped a file into the new version... and realized that it was defaulting to the GPT-4 tokenizer when it should very clearly default to GPT-5/GPT-6 instead!
- After: 未取得 / 未评估
- Conflict: 未取得 / 未评估
- Story Richness: 70.0
- Fallback Story Score: 45.0
- Human Trigger: 44.78
- Viral Potential: 43.57
- Claim Scope: single_case
- Evidence Gaps: ['Missing: after_state', 'Firsthand account is not independently verified']

### 6. web-edit 0.1a0

- Who: I had Codex and GPT-6 Astra Extra High build this Python web app which provides a web UI for viewing and editing files in a folder.
- Did what: I had Codex and GPT-6 Astra Extra High build this Python web app which provides a web UI for viewing and editing files in a folder.
- What happened: I had Codex and GPT-6 Astra Extra High build this Python web app which provides a web UI for viewing and editing files in a folder.
- Before: 未取得 / 未评估
- After: 未取得 / 未评估
- Conflict: 未取得 / 未评估
- Story Richness: 70.0
- Fallback Story Score: 45.0
- Human Trigger: 41.88
- Viral Potential: 43.02
- Claim Scope: single_case
- Evidence Gaps: ['Missing: before_state', 'Missing: after_state', 'Firsthand account is not independently verified']

### 7. Show HN: XY Music Notation

- Who: I used codex to build a music score rendering backend based on MuseScore with custom note heads that display the pitch class of each note.
- Did what: I used codex to build a music score rendering backend based on MuseScore with custom note heads that display the pitch class of each note.
- What happened: I've found it pretty helpful for learning how to play my own instrument, so wanted to share in case anyone else was interested.
- Before: 未取得 / 未评估
- After: 未取得 / 未评估
- Conflict: 未取得 / 未评估
- Story Richness: 65.0
- Fallback Story Score: 75.0
- Human Trigger: 48.53
- Viral Potential: 46.36
- Claim Scope: single_case
- Evidence Gaps: ['Missing: before_state', 'Missing: after_state', 'Firsthand account is not independently verified']

### 8. I posted to HN, and then my website was flooded with AI bot traffic

- Who: I posted to HN, and then my website was flooded with AI bot traffic
- Did what: I posted to HN, and then my website was flooded with AI bot traffic
- What happened: I posted to HN, and then my website was flooded with AI bot traffic
- Before: 未取得 / 未评估
- After: 未取得 / 未评估
- Conflict: 未取得 / 未评估
- Story Richness: 60.0
- Fallback Story Score: 70.0
- Human Trigger: 38.52
- Viral Potential: 39.58
- Claim Scope: single_case
- Evidence Gaps: ['Missing: before_state', 'Missing: after_state', 'Firsthand account is not independently verified']

## GitHub Actions artifact

[完整运行](https://github.com/wanggenAi/xiaohongshu-content-engine/actions/runs/38565125461)

Raw 337 → Fast 50 → Story Candidates 0 → Deep 0；Human Review Queue 10。

人工队列 Fallback Story Score：[100.0, 95.0, 90.0, 85.0, 85.0, 85.0, 80.0, 75.0, 75.0, 75.0]。

artifact 已下载后独立检查 Markdown、JSON、packet 数量、候选身份与来源片段。

云端没有语义 key；本地分数仅是人工排序信号，Human/Viral 均为 null。

## 自动检查

pytest：118 passed；ruff check / format 与 diff 检查通过。

测试包含 30 条明确标注的合成示例及 8 条冻结真实素材，另检验企业 we、评论归属、独立案例、低权威个人来源与无 API 排序。

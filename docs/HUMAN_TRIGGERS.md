# Human Trigger Layer V1.2

以已有必要摘录识别人的处境，不新增采集来源、发布端或界面。外部语义判断不能充当独立事实核验，也不生成最终文案。

## 三个分数与 Deep 门槛

Discovery 保留旧分数。Editorial 保留七维价值权重与独立 decision-risk 扣分；仅在五个 scene 字段全无证据时，将 story_strength 限到 0.25，记录明确证据上限。Human Trigger 是另一组十维分数：钱12、工作12、身份10、失去10、愿望10、反转12、场景10、公平8、幕后8、讨论8。

每维为 0–1，按权重累加。没有来源锚点的维度最多 0.2；缺少完整人行动后果链的 scene 最多 0.25；未取得两个不同来源片段的 reversal 最多 0.2。强反转、场景、身份与生计可分别获得 12/5/3/5 的有证据加分，防止其他无关维度为零淹没稀疏故事；全部贡献、加分和系数可审计，总分上限100。

没有任何场景字段乘0.65，有部分字段但无 who+action+(result/consequence) 乘0.85；没有自然讨论入口再乘0.85。缺证据不通过关键词补齐。

以下任一门可进入后续审阅：A，Human≥65；B，有≥0.75强触发器，scene≥0.65且完整、identity≥0.6且身份明确；C，有≥0.85强反转。A/B 可进入 Deep；仅满足 C 保留人工队列。Deep 仍需 Editorial≥45、human_relevance≥0.4、china_relevance≥0.5、有效后果 lens、完整语义状态且无硬拒绝。45 是现有 Stage B 门槛：低于旧 Deep 60 的有证据人性故事可以进入调查，不自动成为高价值已核实新闻。

`LOW_HUMAN_TRIGGER` 明确保留为降级码。它不抹掉 Stage B 的编辑价值；Deep 需要额外通过人性门槛。排名为 Human55% + Editorial30% + Evidence15%，不是传播预测。

## 事实、故事结构与标题

Human Trigger map、scene、reversal、标题 evidence_anchor 都是原文句子或子串。模型只在来源片段间选择，不能写新事实。模型把同一个含“but/但”等对照的句子选作 setup/turn 时，代码可拆成原文两段；缺失反转明确显示 NONE。

Pattern A–F 从有证据的反转、身份与工作、利益与公平、现场与幕后、具体行为与能力、公平冲突结构组合得到，供审稿识别结构，不复制爆帖。

读者身份与情绪张力都是明确标注的编辑关联/调查假设，不代表已发生的中国现象或真实当事人情绪。讨论路由是自然问题入口，不是已经取得的评论，更不预测评论数。

每条标题有 scene / reversal / identity_interest 三种调查角度，复用语义选中的后果 lens，附原文锚点和 claim_scope；不是原文翻译或平台名替换。标题采用提问/条件表达。没有场景或反转时，它是查证问题，不宣称有实际场景或反转。

claim_scope 为 single_case、reported_trend、company_claim、multiple_sources、verified_event。没有独立记录不能升级成 verified_event；未提供独立证据 URL 不能升级成 multiple_sources；仅标题不能升级为趋势。保留官方声称、个案、报道等语气，不能由植入推断恢复、使用AI推断裁员或交易意向推断成交。

## 缺少语义 API 的生产行为

API 不可用时，从 Stage A 中优先取 Discovery 排名靠前的最多10条；同分时优先有摘录、来源可靠的材料，形成 Human Review Queue。明确 NEEDS_HUMAN_REVIEW、unavailable、null Human/Viral；原始标题、链接、摘录、作者和审稿问题仍可读。不会假装已完成人性评估。

部分请求失败时，已完成判断可形成 Deep，失败素材单独排队。整批有材料但都被降级时保留原拒绝码供人工复核。没有任何 Stage A 材料时无法凭空创造队列，采集审计保留原因。

原文平台专名只保留在内部证据包。主审稿页中的场景原句若包含禁止专名，引导至证据包；待审队列可取不含专名的原文子句并标注“原文片段”，否则引导完整证据包。不机械替换成“海外”；其他原句照录。公开 brief 和审稿摘要都运行相同检查。

## 验证

pytest 覆盖独立评分、五种触发提升、无场景降级、正负 fixture、事实范围约束、三个不同标题角度、读者与讨论入口、断网/缺key完整链、反馈兼容和篡改报告数量。固定受控判断的测试只验证组合逻辑；scripts/backtest_human.py 另对八条真实冻结素材和六个合成样本调用实际语义 API，原始判断保存在生成结果中，不把 fixture 当生产素材。

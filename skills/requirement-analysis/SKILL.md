---
name: requirement-analysis
description: >
  当用户提供需求描述、需求文档、ticket URL，或要求“需求分析”“需求拆解”“整理需求”“生成需求文档”时必须使用。
  本 skill 是方案设计前的入口阶段：提取平台和版本，拆解功能项，澄清模糊点，识别平台依赖和数据来源，
  并把确认后的需求分析文档保存到当前项目目录下。

---

# 需求分析

本 skill 把自然语言需求、ticket 页面或粘贴文档转成可确认、可校验、可交接给 `design-phase` 的需求分析产物。

需求分析只确认问题、范围、功能、数据来源、验收、风险和澄清；不做 UI 设计、API 选型、数据库设计或代码生成。

## 硬性原则

- `product_id` / 平台名称 和 `product_version` / 平台版本是强制项。缺失时先阻塞确认，不能继续分析。
- 直连人工模式下，所有用户交互都必须使用 `AskQuestion`，包括缺信息、澄清、输出路径确认和阶段确认。
- `worker_mode: true` 时不能直接使用 `AskQuestion`。需要人工确认时写 `pending-questions.json` 和 `worker-result.json(status=NEED_USER_INPUT)` 后停止。
- orchestrator worker 模式下必须先读取 `workflow-input.json`。`ticket_url` 走 Mode A；`manual_text`、`document_file`、`goal_only` 走 Mode B。
- 不要把功能项只按页面或 CRUD 拆解；必须同时分析触发来源、输入来源、输出去向、数据对象、状态流转、异常场景和平台依赖。
- 不要把“定制实现”等同于“不依赖平台”。只要需求需要读取、写入、订阅、校验、展示、关联或补全平台既有对象、事件、规则、状态、权限或配置，就必须记录平台依赖。
- 对通知、推送、发送、分派、审批、抄送、派单、升级、授权、订阅、触达等动作，必须识别“目标对象解析”：作用到谁/什么对象、目标从哪里来、如何过滤、如何取得联系方式或标识。
- 需求文档必须保存到当前项目目录下，不能保存到 `%USERPROFILE%\.claude\project`、用户 home、临时目录或当前 skill 目录。
- 不要把未确认推断写成确定结论。所有结论必须标注来源：明确、澄清、推断、待确认。
- 最终版 `需求分析.md` 中不能残留 `[待确认]`、`待确认` 或关键 open question。未解决时只能输出草稿，不能声明完成。

## 输入处理

- Ticket URL：按 `references/input-fetching.md` 的级联抓取策略处理，先轻量抓取，失败后再切换 Playwright MCP 或浏览器。
- 手动文本/文档：直接提取平台、版本、背景、角色、功能项、验收、约束和澄清记录。
- 需要 SSO、人机验证、文件选择、附件下载或外部系统操作时，直连人工模式按 `AskQuestion`；worker 模式按 `references/worker-mode.md` 的 external-action 协议暂停。
- 若平台名称或版本缺失，先确认，不进入 Phase 2。

## 工作流

必须按 Phase 1-5 顺序执行。不要跳过 Phase 4 的澄清门禁。

### Phase 1：提取和归一化

提取并保留来源、原始需求文本、平台名称、平台版本、需求标题、背景目标、角色参与者、外部系统和已有澄清结论。

如果同一信息存在多个叫法，建立映射并标注确认状态，例如 `PV 2.4.0`、`PVIA 2.4.0`、`PVIA平台`。

### Phase 2：功能拆解

把需求拆成离散功能项，编号为 `F-01`、`F-02`。每个功能项必须包含描述、证据级别、原文依据、触发条件、输入、输出、前后置条件、角色、优先级、业务规则、数据规则、权限规则、状态流转、异常边界、审计日志、平台依赖摘要和 Given/When/Then 验收标准。

功能拆解细则、深度标准和模板见 `references/analysis-rules.md`。

### Phase 3：平台依赖和数据来源分析

对每个功能项分析触发依赖、目标对象解析、主数据依赖、详情补全依赖、规则策略依赖、状态写回依赖、查询统计依赖和外部系统边界。

只要任一平台依赖成立，就标记“是”或“待确认”，不能直接标记“否”。数据来源不明确时标记 `[待确认]`，并写出 design-phase 检索意图。

详细依赖类型和输出表格见 `references/analysis-rules.md`。

### Phase 4：模糊点澄清

这是硬门禁。关键澄清点数量必须为 0，才能生成最终版。

澄清至少覆盖平台/版本、角色权限、功能范围、不做范围、触发条件、失败处理、数据来源、目标对象来源、外部协议、非功能要求、统计口径和数据保留。

直连人工模式使用 `AskQuestion` 分批提问；worker 模式写 `pending-questions.json` 后退出。用户回答后，必须回写“澄清记录”和对应功能项。

### Phase 5：生成需求分析产物

按 `references/output-contracts.md` 生成：

- `requirement-handoff.json`
- `requirement-validation.json`
- `worker-result.json`
- `需求分析.md` 或 `需求分析-草稿.md`
- `design-phase-handoff.md`

Phase 5 的写入顺序是机器文件优先：先写 `requirement-handoff.json`，再运行 validator 生成 `requirement-validation.json`，随后尽早写 `worker-result.json`。草稿也必须写 handoff，`source.requirement_status=draft`，并把未解决问题写入 `open_questions`。Markdown 文档和 `design-phase-handoff.md` 可以随后补齐，但不能只写 Markdown 而缺少机器文件。

最终产物必须位于 `<项目根目录>/requirements/<product_id-product_version>/` 或等价产品目录。写入后重新读取，确认不是空文件、不是摘要占位符，并包含功能项、平台依赖、澄清记录和 design-phase 交接上下文。

## Orchestrator Worker 模式

当 prompt、`workflow-state.json` 或用户明确指令包含 `worker_mode: true` 时，进入 worker 模式。

- 第一动作读取 `workflow-state.json`、`workflow-input.json`、`decisions.jsonl`、`worker-checkpoint.json`、`external-result.json` 和已有输入材料。
- 如果 checkpoint 已满足恢复条件，从 `resume_from` 继续，不重复 `completed_steps`。
- 如果没有 checkpoint，按 Phase 1-5 顺序执行。
- 需要用户确认或主流程外部动作时，写 checkpoint、pending/external-action、worker-result 后停止。
- 进入 Phase 5 后优先写 `requirement-handoff.json`、`requirement-validation.json` 和 `worker-result.json`；不要等完整 Markdown 全部润色完成后才写 result。
- 阶段完成且 `requirement-validation.json.success=true` 时，写 `worker-result.json(status=STAGE_COMPLETED)`；是否进入 design-phase 由 orchestrator 处理。

完整 worker 文件协议见 `references/worker-mode.md`。

## 何时读 References

- 抓取 ticket、SSO 配置、输入模式：读 `references/input-fetching.md`。
- 证据级别、功能拆解、平台依赖、澄清门禁：读 `references/analysis-rules.md`。
- worker 模式、pending/result schema、checkpoint/external-action 行为：读 `references/worker-mode.md`。
- 输出目录、文档模板、handoff JSON、validator、完成检查：读 `references/output-contracts.md`。

## 完成条件

只有同时满足以下条件，才能声明需求分析完成：

- 平台名称和版本已确认。
- 所有功能项已拆解，并具备业务规则、数据规则、权限规则、状态流转、异常边界和验收标准。
- 每个功能项都完成平台依赖和数据来源分析。
- 所有关键 `[待确认]` 已解决，最终文档中没有待确认项。
- `需求分析.md`、`design-phase-handoff.md`、`requirement-handoff.json`、`requirement-validation.json` 已生成到项目 `requirements/` 目录。
- `requirement-validation.json.success=true`。
- 最终回复给出产物绝对路径。

有任何一项未完成，不要宣称需求分析完成。

---
name: design-phase
description: 在需求分析已确认平台名称和平台版本后，进入方案设计阶段。使用当前 ai-agent MCP 工具校验平台基线组件、检索组件段和 API 契约，为每个需求分解项产出有证据链的组件/API 选择、前后端方案、数据库和接口设计。用户说“方案设计”“设计阶段”“根据需求分解做设计”时使用。
---

# 方案设计

本 skill 把已确认的需求分析结果转成可执行详细设计。涉及基线组件/API 时必须通过 MCP 获取证据，禁止凭模型记忆编造组件、接口、版本或路径。

## 硬性原则

- 需求分析阶段必须已经明确 `product_id` 和 `product_version`。缺失时先阻塞确认，不调用 MCP。
- design-phase 的事实来源优先级：`requirement-handoff.json` > `design-phase-handoff.md` > `需求分析.md` > 当前对话摘要。
- 不依赖需求分析阶段聊天历史补事实；聊天历史只能提示，不能作为已确认结论。
- 每个需求分解项单独检索，不要把多个需求合成一个 MCP 查询。
- MCP 只检索平台依赖能力，不检索外部系统执行动作。
- “定制实现”不等于“不调用基线组件”。只要定制功能依赖平台既有对象、事件、规则、状态、权限、配置或展示字段，就必须标记为需要调用基线组件或待确认。
- 通知、推送、发送、分派、审批、抄送、派单、升级、授权、订阅、触达等动作必须先解析目标对象来源。
- 每个最终选中的 API 必须经过 `get_api_detail` 二次确认。
- 输出方案时必须带 MCP 证据：组件版本、组件段、文档版本、`match_level`、`risk`、请求/响应契约。
- 低版本组件不能采纳高版本才存在的 API 或契约。最终 API 必须证明 `contract_doc_version <= resolved_doc_version`，并写入版本兼容证据。
- MCP 为空、契约为空、风险不可接受或版本跨 major 不确定时，停止并询问用户；不要猜。

## 运行和交互模式

默认使用人工审阅模式。除非用户明确说“全自动”“自动完成所有阶段”“不要逐阶段确认”，否则不能一口气生成完整设计文档。

直连人工模式下，所有用户交互必须使用 `AskQuestion`。worker 模式下不能直接使用 `AskQuestion`，必须写 `pending-questions.json` 和 `worker-result.json(status=NEED_USER_INPUT)` 后停止。

必须确认的节点：

- Phase 0 加载摘要。
- Phase 2 架构、中间件、运行环境、部署形态、定制模块边界。
- Phase 2.5 每个功能项或子能力的实现方式分类、是否调用基线组件、MCP 检索任务。
- Phase 3 MCP 检索计划、组件范围、现场组件版本覆盖。
- Phase 4 候选 API 选择、改定制、用户指定 API、补知识库。
- Phase 5-8 的前端、后端、数据库、内部协议设计。
- 风险处理、数据库类型、MCP 为空或低置信度等决策。

交互和 worker 文件协议见 `references/worker-mode.md`。

## 实现方式分类

每个功能项或子能力都必须先分类，再决定是否查 MCP：

- `BASELINE_API_REUSE`：直接复用平台基线 API。
- `CUSTOM_CODE`：本项目定制代码实现，不调用基线 API。
- `EXTERNAL_INTEGRATION`：对接第三方或外部系统。
- `HYBRID`：定制代码/外部集成 + 平台基线 API 获取上下文或写回状态。
- `NO_API_NEEDED`：纯页面展示、纯配置说明、纯文档或无需后端调用。
- `UNDECIDED`：信息不足，需要用户确认。

候选 API 只证明“可能可复用”，最终是否复用必须结合业务场景、字段覆盖、版本风险、调用成本和用户选择。

## 执行节奏

必须按 Phase 0-9 顺序推进。人工审阅模式下，每个阶段结束后停止等待用户回复；worker 模式下，每个确认点写 pending，由 orchestrator 主流程询问用户并写入 `decisions.jsonl`。

0. Phase 0：上下文重置和交接文件加载。
1. Phase 1：加载需求分析结果。
2. Phase 2：架构选型和中间件确认。
3. Phase 2.5：确认哪些需求项需要调用基线组件。
4. Phase 3：MCP 基线范围校验和候选 API 检索。
5. Phase 4：API 详情确认和用户选择。
6. Phase 5：前端页面设计。
7. Phase 6：后端 Gateway REST + 基线组件调用设计。
8. Phase 7：数据库设计。
9. Phase 8：内部协议设计。
10. Phase 9：输出详细设计文档。

Phase 详情、状态账本和各阶段输出要求见 `references/phase-details.md`。

## MCP 使用边界

只使用当前项目真实存在的 MCP 工具清单；进入 MCP 阶段前读取 `references/mcp-baseline-rules.md`。

核心约束：

- 先 `health_check()`，再校验产品版本和组件范围。
- 对 Phase 2.5 产出的每个“平台上下文动作”单独调用 `find_apis_for_requirement`。
- 检索词必须描述要从平台获取、校验、监听、写回什么，而不是外部动作。
- 每个候选 Top API 必须调用 `get_api_detail` 二次确认。
- MCP 返回 `NO_COMPATIBLE_CONTRACT`、`NEED_KB_IMPORT`、版本不可比较或契约版本高于当前组件可用文档版本时，不能采纳为最终 API。
- MCP 调用记录、候选、采纳/淘汰原因必须写入 `design-handoff.json` 和设计文档。
- 不要调用旧版搜索类或候选提交类 MCP 工具。

## Orchestrator Worker 模式

当 prompt、`workflow-state.json` 或用户明确指令包含 `worker_mode: true` 时，进入 worker 模式。

- 第一动作读取 `workflow-state.json`、`decisions.jsonl`、`worker-checkpoint.json`、`external-result.json`、`requirement-handoff.json` 和已有 `design-phase-state.md`。
- 如果 checkpoint 已满足恢复条件，从 `resume_from` 继续，不重复 `completed_steps`。
- 如果没有 checkpoint，按 Phase 0-9 顺序执行。
- 需要用户确认或主流程外部动作时，写 checkpoint、pending/external-action、worker-result 后停止。
- worker 模式下也不能隐藏 MCP 过程；MCP 搜索计划、调用日志、候选淘汰原因必须落入 `design-handoff.json`。
- `design-handoff.json`、`pending-questions.json` 和 `worker-result.json` 必须通过 JSON serializer 写入，写完立即 `json.load` 校验；API 示例、请求/响应样例和用户原话中的双引号不能破坏 JSON。
- 阶段完成且 `design-validation.json.success=true` 时，写 `worker-result.json(status=STAGE_COMPLETED)`；是否进入后续阶段由 orchestrator 处理。

完整协议见 `references/worker-mode.md`。

## 输出产物

Phase 9 必须在需求交接目录生成：

- `design-doc.md`
- `design-handoff.json`
- `design-validation.json`

输出目录、核心表、handoff JSON schema、validator 和完整检查清单见 `references/output-contracts.md`。

## 何时读 References

- 用户交互、人工审阅、worker-mode、pending/result schema：读 `references/worker-mode.md`。
- MCP 工具清单、高准确率原则、Phase 2.5/3/4 细则、MCP 为空处理：读 `references/mcp-baseline-rules.md`。
- Phase 0-9 详细动作、状态账本、架构/前后端/数据库/协议设计要求：读 `references/phase-details.md`。
- 设计文档模板、`design-handoff.json`、validator、完成检查：读 `references/output-contracts.md`。

## 完成条件

只有同时满足以下条件，才能声明方案设计完成：

- 已优先读取并使用 `requirement-handoff.json`，或明确说明替代来源。
- 已创建并持续更新 `design-phase-state.md`。
- 平台和版本已确认。
- 架构、中间件、实现方式分类、MCP 计划、候选 API、数据库和风险均已确认，除非用户明确要求全自动。
- 已调用 `list_products` 和 `list_product_components` 确认平台及组件范围。
- 每个平台上下文动作都有 MCP 检索任务和调用记录。
- 每个最终 API 都调用了 `get_api_detail`。
- 每个最终 API 都在 `design-handoff.json` 中写明 `method`、`api_path`、请求参数/契约和响应结果/契约。
- 每个最终 API 都在 `design-handoff.json` 中写明 `resolved_doc_version`、`contract_doc_version`、`version_match_policy`、`version_compatibility=PASS`；不得低版本采纳高版本契约。
- `CUSTOM_CODE`、`EXTERNAL_INTEGRATION`、`HYBRID` 子能力都有非 MCP 设计说明。
- `design-doc.md`、`design-handoff.json`、`design-validation.json` 已生成到项目 `requirements/` 目录。
- `design-validation.json.success=true`。
- 没有 `UNDECIDED`、`待确认`、编造组件/API 或用外部动作直接作为 MCP 查询词。

有任何一项未完成，不要宣称方案设计完成。

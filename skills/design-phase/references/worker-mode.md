# Worker Mode

## 直连人工模式

design-phase 涉及用户交互时必须使用 `AskQuestion`，不能用普通助手消息直接提问或让用户选择。

适用范围包括：

- 缺少 `product_id`、`product_version`、数据库类型、运行环境等必要信息。
- 每个阶段结束后的确认。
- 架构、中间件、运行环境、部署形态、定制模块边界确认。
- 实现方式分类确认。
- 需求项是否调用基线组件的逐项确认。
- 现场组件版本覆盖、组件版本到文档版本映射确认。
- 候选 API 选择、改为定制实现、用户指定其他 API、要求补知识库。
- MCP 为空、契约为空、低置信度、风险不可接受、版本跨 major 不确定等场景。

`AskQuestion` 内容必须包含当前阶段、阻塞原因、已知事实和 MCP 证据摘要、明确问题、可选项、推荐项和推荐理由。没有足够证据时写“无推荐项”。发出后立即停止当前阶段。

## Orchestrator Worker 模式

当 prompt、`workflow-state.json` 或用户明确指令包含 `worker_mode: true` 时使用本协议。

- 先读取 `workflow-state.json`、`decisions.jsonl`、`worker-checkpoint.json`、`external-result.json`、`requirement-handoff.json` 和已有 `design-phase-state.md`。
- 如果 checkpoint 已满足恢复条件，必须从 `resume_from` 继续，不重复 `completed_steps` 中已经完成的 Phase、MCP 查询、用户确认、API 详情确认或写文件动作。
- 如果不存在可恢复 checkpoint，按 Phase 0-9 顺序执行。
- 不要直接向用户提问，不要调用 `AskQuestion`。
- 遇到架构选型、中间件、实现方式分类、MCP 检索计划、候选 API 选择、数据库类型、风险处理等人工确认点，先写 `worker-checkpoint.json`，再写 `pending-questions.json`，再写 `worker-result.json(status=NEED_USER_INPUT)`，然后停止。
- 如果 `decisions.jsonl` 已经包含对应 `question_id` 的用户决策，使用该决策继续执行，并写入 `design-phase-state.md`、`design-handoff.json` 和设计文档。
- 每个问题必须有稳定 `id`；同一个问题重试时复用同一个 `id`。
- 遇到启动 MCP 服务、导入/补充知识库、选择本地文件、访问外部系统、人机验证或长时间人工处理，写 `external-action.json` 和 `worker-checkpoint.json`，再写 pending/result 后停止；恢复后读取 `external-result.json` 并从 checkpoint 继续。
- worker 模式下也不能隐藏 MCP 过程；MCP 搜索计划、调用日志、候选淘汰原因必须落入 `design-handoff.json`。
- `design-handoff.json`、`pending-questions.json` 和 `worker-result.json` 必须用 JSON serializer 写入，写完立即 `json.load` 校验；不要手工拼接包含双引号、反斜杠或换行的 JSON 字符串。
- 阶段完成时写 `worker-result.json(status=STAGE_COMPLETED)`，包含 `artifact_dir`、`handoff`、`validation` 和简短 `summary`。
- 校验失败时先分类：涉及 `UNDECIDED`、`待确认`、架构/中间件选择、MCP 计划确认、候选 API 选择、数据库类型、风险处理等用户决策的问题，必须转 pending；纯文档结构或字段漏写可基于已确认事实补充后重跑 validator。
- worker 模式下不要询问“是否继续进入原型/编码/自测”。设计完成且 validator 成功时直接返回 `STAGE_COMPLETED`。

## pending-questions.json

```json
{
  "status": "NEED_USER_INPUT",
  "stage": "design-phase",
  "phase": "Phase 2 架构选型",
  "question_batch_id": "DQ-0001",
  "questions": [
    {
      "id": "design.architecture.service_shape",
      "question": "",
      "options": [
        {
          "key": "",
          "label": "",
          "recommended": true,
          "description": ""
        }
      ],
      "impact": "",
      "default_if_full_auto": ""
    }
  ],
  "known_facts": [],
  "blocking_reason": ""
}
```

## worker-result.json

```json
{
  "status": "STAGE_COMPLETED|NEED_USER_INPUT|VALIDATION_FAILED|BLOCKED",
  "stage": "design-phase",
  "phase": "",
  "artifact_dir": "",
  "handoff": "",
  "validation": "",
  "pending_questions": "",
  "summary": "",
  "next_action": ""
}
```

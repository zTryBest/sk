# Worker Mode

当 prompt、`workflow-state.json` 或用户明确指令包含 `worker_mode: true` 时使用本协议。

## 执行规则

- 先读取 `workflow-state.json`、`workflow-input.json`、`decisions.jsonl`、`worker-checkpoint.json`、`external-result.json` 和已有输入材料。
- 根据 `workflow-input.json.source_type` 分流：`ticket_url` 走 Mode A；`manual_text`、`document_file`、`goal_only` 走 Mode B；`mixed` 先处理 URL/文档证据，再合并直接文本补充。
- 如果存在 `worker-checkpoint.json`，且 `decisions.jsonl` 或 `external-result.json` 已满足其 `required_inputs`，必须从 `resume_from` 继续。
- 不要重复 `completed_steps` 中已经完成的抓取、分析、确认或写文件动作。
- 如果不存在可恢复 checkpoint，按 Phase 1-5 顺序执行。
- 不要直接向用户提问，不要调用 `AskQuestion`。
- 遇到缺少平台名称/版本、关键澄清点、输出路径确认等人工确认点，先写 `worker-checkpoint.json`，再写 `pending-questions.json`，再写 `worker-result.json(status=NEED_USER_INPUT)`，然后停止。
- 如果 `decisions.jsonl` 已经包含对应 `question_id` 的用户决策，使用该决策继续执行，并把证据级别标为 `澄清`。
- 每个问题必须有稳定 `id`；同一个问题重试时复用同一个 `id`。
- 遇到 SSO 时先按 `input-fetching.md` 尝试 worker 内自动登录；只有缺少配置、MCP/浏览器不可用、自动登录失败或需要人机验证时，才写 `external-action.json` 和 checkpoint，再写 pending/result 后停止。
- 遇到文件选择、附件下载、访问外部系统或长时间人工处理，写 `external-action.json` 和 checkpoint，再写 pending/result 后停止；恢复后读取 `external-result.json` 并从 checkpoint 继续。
- 阶段完成时写 `worker-result.json(status=STAGE_COMPLETED)`，包含 `artifact_dir`、`handoff`、`validation` 和简短 `summary`。
- 校验失败时先分类：需要用户确认的新事实必须转 pending；纯文档结构或字段遗漏可以基于已知事实补齐并重跑 validator。
- worker 模式下不要询问“是否继续进入 design-phase”。需求分析完成且 validator 成功时直接返回 `STAGE_COMPLETED`。

## pending-questions.json

```json
{
  "status": "NEED_USER_INPUT",
  "stage": "requirement-analysis",
  "phase": "Phase 4 模糊点澄清",
  "question_batch_id": "RQ-0001",
  "questions": [
    {
      "id": "requirement.target_source.F-01",
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
  "stage": "requirement-analysis",
  "phase": "",
  "artifact_dir": "",
  "handoff": "",
  "validation": "",
  "pending_questions": "",
  "summary": "",
  "next_action": ""
}
```

## validation failure 分类

需要用户确认，必须转 pending：

- `[待确认]` 或 `待确认`
- `open_questions`
- 目标对象来源未确认
- 产品/版本缺失
- 任何需要新业务事实的问题

可以 worker 自行修复：

- 章节缺失
- 验收标准数量不足
- 字段漏写但不需要新增业务事实
- JSON/Markdown 结构问题

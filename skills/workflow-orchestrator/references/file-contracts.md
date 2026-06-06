# File Contracts

本文件保存 workflow-orchestrator 的精确文件协议。主 `SKILL.md` 只保留调度规则；需要 schema 时再读取本文件。

## 运行目录选择

- 如果已知 `product_id` 和 `product_version`，使用 `<项目根目录>/requirements/<product_id-product_version>/`。
- 如果还不知道产品和版本，先使用 `<项目根目录>/requirements/_workflow/<run_id>/`。
- `requirement-analysis` 完成后，如果产物位于新的产品目录，更新 `workflow-state.json.artifact_dir` 指向产品目录。

## 必备文件

```text
workflow-state.json
decisions.jsonl
worker-prompt.md
worker-result.json
pending-questions.json
worker-run-metrics.json
```

## 按需文件

```text
worker-checkpoint.json
external-action.json
external-result.json
```

这些文件用于通用“暂停-外部动作-恢复”协议。worker 不能假设自己的浏览器、MCP 连接、临时进程或内存状态能跨 `NEED_USER_INPUT` 保留。

## workflow-state.json

```json
{
  "schema_version": "1.0",
  "workflow_goal": "",
  "run_id": "",
  "project_root": "",
  "artifact_dir": "",
  "current_stage": "requirement-analysis",
  "current_phase": "",
  "stage_status": "READY|RUNNING|NEED_USER_INPUT|VALIDATION_FAILED|COMPLETED|BLOCKED",
  "latest_handoff": "",
  "latest_validation": "",
  "pending_questions": "",
  "pending_next_stage": "",
  "completed_stage_waiting_approval": "",
  "decisions_log": "decisions.jsonl",
  "retry_count": 0,
  "max_retries": 2,
  "auto_advance_stages": false,
  "worker_subagents_enabled": false,
  "worker_subagents": [],
  "history": []
}
```

## pending-questions.json

```json
{
  "status": "NEED_USER_INPUT",
  "stage": "",
  "phase": "",
  "question_batch_id": "",
  "questions": [
    {
      "id": "",
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

## worker-checkpoint.json

worker 在任何 `NEED_USER_INPUT`、外部动作、validation retry 或阶段暂停前都必须写 checkpoint，保证重新拉起 worker 时可以断点恢复，而不是从头执行。

```json
{
  "schema_version": "1.0",
  "stage": "",
  "phase": "",
  "checkpoint_id": "",
  "resume_mode": "continue_from_checkpoint",
  "completed_steps": [],
  "resume_from": "",
  "required_inputs": [],
  "produced_artifacts": {},
  "external_action": "",
  "notes_for_worker": ""
}
```

## external-action.json

当 worker 需要主流程或用户完成外部动作时写入。它是通用协议，不限于 SSO。

```json
{
  "schema_version": "1.0",
  "status": "NEED_MAIN_ACTION",
  "action_id": "",
  "action_type": "BROWSER_LOGIN|HUMAN_VERIFICATION|FILE_SELECTION|EXTERNAL_SYSTEM_OPERATION|MANUAL_CONFIRMATION|OTHER",
  "stage": "",
  "phase": "",
  "reason": "",
  "inputs": {},
  "expected_outputs": [
    {
      "name": "",
      "path": "",
      "description": ""
    }
  ],
  "resume_decision_id": "",
  "instructions_for_main_session": []
}
```

常见映射：

- SSO 登录、人机验证：`BROWSER_LOGIN` 或 `HUMAN_VERIFICATION`，主 session 持有浏览器，输出页面文本、HTML 文件、cookies 状态或可继续抓取的证据路径。
- 用户选择本地文件、下载附件：`FILE_SELECTION`，输出文件路径。
- 外部系统里创建、审批、授权、配置开关：`EXTERNAL_SYSTEM_OPERATION`，输出操作结果和证据路径。
- 纯业务决策：优先只用 `pending-questions.json`；如果伴随外部动作，再同时写 `external-action.json`。

## external-result.json

主流程完成 `external-action.json` 后写入。worker 恢复时必须先读它，再根据 `worker-checkpoint.json.resume_from` 继续。

```json
{
  "schema_version": "1.0",
  "action_id": "",
  "status": "COMPLETED|FAILED|CANCELLED",
  "outputs": {},
  "summary": "",
  "completed_at": ""
}
```

## decisions.jsonl

每行一个用户决策：

```json
{"decision_id":"D-0001","question_batch_id":"Q-0001","question_id":"architecture.service_shape","selected":"springboot-monolith","free_text":"","decided_by":"user","decided_at":"2026-06-05T12:00:00+08:00"}
```

## worker-result.json

```json
{
  "status": "STAGE_COMPLETED|NEED_USER_INPUT|VALIDATION_FAILED|BLOCKED",
  "stage": "",
  "phase": "",
  "artifact_dir": "",
  "handoff": "",
  "validation": "",
  "pending_questions": "",
  "summary": "",
  "next_action": ""
}
```

## worker-run-metrics.json

`run-worker` 启动 `claude -p` 后必须写该文件，用于证明 worker 真的被单独调用，并记录 CLI JSON 输出中可提取的用量字段。

```json
{
  "is_worker": true,
  "worker_invocation": "claude -p",
  "session_isolation": "new claude -p invocation; no --resume or --continue is used by the orchestrator",
  "started_at": "",
  "ended_at": "",
  "duration_seconds": 0,
  "returncode": 0,
  "command": [],
  "prompt_path": "",
  "log_path": "",
  "stdout_json_parsed": true,
  "session_id": "",
  "num_turns": 0,
  "total_cost_usd": 0,
  "usage": {},
  "worker_subagents_enabled": false,
  "worker_subagents": []
}
```

如果 CLI 当前版本没有在 JSON 中返回 token usage，`usage` 可能为空。这不等于 worker 没有隔离；仍可通过 `worker_invocation`、`command`、`started_at`、`duration_seconds`、`returncode` 和独立输出文件证明。

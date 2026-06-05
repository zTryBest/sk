---
name: workflow-orchestrator
description: >
  当用户要求在 Claude Code 中自动完成“需求分析、方案设计、原型图设计、前后端编码、自测”的端到端流程，
  或提到“主流程”“orchestrator”“worker 模式”“不依赖 auto compact”“一个 session 编排多个阶段”时必须使用。
  本 skill 负责让主 session 只做轻量状态机、用户确认和 worker 调度，阶段执行交给隔离的 Claude Code worker。
---

# Workflow Orchestrator

本 skill 用于把长链路交付流程从“一个 Claude Code session 扛完整上下文”改成“一个主 session 编排多个隔离 worker”。

主 session 只保留当前阶段、当前 phase、目标、文件路径、用户决策和校验状态；不要把完整需求文档、完整设计文档、MCP 全量日志或代码全文放进主上下文。

## 核心原则

- 不依赖 auto compact。自动压缩只能作为兜底，不能作为流程正确性的前提。
- 用户只和主 session 交互；不要要求用户手动新建 session。
- 每个阶段由独立 worker 执行。worker 可以用 `claude -p` 启动，也可以由主 session 生成 worker prompt 后交给可用的隔离执行工具。
- 阶段之间只通过文件交接：`*-handoff.json`、`*-validation.json`、`worker-result.json`。
- 涉及人工确认时，worker 不直接提问，不等待用户输入；它必须写 `pending-questions.json` 和 `worker-result.json`，状态为 `NEED_USER_INPUT`，然后退出。
- 主 session 读取 `pending-questions.json`，用 `AskQuestion` 问用户；用户回答写入 `decisions.jsonl`，再拉起 worker 继续。
- validator 是硬门禁。上一个阶段 validation 不通过，不能进入下一阶段。

## 文件契约

每个流程运行目录必须包含：

```text
workflow-state.json
decisions.jsonl
worker-prompt.md
worker-result.json
pending-questions.json
```

运行目录选择：

- 如果已知 `product_id` 和 `product_version`，使用 `<项目根目录>/requirements/<product_id-product_version>/`。
- 如果还不知道产品和版本，先使用 `<项目根目录>/requirements/_workflow/<run_id>/`。
- requirement-analysis 完成后，如果产物位于新的产品目录，更新 `workflow-state.json.artifact_dir` 指向产品目录。

### workflow-state.json

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
  "decisions_log": "decisions.jsonl",
  "retry_count": 0,
  "max_retries": 2,
  "history": []
}
```

### pending-questions.json

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

### decisions.jsonl

每行一个用户决策：

```json
{"decision_id":"D-0001","question_batch_id":"Q-0001","question_id":"architecture.service_shape","selected":"springboot-monolith","free_text":"","decided_by":"user","decided_at":"2026-06-05T12:00:00+08:00"}
```

### worker-result.json

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

## 阶段顺序

默认阶段顺序：

1. `requirement-analysis`
2. `design-phase`
3. `prototype-design`
4. `implementation`
5. `self-test`

当前仓库已经实现前两个阶段的 handoff 和 validator。后续阶段未实现时，orchestrator 必须把状态标记为 `BLOCKED`，说明缺少对应 skill 或 validator，不要假装继续。

## 主流程

1. 初始化或读取 `workflow-state.json`。
2. 检查 `stage_status`：
   - `READY`: 生成 worker prompt 并启动 worker。
   - `NEED_USER_INPUT`: 读取 `pending-questions.json`，使用 `AskQuestion` 问用户。
   - `VALIDATION_FAILED`: 若 `retry_count < max_retries`，生成修复 worker prompt；否则停止并报告失败。
   - `COMPLETED`: 进入下一阶段。
   - `BLOCKED`: 停止并说明缺失能力或外部阻塞。
3. 用户回答后，把答案追加到 `decisions.jsonl`，清空 pending 状态，再生成下一次 worker prompt。
4. worker 结束后，读取 `worker-result.json`，更新 `workflow-state.json`。
5. 只向主上下文汇报摘要、路径和下一步；不要粘贴完整文档。

## Worker Prompt 要求

worker prompt 必须包含：

- `worker_mode: true`
- 当前 stage 和 artifact_dir。
- 必须读取的 handoff、state、decisions 文件。
- 禁止直接 AskQuestion；需要人工确认时写 `pending-questions.json` 并退出。
- 完成阶段后必须运行对应 validator。
- 最后必须写 `worker-result.json`。

worker prompt 示例：

```text
worker_mode: true
stage: design-phase
artifact_dir: D:\github\ai-agent\requirements\PVIA-2.4.0

请使用 .claude/skills/design-phase/SKILL.md。
先读取 workflow-state.json、decisions.jsonl 和 requirement-handoff.json。
不要直接向用户提问；如需用户确认，写 pending-questions.json 和 worker-result.json(status=NEED_USER_INPUT) 后停止。
如果已有 decisions 覆盖该问题，使用 decisions 继续执行。
阶段完成后生成 design-doc.md、design-handoff.json、design-validation.json，并运行 validate_design.py。
最后写 worker-result.json。
```

## 脚本

使用 bundled script 管理文件状态：

```text
python .claude/skills/workflow-orchestrator/scripts/workflow_orchestrator.py init --goal "<目标>"
python .claude/skills/workflow-orchestrator/scripts/workflow_orchestrator.py prompt --state <artifact_dir>/workflow-state.json
python .claude/skills/workflow-orchestrator/scripts/workflow_orchestrator.py record-result --state <artifact_dir>/workflow-state.json --result <artifact_dir>/worker-result.json
python .claude/skills/workflow-orchestrator/scripts/workflow_orchestrator.py add-decision --state <artifact_dir>/workflow-state.json --question-batch-id Q-0001 --question-id <id> --selected <key>
python .claude/skills/workflow-orchestrator/scripts/workflow_orchestrator.py status --state <artifact_dir>/workflow-state.json
```

如果 `claude` CLI 可用，可以使用脚本的 `run-worker` 命令自动启动 worker；如果不可用，生成 `worker-prompt.md` 后由主流程使用可用的隔离执行方式运行。

## AskQuestion 规则

主流程需要问用户时必须使用 `AskQuestion`。问题来自 `pending-questions.json`，不要重新发明问题。

每次最多问 3 个问题；如果 `pending-questions.json` 中超过 3 个，按顺序分批。用户回答后立即写入 `decisions.jsonl`，再继续调度 worker。

## 完成检查

- [ ] 主 session 没有读取或复述完整需求/设计/代码大文档。
- [ ] 每个阶段都有 `worker-result.json`。
- [ ] 需要人工确认时，问题来自 `pending-questions.json`，回答写入 `decisions.jsonl`。
- [ ] 每个阶段完成前对应 validation 为 `success=true`。
- [ ] `workflow-state.json` 的 `current_stage`、`stage_status`、`latest_handoff`、`latest_validation` 已更新。
- [ ] 不依赖 auto compact 才能继续。

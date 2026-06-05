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

## 用户入口

用户入口永远是自然语言触发本 skill，例如：

```text
根据这个 ticket URL 开始全流程
执行需求分析、方案设计、原型、编码和自测
用 workflow-orchestrator 跑完整自动化流程
```

不要要求用户手动执行 `workflow_orchestrator.py` 命令。脚本命令是本 skill 的内部实现工具，由 Claude Code 主流程在需要时自动运行。

当用户触发本 skill 后，Claude Code 主流程必须：

1. 自动调用 `workflow_orchestrator.py init` 初始化状态，或读取已有 `workflow-state.json`。
2. 自动调用 `workflow_orchestrator.py run-loop` 推进阶段。
3. 如果 run-loop 停在 `NEED_USER_INPUT`，读取 `pending-questions.json` 并用 `AskQuestion` 问用户。
4. 用户回答后，自动调用 `workflow_orchestrator.py add-decision` 写入 `decisions.jsonl`。
5. 再自动调用 `run-loop` 继续执行。

只有在调试、排障或用户明确要求看底层命令时，才展示脚本命令。

## 核心原则

- 不依赖 auto compact。自动压缩只能作为兜底，不能作为流程正确性的前提。
- 用户只和主 session 交互；不要要求用户手动新建 session。
- 用户也不需要手动运行 orchestrator 脚本；主 session 负责调用脚本和 worker。
- 每个阶段由独立 worker 执行。worker 可以用 `claude -p` 启动，也可以由主 session 生成 worker prompt 后交给可用的隔离执行工具。
- 阶段之间只通过文件交接：`*-handoff.json`、`*-validation.json`、`worker-result.json`。
- 涉及人工确认时，worker 不直接提问，不等待用户输入；它必须写 `pending-questions.json` 和 `worker-result.json`，状态为 `NEED_USER_INPUT`，然后退出。
- 主 session 读取 `pending-questions.json`，用 `AskQuestion` 问用户；用户回答写入 `decisions.jsonl`，再拉起 worker 继续。
- validator 是硬门禁。上一个阶段 validation 不通过，不能进入下一阶段。
- 子 skill 的业务流程规则优先于 orchestrator。orchestrator 只负责调度和交互转发，不能替代 requirement-analysis、design-phase 等子 skill 的抓取、分析、MCP、文档生成规则。

## 文件契约

每个流程运行目录必须包含：

```text
workflow-state.json
decisions.jsonl
worker-prompt.md
worker-result.json
pending-questions.json
worker-run-metrics.json
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

### worker-run-metrics.json

`run-worker` 命令启动 `claude -p` 后必须写该文件，用于证明 worker 真的被单独调用，并记录可从 CLI JSON 输出中提取的用量字段：

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
  "usage": {}
}
```

如果 CLI 当前版本没有在 JSON 中返回 token usage，`usage` 可能为空；这种情况下仍可通过 `worker_invocation`、`command`、`started_at`、`duration_seconds`、`returncode` 和独立输出文件证明 worker 是独立 `claude -p` 调用。

## 阶段顺序

当前启用阶段顺序：

1. `requirement-analysis`
2. `design-phase`

当前仓库只实现前两个阶段的 handoff 和 validator。`design-phase` 通过 validator 后，orchestrator 必须把全流程标记为 `COMPLETED`，不要继续启动 `prototype-design`、`implementation` 或 `self-test`。后续阶段只有在对应 skill 和 validator 实现后，才加入默认阶段顺序。

## 主流程

1. 初始化或读取 `workflow-state.json`。
2. 检查 `stage_status`：
   - `READY`: 生成 worker prompt 并启动 worker。
   - `NEED_USER_INPUT`: 读取 `pending-questions.json`，使用 `AskQuestion` 问用户。
   - `VALIDATION_FAILED`: 若 `retry_count < max_retries`，生成修复 worker prompt；否则停止并报告失败。
   - `COMPLETED`: 结束全流程。
   - `BLOCKED`: 停止并说明缺失能力或外部阻塞。
3. 用户回答后，把答案追加到 `decisions.jsonl`，清空 pending 状态，再生成下一次 worker prompt。
4. worker 结束后，读取 `worker-result.json`，更新 `workflow-state.json`。如果阶段完成且 validation 成功，自动进入下一阶段；不要询问用户“是否继续”。
5. 只向主上下文汇报摘要、路径和下一步；不要粘贴完整文档。

## Worker Prompt 要求

worker prompt 必须包含：

- `worker_mode: true`
- 当前 stage 和 artifact_dir。
- 必须读取的 handoff、state、decisions 文件。
- 第一动作必须读取对应阶段的 `SKILL.md`，并声明子 skill 规则优先。
- 明确说明 worker 模式只把 `AskQuestion` 替换成 `pending-questions.json`，不改变子 skill 的其他流程。
- 禁止直接 AskQuestion；需要人工确认时写 `pending-questions.json` 并退出。
- 完成阶段后必须运行对应 validator。
- 最后必须写 `worker-result.json`。
- 阶段完成且 validation 成功时，worker 必须直接返回 `STAGE_COMPLETED`；不要输出“是否继续下一阶段”的问题。

worker prompt 示例：

```text
worker_mode: true
stage: design-phase
artifact_dir: D:\github\ai-agent\requirements\PVIA-2.4.0

请使用 .claude/skills/design-phase/SKILL.md。
第一件事必须读取并理解 .claude/skills/design-phase/SKILL.md；子 skill 规则优先，本 prompt 只覆盖交互方式。
先读取 workflow-state.json、decisions.jsonl 和 requirement-handoff.json。
不要直接向用户提问；如需用户确认，写 pending-questions.json 和 worker-result.json(status=NEED_USER_INPUT) 后停止。
如果已有 decisions 覆盖该问题，使用 decisions 继续执行。
阶段完成后生成 design-doc.md、design-handoff.json、design-validation.json，并运行 validate_design.py。
最后写 worker-result.json。
```

### 子 skill 优先级

worker 不是“泛化任务代理”，而是“带隔离上下文的阶段执行器”。因此：

- requirement-analysis worker 必须完整遵守 `requirement-analysis/SKILL.md`，包括 ticket URL 的级联抓取策略：轻量抓取失败后自动切换 Playwright MCP 或浏览器抓取；只有 SSO 登录、缺产品版本或关键澄清点才回传主流程。
- design-phase worker 必须完整遵守 `design-phase/SKILL.md`，包括读取 `requirement-handoff.json`、区分执行动作/平台上下文动作、MCP 透明日志、`get_api_detail` 二次确认。
- 如果 worker 没有读取子 skill 就开始执行，视为流程错误；应停止并写 `worker-result.json(status=BLOCKED)`。
- 如果子 skill 与 orchestrator prompt 冲突，只有交互方式以 orchestrator 为准：直接 `AskQuestion` 改为写 `pending-questions.json`。其他流程必须听子 skill。

## 内部脚本

以下 bundled script 只供 Claude Code 主流程内部调用，用于管理文件状态；不要把它作为用户操作入口：

```text
python .claude/skills/workflow-orchestrator/scripts/workflow_orchestrator.py init --goal "<目标>"
python .claude/skills/workflow-orchestrator/scripts/workflow_orchestrator.py prompt --state <artifact_dir>/workflow-state.json
python .claude/skills/workflow-orchestrator/scripts/workflow_orchestrator.py step --state <artifact_dir>/workflow-state.json
python .claude/skills/workflow-orchestrator/scripts/workflow_orchestrator.py run-loop --state <artifact_dir>/workflow-state.json
python .claude/skills/workflow-orchestrator/scripts/workflow_orchestrator.py record-result --state <artifact_dir>/workflow-state.json --result <artifact_dir>/worker-result.json
python .claude/skills/workflow-orchestrator/scripts/workflow_orchestrator.py add-decision --state <artifact_dir>/workflow-state.json --question-batch-id Q-0001 --question-id <id> --selected <key>
python .claude/skills/workflow-orchestrator/scripts/workflow_orchestrator.py status --state <artifact_dir>/workflow-state.json
python .claude/skills/workflow-orchestrator/scripts/workflow_orchestrator.py metrics --state <artifact_dir>/workflow-state.json
```

如果 `claude` CLI 可用，可以使用脚本的 `run-worker` 命令自动启动 worker；如果不可用，生成 `worker-prompt.md` 后由主流程使用可用的隔离执行方式运行。

主流程应优先内部调用 `run-loop`，它会自动执行当前阶段、记录结果并流转到下一阶段，直到遇到以下情况才停：

- `NEED_USER_INPUT`: 需要主流程用 `AskQuestion` 问用户。
- `BLOCKED`: 缺少阶段 skill、MCP 不可用或外部阻塞。
- `COMPLETED`: 全流程完成。
- 达到 `--max-steps`。

不要把“是否进入下一阶段”作为人工确认点；阶段之间默认自动流转，只有业务事实、技术决策或风险选择才需要用户确认。不要让用户自己复制执行这些命令。

在 Windows cmd / PowerShell 中查看 worker 是否真的运行：

```text
python .claude\skills\workflow-orchestrator\scripts\workflow_orchestrator.py status --state <artifact_dir>\workflow-state.json
python .claude\skills\workflow-orchestrator\scripts\workflow_orchestrator.py metrics --state <artifact_dir>\workflow-state.json
type <artifact_dir>\worker-run-metrics.json
type <artifact_dir>\worker-cli-output.log
```

交互式主 session 的实时上下文用量由 Claude Code 自身显示：在正在运行的 `claude` 交互界面里输入 `/context`。`claude -p` worker 是非交互调用，不能在运行中输入 `/context`；用 `worker-run-metrics.json` 看该 worker 调用的结构化用量和审计信息。

## AskQuestion 规则

主流程需要问用户时必须使用 `AskQuestion`。问题来自 `pending-questions.json`，不要重新发明问题。

每次最多问 3 个问题；如果 `pending-questions.json` 中超过 3 个，按顺序分批。用户回答后立即写入 `decisions.jsonl`，再继续调度 worker。

## 完成检查

- [ ] 主 session 没有读取或复述完整需求/设计/代码大文档。
- [ ] 每个阶段都有 `worker-result.json`。
- [ ] 通过 `run-worker` 执行的阶段都有 `worker-run-metrics.json`。
- [ ] 需要人工确认时，问题来自 `pending-questions.json`，回答写入 `decisions.jsonl`。
- [ ] 每个阶段完成前对应 validation 为 `success=true`。
- [ ] `workflow-state.json` 的 `current_stage`、`stage_status`、`latest_handoff`、`latest_validation` 已更新。
- [ ] 不依赖 auto compact 才能继续。

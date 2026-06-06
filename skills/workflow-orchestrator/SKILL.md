---
name: workflow-orchestrator
description: >
  当用户要求在 Claude Code 中阶段式推进“需求分析、方案设计、原型图设计、前后端编码、自测”的端到端流程，
  或提到“主流程”“orchestrator”“worker 模式”“不依赖 auto compact”“一个 session 编排多个阶段”时必须使用。
  本 skill 负责让主 session 只做轻量状态机、用户确认和 worker 调度，阶段执行交给隔离的 Claude Code worker。
---

# Workflow Orchestrator

本 skill 把长链路交付流程拆成“主 session 编排 + 独立 worker 执行”。主 session 只保留当前阶段、状态、问题、用户决策、产物路径和审计摘要；需求分析、方案设计等重工作必须在可审计的 worker 中完成。

## 先读这个

- 用户入口永远是自然语言。不要要求用户手动执行 `workflow_orchestrator.py`，也不要把脚本命令当成下一步操作展示给用户。
- 脚本是本 skill 的内部实现工具。主流程需要时自动定位当前 `workflow-orchestrator` skill 目录下的 `scripts/workflow_orchestrator.py` 并调用。
- 不要猜固定安装路径，例如 `C:\Users\.claude`、`~/.claude` 或项目根目录下的 `.claude/skills/workflow-orchestrator`。只能从当前已加载的 `workflow-orchestrator/SKILL.md` 所在目录定位脚本。
- 执行脚本前必须做安全检查：目标文件存在，开头是 Python 脚本，例如 `#!/usr/bin/env python3`，第二行可为 `# -*- coding: utf-8 -*-`。如果开头是 `---`、`name:`、`description:` 或中文 skill 描述，说明定位到了 `SKILL.md` 或安装损坏，必须停止并报告，不要继续用 Python 执行。
- 初始化时要把用户输入写入 `workflow-input.json`。Ticket URL 使用 `--url`/`--ticket-url`，直接需求文本使用 `--input-text`/`--requirement`，本地文档使用 `--input-file`/`--document`；只有自然语言 `--goal` 时也必须按 Mode B 交给 requirement-analysis。
- 用户明确要求“全自动流程”“自动完成所有阶段”“不要人工确认”时，初始化必须使用 `--full-auto`。全自动不是跳过问题，而是由独立 AI auto-decision worker 多轮复核后把答案写入 `decisions.jsonl`。
- 当前仓库只启用 `requirement-analysis` 和 `design-phase` 两个阶段。`design-phase` 通过 validator 后，workflow 标记为 `COMPLETED`，不要继续启动原型、编码或自测阶段。

## 核心契约

- 不依赖 auto compact。上下文控制靠文件交接和 worker 隔离，自动压缩只能兜底。
- 每个阶段默认必须由脚本通过 `claude -p` 启动独立 worker。没有可审计隔离 runner 时，标记 `BLOCKED`，不要让主 session 代替 worker 执行子 skill。
- 阶段之间只通过文件交接：`*-handoff.json`、`*-validation.json`、`worker-result.json`、`workflow-state.json`、`decisions.jsonl`。
- worker 必须先读对应子 skill 的 `SKILL.md`。子 skill 的业务流程优先，orchestrator 只覆盖交互方式：worker 不能直接问用户，必须写 `pending-questions.json` 后退出。
- worker 遇到用户确认、SSO、人机验证、文件选择、外部系统操作、长时间人工处理、MCP/浏览器等不能跨进程保存的资源时，必须先写 `worker-checkpoint.json` 和必要的 `external-action.json`，再写 `worker-result.json(status=NEED_USER_INPUT)` 后退出。
- 用户回答或主流程完成外部动作后，主 session 只能写 `decisions.jsonl` 或 `external-result.json`，然后重新调用 `run-loop` 拉起 worker。禁止在主 session 里继续执行 requirement-analysis 或 design-phase。
- 全自动模式下，主 session 不替 worker 执行业务阶段；它只在 `NEED_USER_INPUT` 时调度 auto-decision worker。auto-decision worker 必须输出可审计决策，不能直接改阶段产物。
- 重新 `run-loop` 不是恢复同一个进程，而是启动新的隔离 worker。worker 必须根据 `worker-checkpoint.json`、`decisions.jsonl`、`external-result.json` 断点继续，不能重复已经完成的步骤。
- 阶段边界默认需要用户确认。需求分析完成且验证通过后，orchestrator 必须停在 `NEED_USER_INPUT`，确认需求产物可作为方案设计输入后，才能进入 `design-phase`。
- 全自动模式可以由 AI 自动确认阶段边界，但必须受 `auto_decision_rounds`、`max_auto_decisions` 和 `run-loop --max-steps` 限制；达到上限就停下来，不继续循环。
- SSO、人机验证、文件选择、外部系统操作、生产变更等需要真实外部状态的动作不能被 AI 伪确认，即使在全自动模式下也必须停在 `NEED_USER_INPUT`。

## 主流程

1. 初始化或读取 `workflow-state.json`。
2. 内部调用 `run-loop` 推进当前阶段；不要在主 session 手写或执行 worker prompt。
3. 每次 `run-loop` 后内部调用 `audit`，确认最近一次阶段是否由独立 `claude -p` worker 执行。
4. 如果状态是 `NEED_USER_INPUT`，只读取轻量文件：`pending-questions.json`、`worker-checkpoint.json`、必要的 `external-action.json` 和 `external-result.json`。
5. 如果存在 `external-action.json`，主 session 按其中的 `action_type` 完成外部动作，并把结果写入 `external-result.json`。
6. 如果需要问用户，使用 `AskQuestion` 转述 `pending-questions.json` 中的问题；不要重新发明问题。每次最多问 3 个。
7. 用户回答后写入 `decisions.jsonl`，再内部调用 `run-loop`。如果 `add-decision` 输出 `resume_worker_required=true`，下一步必须是重新调用 worker，而不是主 session 继续阶段工作。
8. 全自动模式下，如果状态是 `NEED_USER_INPUT` 且没有外部动作阻塞，内部调用 `auto-decide` 或带全自动参数的 `run-loop`，由 AI 写入 `decisions.jsonl` 后继续 worker。
9. 只向用户汇报状态、问题、产物路径、worker 审计结论、auto-decision 摘要和下一步，不粘贴完整需求/设计文档或 worker 日志。

## 主 Session 边界

主 session 可以读取和总结：

- `workflow-state.json` 的轻量状态。
- `worker-result.json` 的 `status`、`summary`、`next_action` 和产物路径。
- `pending-questions.json` 中需要问用户的问题。
- `decisions.jsonl` 中用户刚回答的决策。
- `status` / `audit` / `metrics` 的 worker 证明摘要。

主 session 默认不要读取：

- `worker-prompt.md`
- `worker-cli-output.log`
- 完整需求文档、完整设计文档、MCP 全量日志
- 子 skill 的完整正文，除非正在排障或修改 skill 本身

如果主 session 发现必须读取这些大文件才能继续，说明阶段执行没有正确封装；应重新调度 worker 或标记 `BLOCKED`，不要把子 skill 的工作搬回主 session。

## Worker Prompt 最小要求

worker prompt 必须包含：

- `worker_mode: true`
- 当前 `stage`、`artifact_dir` 和必须读取的 state/handoff/decisions 文件。
- 对应子 skill 的 `SKILL.md` 路径，并要求 worker 第一件事读取它。
- 子 skill 优先级声明：除交互方式外，不改写子 skill 的业务阶段、抓取、分析、MCP、文档生成和 validator 规则。
- 禁止直接 `AskQuestion`；需要用户确认时写 `pending-questions.json`、`worker-checkpoint.json` 和 `worker-result.json(status=NEED_USER_INPUT)`。
- 阶段完成后必须运行对应 validator，并写 `worker-result.json`。
- 阶段完成且 validator 成功时，worker 直接返回 `STAGE_COMPLETED`；是否进入下一阶段由 orchestrator 在主 session 统一处理。

## 何时读 References

- 需要精确 JSON schema、目录选择或文件契约时，读 `references/file-contracts.md`。
- 用户询问“主线程上下文占用”“worker 是否独立上下文”“到底有没有用 worker”或需要审计报告时，读 `references/context-worker-audit.md`。
- 需要判断 worker 内部是否启用 subAgent、或用户问“subAgent 放在 worker 里有没有必要”时，读 `references/worker-subagents.md`。
- 需要解释或排障全自动确认时，读 `references/full-auto.md`。
- 需要排障脚本定位、Windows 编码、`claude -p` 权限、内部命令或 run-loop 行为时，读 `references/internal-script-operations.md`。
- 后续要增加原型、编码、自测等阶段时，读 `references/extending-stages.md`。

## AskQuestion 规则

主流程需要问用户时必须使用 `AskQuestion`。问题来自 `pending-questions.json`，每次最多问 3 个；如果超过 3 个，按顺序分批。用户回答后立刻写入 `decisions.jsonl`，再继续调度 worker。

## 完成检查

- 主 session 没有读取或复述完整需求/设计/代码大文档。
- 每个阶段都有 `worker-result.json`。
- 通过 worker 执行的阶段都有 `worker-run-metrics.json`。
- 需要人工确认时，问题来自 `pending-questions.json`，回答写入 `decisions.jsonl`。
- 每个阶段完成前对应 validation 为 `success=true`。
- `workflow-state.json` 的 `current_stage`、`stage_status`、`latest_handoff`、`latest_validation` 已更新。
- worker 审计结论能说明最近一次阶段是否由独立 `claude -p` 调用完成。

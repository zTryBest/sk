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
- 初始化时要把用户输入写入 `workflow-input.json`。Ticket URL 使用 `--url`/`--ticket-url`，直接需求文本使用 `--input-text`/`--requirement`，本地文档使用 `--input-file`/`--document`；如果没有显式 `--goal`，脚本会根据输入自动生成默认目标。只有自然语言 `--goal` 时也必须按 Mode B 交给 requirement-analysis。
- 初始化默认复用同一项目、同一输入、同一阶段下最近的活动 workflow，避免纠错时重复创建 `_workflow/<run_id>` 目录。只有用户明确要求新建或内部确实需要并行 workflow 时，才使用 `--no-reuse-existing`、`--run-id` 或 `--artifact-dir`。
- 内部脚本兼容 `--artifact-dir` 和 `--artifacts-dir`，二者含义相同；`status` 可用 `--state` 或 `--artifact-dir/--artifacts-dir` 定位状态，不要无状态调用。
- 用户明确要求“全自动流程”“自动完成所有阶段”“不要人工确认”时，初始化必须使用 `--full-auto`。全自动不是跳过问题，而是由独立 AI auto-decision worker 多轮复核后把答案写入 `decisions.jsonl`。
- 用户没有说明全自动或人工阶段时，默认确认策略是：`requirement-analysis` 需要人工确认，其他阶段使用 AI 自动确认。也就是需求澄清、需求产物进入方案设计前必须停给用户；方案设计及后续阶段的普通确认点默认由 auto-decision worker 审计后确认。
- 用户可以自然语言指定人工确认阶段，例如“需求分析和方案设计都人工确认”“只有方案设计人工确认”“需求分析人工，后面自动”。主流程初始化时映射为 `--manual-confirm-stages <stage-list>`；如果用户指定某阶段自动确认，映射为 `--ai-confirm-stages <stage-list>`。
- 当前仓库只启用 `requirement-analysis` 和 `design-phase` 两个阶段。`design-phase` 通过 validator 后，workflow 标记为 `COMPLETED`，不要继续启动原型、编码或自测阶段。

## 核心契约

- 不依赖 auto compact。上下文控制靠文件交接和 worker 隔离，自动压缩只能兜底。
- 每个阶段默认必须由脚本通过 `claude -p` 启动独立 worker。没有可审计隔离 runner 时，标记 `BLOCKED`，不要让主 session 代替 worker 执行子 skill。
- 阶段之间只通过文件交接：`*-handoff.json`、`*-validation.json`、`worker-result.json`、`workflow-state.json`、`decisions.jsonl`。
- 所有 JSON 交接文件必须通过 JSON serializer 写入，禁止手工拼接 JSON 字符串。写完必须重新 `json.load` 校验，尤其是验收标准、问题描述、API 示例中包含双引号、反斜杠或换行时。
- 如果 `*-validation.json` 报告 `invalid JSON`、`JSONDecodeError`、`Expecting delimiter` 或 `Invalid control character`，主 session 只读取 validation 中的错误行列和短 `json_error.context`，然后重新调度 worker 用 serializer 重写 JSON。不要在主 session 展开读取完整 handoff/Markdown，也不要把优先排查方向转成 BOM 或隐藏字符。
- worker 必须先读对应子 skill 的 `SKILL.md`。子 skill 的业务流程优先，orchestrator 只覆盖交互方式：worker 不能直接问用户，必须写 `pending-questions.json` 后退出。
- worker 遇到用户确认、SSO、人机验证、文件选择、外部系统操作、长时间人工处理、MCP/浏览器等不能跨进程保存的资源时，必须先写 `worker-checkpoint.json` 和必要的 `external-action.json`，再写 `pending-questions.json` 和 `worker-result.json(status=NEED_USER_INPUT)` 后退出；禁止只写 pending 不写 result。
- worker 写文件优先使用 Write/Edit/MultiEdit 或结构化 Python serializer。禁止用 shell heredoc、`cat > file`、`echo ... > file` 或把大段 JSON 嵌进 `python -c "..."`；遇到 Bash 权限拒绝时立即换工具或写 `worker-result.json(status=BLOCKED)`，不要反复消耗 turns。
- 如果 worker 因 max-turns 被截断但已经留下 `pending-questions.json` 或 `worker-checkpoint.json`，orchestrator 可以自动恢复到 `NEED_USER_INPUT` 或 `READY`。同一 pending/checkpoint 重复恢复超过上限后才标记 `BLOCKED`，避免死循环。
- 如果 worker 因 max-turns 被截断但已经留下阶段草稿或 handoff Markdown，orchestrator 恢复为 `READY` 并标记 `finalize-recovery`；下一轮只启动收尾 worker 补 `*-handoff.json`、`*-validation.json` 和 `worker-result.json`，主 session 不读取大文档手动收尾。
- 如果只在 `worker-cli-output.log` 里看到了完整 handoff，但没有 pending/checkpoint/可收尾产物，主 session 也不能从日志手工抽 JSON 补交接文件；应重新调度 worker、调整 worker 权限或标记 `BLOCKED`。
- 用户回答或主流程完成外部动作后，主 session 只能写 `decisions.jsonl` 或 `external-result.json`，然后重新调用 `run-loop` 拉起 worker。禁止在主 session 里继续执行 requirement-analysis 或 design-phase。
- 全自动模式下，主 session 不替 worker 执行业务阶段；它只在 `NEED_USER_INPUT` 时调度 auto-decision worker。auto-decision worker 必须输出可审计决策，不能直接改阶段产物。
- 重新 `run-loop` 不是恢复同一个进程，而是启动新的隔离 worker。worker 必须根据 `worker-checkpoint.json`、`decisions.jsonl`、`external-result.json` 断点继续，不能重复已经完成的步骤。
- 阶段边界是否人工确认由 `manual_confirmation_stages` 决定。默认只有 `requirement-analysis` 在阶段内部确认点和阶段完成边界停给用户；其他阶段的确认点由 AI 自动确认。
- 全自动模式下 `manual_confirmation_stages=[]`，每个阶段都无需人工确认，但仍必须受 `auto_decision_rounds`、`max_auto_decisions` 和 `run-loop --max-steps` 限制；达到上限就停下来，不继续循环。
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
- validation 文件里的 `errors`、`warnings` 和 `json_error` 短上下文。

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
- `finalize-recovery` 模式下，worker 只读取已有阶段产物并补齐缺失机器文件；不要重新抓取 URL、重新跑完整需求分析或完整方案设计。
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
- worker 被截断时，如果存在 pending/checkpoint，状态已通过恢复机制处理；如果同一恢复签名反复出现，流程会停止而不是无限加 turns。
- 需要人工确认时，问题来自 `pending-questions.json`，回答写入 `decisions.jsonl`。
- 每个阶段完成前对应 validation 为 `success=true`。
- `workflow-state.json` 的 `current_stage`、`stage_status`、`latest_handoff`、`latest_validation` 已更新。
- worker 审计结论能说明最近一次阶段是否由独立 `claude -p` 调用完成。

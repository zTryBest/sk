# Context And Worker Audit

当用户问“主线程上下文占用”“worker 是否独立上下文”“到底有没有用 worker”时，按本文件回答和排查。

## Claude Code 支持边界

本 workflow 依赖 Claude Code 已支持的能力：

- `claude -p` 非交互调用，用于启动一次性 worker。
- `--output-format json` / `stream-json`，用于脚本化审计 worker 输出。
- `--permission-mode`、`--allowed-tools`、`--add-dir`，用于控制 worker 权限和可访问目录。
- subAgent / custom agent 的独立上下文和工具限制，用于 worker 内部可选局部检索或审查。
- MCP / 浏览器等工具能力，用于主 session 或 worker 在各自可用环境中执行工具动作。

本 workflow 自己定义的能力：

- `workflow-state.json`、`worker-checkpoint.json`、`external-action.json`、`external-result.json`、`decisions.jsonl` 是本 skill 的文件协议，不是 Claude Code 内建状态机。
- Claude Code 不会自动持久化 worker 的 Playwright 浏览器、MCP 连接、临时进程或内存对象给下一次 `claude -p` 调用。任何跨 worker 的恢复都必须通过文件化 checkpoint 和结果文件完成。
- 重新 `run-loop` 的含义是“启动新的隔离 worker，并要求它读取 checkpoint/decisions/external-result 后断点继续”。

## 主 Session 精确上下文占用

- 精确占用只能由 Claude Code 交互 session 自己显示，例如用户在当前主 session 输入 `/context`。
- `workflow_orchestrator.py` 和子 worker 不能准确读取当前交互式主 session 的 `/context` 数字。
- 不要让用户运行 shell 命令来查看主 session 上下文；只提示在当前 Claude Code 主 session 输入 `/context`。

## 主 Session 健康判断

主 session 只能做结构性判断：

- 是否只读取了 `workflow-state.json`、`worker-result.json`、`pending-questions.json`、`worker-run-metrics.json` 等轻量文件。
- 是否避免读取完整需求文档、完整设计文档、`worker-cli-output.log`、MCP 全量日志。
- 如果主 session 已经读取上述大文件，应视为上下文边界被破坏，需要后续收敛回轻量状态，不要继续把阶段工作搬到主 session。

## Worker 独立性证据

主流程内部调用 `audit`，重点检查：

- `worker_isolation_ok`
- `worker_proof`
- `worker_invocation=claude -p`
- 命令包含 `-p` 或 `--print`
- 没有 `--resume` / `--continue`
- 包含 `--no-session-persistence`
- 存在 `worker-run-metrics.json` 和 `worker-result.json`

如果 CLI JSON 返回 `session_id`、`usage`、`num_turns`、`total_cost_usd`，可以作为 worker 运行证据。没有返回时，不应单独视为失败。

## 正常报告格式

面向用户时保持轻量：

```text
主 session 精确占用：请在当前 Claude Code 主 session 输入 /context 查看；本 skill 不从脚本读取该数字。
主 session 边界：本轮只读取了 workflow-state / pending-questions / worker-result / metrics 等轻量文件，未读取大文档或日志。
worker 隔离：已通过/未通过。证据：claude -p、无 resume/continue、no-session-persistence、metrics 路径。
AI 自动确认：启用/未启用；已自动确认次数；auto-decisions.jsonl 路径；若停止，说明是否因为外部动作或上限。
当前阶段状态：READY/NEED_USER_INPUT/COMPLETED/BLOCKED。
```

不要把 `worker-cli-output.log` 粘贴到主 session。只有用户明确要求排障时，说明日志路径和关键结论。

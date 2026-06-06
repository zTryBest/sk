# Internal Script Operations

本文件只给 orchestrator 主流程内部使用。不要把这里的命令当成用户操作步骤展示。

## 脚本定位

- 使用当前已加载的 `workflow-orchestrator/SKILL.md` 所在目录。
- 拼接 `scripts/workflow_orchestrator.py`。
- 不要猜 `C:\Users\.claude`、`~/.claude` 或项目根目录下固定路径。
- 执行前确认目标文件存在，且开头是 Python 脚本。如果开头是 `---`、`name:`、`description:` 或中文 skill 描述，说明定位错了或安装损坏，停止执行并报告。

## 内部调用表

```text
python <workflow-orchestrator-skill-dir>/scripts/workflow_orchestrator.py init --goal "<目标>" [--url "<ticket URL>"] [--input-text "<直接需求文本>"] [--input-file "<需求文档路径>"]
python <workflow-orchestrator-skill-dir>/scripts/workflow_orchestrator.py prompt --state <artifact_dir>/workflow-state.json
python <workflow-orchestrator-skill-dir>/scripts/workflow_orchestrator.py step --state <artifact_dir>/workflow-state.json
python <workflow-orchestrator-skill-dir>/scripts/workflow_orchestrator.py run-loop --state <artifact_dir>/workflow-state.json
python <workflow-orchestrator-skill-dir>/scripts/workflow_orchestrator.py record-result --state <artifact_dir>/workflow-state.json --result <artifact_dir>/worker-result.json
python <workflow-orchestrator-skill-dir>/scripts/workflow_orchestrator.py add-decision --state <artifact_dir>/workflow-state.json --question-batch-id Q-0001 --question-id <id> --selected <key>
python <workflow-orchestrator-skill-dir>/scripts/workflow_orchestrator.py status --state <artifact_dir>/workflow-state.json
python <workflow-orchestrator-skill-dir>/scripts/workflow_orchestrator.py audit --state <artifact_dir>/workflow-state.json
python <workflow-orchestrator-skill-dir>/scripts/workflow_orchestrator.py metrics --state <artifact_dir>/workflow-state.json
```

主流程应优先内部调用 `run-loop`。它会自动执行当前阶段并记录结果。默认不跨阶段全自动继续；阶段完成且 validator 通过后，会写入阶段边界确认问题并停在 `NEED_USER_INPUT`。只有内部显式配置 `auto_advance_stages=true` 时才自动进入下一阶段。

初始化输入规则：

- 用户给 ticket URL 时，内部使用 `--url` 或 `--ticket-url`，脚本写入 `workflow-input.json(source_type=ticket_url)`。
- 用户直接描述需求时，内部使用 `--input-text` 或仅把完整需求放入 `--goal`，脚本写入 `workflow-input.json(source_type=manual_text|goal_only)`。
- 用户给本地需求文档时，内部使用 `--input-file` 或 `--document`，脚本写入 `workflow-input.json(source_type=document_file)`，worker 会被授予文档所在目录的读取权限。
- 不要让用户手动执行这些命令；它们只是主流程内部接口。

## 状态含义

- `READY`：可以生成 worker prompt 并启动 worker。
- `NEED_USER_INPUT`：需要主流程读取 `pending-questions.json` 或 `external-action.json`，然后问用户或完成外部动作。
- `VALIDATION_FAILED`：如果 `retry_count < max_retries`，重新调度修复 worker；否则停下报告失败。
- `BLOCKED`：缺少阶段 skill、MCP 不可用、缺少可审计 runner 或外部阻塞。
- `COMPLETED`：当前启用的 workflow 阶段全部完成。

## Worker 调用要求

脚本通过 `run-worker` / `run-loop` 自动启动 `claude -p` worker。worker 默认应带：

- `--permission-mode acceptEdits`
- `--add-dir` 当前项目、产物目录和阶段 skill 目录
- `--allowed-tools Read,Write,Edit,MultiEdit,Glob,Grep,LS,WebFetch,WebSearch,Bash(python *),Bash(py *)`
- `--no-session-persistence`
- `--output-format json`

如果 `claude` CLI 不可用，主流程只能生成 `worker-prompt.md` 供排障查看，不能在主 session 手工执行该 prompt；此时应报告缺少可审计隔离 runner 或标记 `BLOCKED`。

## Windows 和中文排障

- Python 脚本必须包含 UTF-8 声明：`# -*- coding: utf-8 -*-`。
- 内部调用 Python 时应设置 UTF-8 环境，例如 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`；脚本自身也应对 stdout/stderr 做 UTF-8 reconfigure。
- 如果出现 `SyntaxError: invalid character '、' (U+3001)` 且报错行是 skill 的中文描述，通常不是中文编码问题，而是 Python 执行到了 `SKILL.md` 或损坏的 `.py` 文件。
- 这种情况必须先做脚本定位安全检查：确认真正执行的是 `scripts/workflow_orchestrator.py`，且文件开头是 shebang 和 Python 代码。

## 排障原则

- 每次 `run-loop` 后内部调用 `audit`，只向用户汇报审计结论。
- `worker-cli-output.log` 可能很大，只在用户明确要求排障时查看。
- 交互式主 session 的实时上下文用量由 Claude Code 自身显示：让用户在当前主 session 输入 `/context`。不要让用户通过 shell 命令查询。

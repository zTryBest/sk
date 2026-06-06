# Extending Stages

当前 workflow 只启用：

1. `requirement-analysis`
2. `design-phase`

后续补充原型、编码、自测等阶段时，按本文件扩展。不要只改 `SKILL.md` 文案；必须让脚本、子 skill、validator 和 handoff 同步存在。

## 新增阶段前提

每个阶段至少需要：

- `.claude/skills/<stage>/SKILL.md`
- 明确的 worker-mode overlay：如何读取 state/decisions/checkpoint/external-result，如何把直接 AskQuestion 改成写 `pending-questions.json`
- 阶段产物文件
- `<stage>-handoff.json`
- `<stage>-validation.json`
- validator 脚本或等价验证机制
- `worker-result.json` 写入规则

## 脚本需要同步修改

在 `scripts/workflow_orchestrator.py` 中同步更新：

- `STAGES`
- `VALIDATION_BY_STAGE`
- `HANDOFF_BY_STAGE`
- 如需 subAgent，更新 `DEFAULT_WORKER_SUBAGENTS` 和 `STAGE_WORKER_SUBAGENTS`
- 如阶段需要特殊 prompt 提醒，更新 `generate_worker_prompt` 中的 stage-specific notes
- 如果新阶段有新 validator 或交接路径，确保 `record-result` 能找到并记录

## 主 skill 需要同步修改

在 `workflow-orchestrator/SKILL.md` 中更新：

- “当前仓库只启用...” 的阶段说明
- “当前阶段完成后是否 `COMPLETED`” 的规则
- 如阶段边界确认策略不同，补充主流程边界规则

不要把新阶段的完整业务步骤塞进 orchestrator 主 `SKILL.md`。业务细节应放在对应子 skill；orchestrator 只写调度、交互和文件交接规则。

## 子 skill 需要遵守的 worker-mode 规则

新增子 skill 中保留原业务步骤，但增加 worker-mode overlay：

- 第一动作读取 `workflow-state.json`、`decisions.jsonl`、`worker-checkpoint.json`、`external-result.json` 和上一阶段 handoff。
- 如果 checkpoint 存在且 required inputs 已满足，从 `resume_from` 继续，不重复 `completed_steps`。
- 需要用户确认时，不直接问用户；写 `worker-checkpoint.json`、`pending-questions.json`、`worker-result.json(status=NEED_USER_INPUT)` 后退出。
- 需要主 session 或用户完成外部动作时，额外写 `external-action.json`。
- 阶段完成后运行 validator，成功后写 `worker-result.json(status=STAGE_COMPLETED)`。
- 是否进入下一阶段由 orchestrator 处理，不由子 skill 自己推进。

## 阶段边界

默认策略是阶段完成后停在 `NEED_USER_INPUT`，由用户确认是否进入下一阶段。只有主流程内部显式设置 `auto_advance_stages=true`，才允许自动推进。

如果某个阶段必须全自动推进，要在该阶段说明原因，并确认不会跳过用户需要确认的业务事实。

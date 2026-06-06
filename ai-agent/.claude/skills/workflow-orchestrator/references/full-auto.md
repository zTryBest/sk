# Full Auto Mode

全自动模式用于用户明确说“全自动流程”“自动完成所有阶段”“不要人工确认”的情况。

## 设计原则

- 全自动不等于跳过问题。worker 仍按子 skill 规则在确认点写 `pending-questions.json`。
- orchestrator 在 `NEED_USER_INPUT` 时启动独立 `claude -p` auto-decision worker，由它多轮复核并写入 AI 决策。
- 主 session 不执行 requirement-analysis 或 design-phase 的业务工作，只调度 worker 和记录状态。
- 每个 AI 决策写入 `decisions.jsonl(decided_by=ai-auto)`，并追加 `auto-decisions.jsonl` 供审计。

## 推荐内部参数

初始化全自动流程：

```text
python <workflow-orchestrator-skill-dir>/scripts/workflow_orchestrator.py init --goal "<目标>" --full-auto --auto-decision-rounds 3 --max-auto-decisions 20
```

推进全自动流程：

```text
python <workflow-orchestrator-skill-dir>/scripts/workflow_orchestrator.py run-loop --state <artifact_dir>/workflow-state.json --full-auto --max-steps 12
```

这些命令仍然是主流程内部调用，不展示给用户执行。

## Auto-Decision 行为

auto-decision worker 会做多轮复核：

1. 事实复核：梳理已知事实、问题、选项和默认项。
2. 风险复核：检查范围、数据来源、权限、安全、外部系统、不可逆动作风险。
3. 最终决策：证据足够时选择选项；证据不足时保持 `NEED_USER_INPUT`。

输出只保留简短 review summary、选择、置信度和理由，不输出长推理链。

## 停止条件

即使全自动，也必须停止并等待主流程/用户处理：

- SSO 登录
- 人机验证
- 文件选择
- 外部系统操作
- 生产变更、删除、付款、法律/合规承诺
- auto-decision worker 无法给出安全选择，且没有 `default_if_full_auto` 或推荐选项
- 达到 `max_auto_decisions`
- 达到 `run-loop --max-steps`

## 和 auto-advance 的区别

- `--auto-advance`：阶段 validation 成功后直接进入下一阶段，不生成阶段边界确认。
- `--full-auto`：保留确认点，但由 AI 自动确认，留下审计记录。

优先使用 `--full-auto`。只有明确不需要阶段边界复核时，才使用 `--auto-advance`。

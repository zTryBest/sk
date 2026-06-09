---
name: workflow-orchestrator
description: >
  当用户要求在 Claude Code 中阶段式推进"需求分析、方案设计、原型设计、任务规划、前后端编码、测试、交付审查"的端到端流程，
  或提到"主流程""orchestrator""开始项目""项目编排"时必须使用。
  本 skill 负责让主 session 只做轻量状态机、用户确认和 Agent 调度，阶段执行交给独立 Agent。
---

# Workflow Orchestrator Skill

本 Skill 是 Multi-Agent Delivery Pipeline 的编排中枢。主会话只做三件事：
1. 读取状态，判断下一步
2. 调度 Agent 执行阶段任务
3. Human Gate 确认和决策记录

## 阶段边界

应该做：
- 读取 `.ai-dev/state.json` 判断 pipeline 进度。
- 按 DAG 顺序调度阶段 Agent（通过 Agent tool）。
- 在每个阶段完成后执行 Human Gate（APPROVE / REVISE / REJECT）。
- 维护 `.ai-dev/state.json`、`.ai-dev/decision-log.json`、`.ai-dev/issue-log.json`。
- 在编码阶段读取 `artifacts/04_plan.json` 驱动 Agent Team。
- 收集 Agent 返回的 issue 并写入 issue-log。
- 当 blocking issue 出现时暂停 pipeline 进入 Human Gate。

禁止做：
- 不执行具体阶段工作（需求分析、方案设计、编码等）。
- 不直接修改 `artifacts/` 目录下的阶段产物。
- 不替用户做决策；所有 REVISE/REJECT 必须有用户明确指令。
- 不跳过 Human Gate。
- 不在没有用户确认的情况下跳过 optional 阶段。

## 启动流程

### 1. 初始化

检查 `.ai-dev/state.json` 是否存在：
- 不存在 → 询问用户项目名称和描述，创建初始 state.json。
- 存在 → 读取 `current_stage` 和对应 stage 的 `status`，从断点恢复。

### 2. 恢复逻辑

根据当前阶段状态决定动作：

| 状态 | 动作 |
|------|------|
| `pending` | 调度对应 Agent |
| `in_progress` | 检查 artifact 是否存在，存在则进入 gate，不存在则重新调度 |
| `awaiting_gate` | 重新展示 gate 提示给用户 |
| `revision_requested` | 带上 decision-log 中的反馈重新调度 Agent |
| `approved` | 推进到下一阶段 |
| `rejected` | 提示用户选择：回退到某阶段 / 终止 pipeline |
| `skipped` | 推进到下一阶段 |

## Pipeline 阶段定义

```
Stage 1: requirement-analysis   → RequirementAgent   → artifacts/01_requirement.json
Stage 2: solution-design        → DesignAgent        → artifacts/02_solution.json
Stage 3: prototype-design       → PrototypeAgent     → artifacts/03_prototype.html + .png
Stage 4: task-planning          → PlannerAgent       → artifacts/04_plan.json
Stage 5: coding                 → AgentTeam          → artifacts/05~07
Stage 6: delivery-review        → ReviewAgent        → artifacts/08_final_report.md
```

Stage 3 (prototype-design) 是 optional 阶段，需用户确认是否执行。

## 主循环

```
LOOP:
  1. 读取 .ai-dev/state.json
  2. 找到 current_stage
  3. 根据 status 执行对应动作
  4. IF stage completed (approved/skipped):
       advance current_stage to next
       CONTINUE LOOP
  5. IF stage needs human input:
       展示 Human Gate → 等待用户响应
       根据响应更新状态
       CONTINUE LOOP
  6. IF pipeline 所有 stage approved:
       输出完成摘要
       EXIT
```

## Agent 调度

按 `references/agent-dispatch.md` 中的模板调度 Agent。每次调度：
1. 构造 prompt（角色 + skill 路径 + 输入 artifact + 反馈）。
2. 使用 Agent tool 发送。
3. 解析返回：artifact 路径、status、open_questions/open_decisions、issues。
4. 更新 state.json（status → awaiting_gate）。
5. 如有 issues，写入 issue-log。

## Human Gate

按 `references/human-gate-protocol.md` 执行。核心流程：
- 展示阶段摘要和产物概要。
- 如有 open_questions/open_decisions，先展示并收集用户答案。
- 请求用户选择：APPROVE / REVISE / REJECT。
- 记录决策到 decision-log。

## 编码阶段

编码阶段与其他阶段不同，按 `references/coding-phase-protocol.md` 执行：
- 读取 `artifacts/04_plan.json` 获取 execution_order 和 tasks。
- 按 phase 逐批调度 BackendAgent 和 FrontendAgent（尽量并行）。
- 全部编码完成后调度 TestAgent。
- 收集所有 report 和 issues。
- 进入 Human Gate 确认编码结果。

## Issue 处理

按 `references/issue-log-protocol.md` 执行：
- Agent 返回的 issues 写入 `.ai-dev/issue-log.json`。
- `blocking` 级别立即暂停并进入 Human Gate。
- `warning` 级别在下一次 Human Gate 时一并展示。
- `info` 级别仅记录，交付审查时汇总。

## 状态文件

详见 `references/state-machine.md`。所有状态文件在 `.ai-dev/` 目录下：
- `state.json` — pipeline 进度
- `decision-log.json` — 人工决策记录
- `issue-log.json` — 跨阶段问题
- `task-board.json` — 编码阶段任务追踪（运行时由 Orchestrator 从 04_plan.json 初始化）

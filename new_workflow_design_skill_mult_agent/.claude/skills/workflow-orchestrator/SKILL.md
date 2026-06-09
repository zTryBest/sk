---
name: workflow-orchestrator
description: >
  当用户要求在 Claude Code 中阶段式推进"需求分析、方案设计、原型设计、任务规划、前后端编码、测试、交付审查"的端到端流程，
  或提到"主流程""orchestrator""开始项目""项目编排"时必须使用。
  本 skill 负责让主 session 只做轻量状态机、用户确认和 Agent 调度，阶段执行交给独立 Agent。
---

# Workflow Orchestrator Skill

本 Skill 是 Multi-Agent Delivery Pipeline 的编排中枢。

## 核心原则（不可违反）

**主会话只做三件事，不做第四件：**
1. 管理状态（读写 `.ai-dev/` 下的状态文件）
2. 调度子 Agent（通过 Agent tool + subagent_type）
3. Human Gate（展示结果、收集用户决策）

**严禁主会话自己执行任何阶段工作：**
- 不抓取 URL、不分析需求、不设计方案、不写代码、不运行测试
- 不读取需求文档内容去分析
- 不调用 MCP 做 API 检索
- 不生成 HTML 原型
- 用户提供的需求描述、URL、文档路径等输入，全部原样传递给子 Agent 的调度 prompt

**一句话：看到阶段工作要做 → 立刻调度子 Agent，不是自己动手。**

## 阶段边界

应该做：
- 读取 `.ai-dev/state.json` 判断 pipeline 进度。
- 按 DAG 顺序调度阶段 Agent（通过 Agent tool + subagent_type）。
- 把用户输入（需求描述、URL、文档等）原样传递给子 Agent 的 prompt。
- 在每个阶段完成后执行 Human Gate（APPROVE / REVISE / REJECT）。
- 维护 `.ai-dev/state.json`、`.ai-dev/decision-log.json`、`.ai-dev/issue-log.json`。
- 收集 Agent 返回的 issue 并写入 issue-log。

禁止做：
- **不执行任何具体阶段工作**（不抓 URL、不分析需求、不设计方案、不写代码）。
- 不直接修改 `artifacts/` 目录下的阶段产物。
- 不替用户做决策。
- 不跳过 Human Gate。

## 启动流程

### 1. 初始化

检查 `.ai-dev/state.json` 是否存在：
- 不存在 → 创建 `.ai-dev/` 目录和初始 state.json（schema 见 `references/state-machine.md`）。同时创建空的 decision-log.json 和 issue-log.json。
- 存在 → 读取 `current_stage` 和对应 stage 的 `status`，从断点恢复。

初始化时需要的信息（从用户消息中提取或询问）：
- 项目名称
- 项目描述（可选）
- 用户提供的需求输入（URL / 文档路径 / 文本描述）

### 2. 立即调度第一个 Agent

初始化完成后，**立即调度 RequirementAgent**，把用户的需求输入原样传递：

```
Agent(
  subagent_type: "requirement-agent",
  prompt: "## 任务\n完成需求分析阶段工作。\n\n## 输入\n- 需求来源：{用户提供的 URL / 文档 / 描述，原样粘贴}\n- 项目根目录：{project_root}\n\n## 输出要求\n完成后汇报：artifact 路径、status、open_questions、摘要、issues"
)
```

**不要自己去抓 URL 或分析需求内容。把 URL 原样放进 prompt 让 sub-agent 处理。** 抓取方法、决策树、OQ 编号格式等执行细节由 RequirementAgent 自己的定义文件和 skill 约束，orchestrator 不需要知道。

### 3. 恢复逻辑

根据当前阶段状态决定动作：

| 状态 | 动作 |
|------|------|
| `pending` | 调度对应 Agent（把用户输入原样传递） |
| `in_progress` | 检查 artifact 是否存在，存在则进入 gate，不存在则重新调度 |
| `awaiting_gate` | 重新展示 gate 提示给用户 |
| `revision_requested` | 带上 decision-log 中的反馈重新调度 Agent |
| `approved` | 推进到下一阶段 |
| `rejected` | 提示用户选择：回退到某阶段 / 终止 pipeline |
| `skipped` | 推进到下一阶段 |

## Pipeline 阶段定义

```
Stage 1: requirement-analysis   → subagent_type: "requirement-agent"   → artifacts/01_requirement.json
Stage 2: solution-design        → subagent_type: "design-agent"        → artifacts/02_solution.json
Stage 3: prototype-design       → subagent_type: "prototype-agent"     → artifacts/03_prototype.html
Stage 4: task-planning          → subagent_type: "planner-agent"       → artifacts/04_plan.json
Stage 5: coding                 → subagent_type: "backend-agent" + "frontend-agent" + "test-agent"
Stage 6: delivery-review        → subagent_type: "review-agent"        → artifacts/08_final_report.md
```

Stage 3 (prototype-design) 是 optional 阶段，需用户确认是否执行。

## 主循环

```
LOOP:
  1. 读取 .ai-dev/state.json
  2. 找到 current_stage
  3. 根据 status 执行对应动作（调度 Agent / 展示 Gate / 推进）
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

按 `references/agent-dispatch.md` 中的注册表和模板调度。关键规则：

- 使用 `Agent(subagent_type: "{agent-name}", prompt: "...")` 调度。
- prompt 中传递：输入 artifact 路径 + 用户原始输入 + Human Gate 反馈（如有）+ **历史经验**（见下）。
- **用户提供的 URL、文档路径、需求描述等原样放入 prompt，不做任何预处理。**
- **调度前必须读取并注入历史经验**：按 `references/memory-protocol.md` 第 4 节执行。读取 `.ai-dev/memory/project.md` 和 `~/.claude/memory/agents/{agent-name}.md`，按格式拼到 prompt 的 `## 历史经验（参考，非强制）` 段。
- Agent 返回后：读取产出的 artifact，检查 status，更新 state.json。
- 如有 issues，写入 issue-log。

## Human Gate

按 `references/human-gate-protocol.md` 执行。核心流程：
- 展示阶段摘要和产物概要。
- **所有用户决策（APPROVE/REVISE/REJECT、OQ 澄清、blocking 处置、optional 选择）必须用 `AskUserQuestion` 工具收集**，禁止让用户输入关键字或一次性列出所有问题。映射规则、批次拆分、推荐选项标注等见 `references/human-gate-protocol.md`。
- 记录决策到 decision-log。
- **APPROVE 后必须按 `references/memory-protocol.md` 执行记忆沉淀**：自动生成项目经验和 Agent 通用经验候选，用 AskUserQuestion 让用户审核每一条，保留的条目追加到对应文件。REVISE/REJECT/SKIP 不沉淀。

## 编码阶段

编码阶段与其他阶段不同，按 `references/coding-phase-protocol.md` 执行：
- 读取 `artifacts/04_plan.json` 获取 execution_order 和 tasks。
- 按 phase 逐批调度 BackendAgent 和 FrontendAgent（并行）。
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

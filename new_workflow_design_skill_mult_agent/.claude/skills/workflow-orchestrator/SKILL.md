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

**首次初始化时必须记录 `project_root`**（当前 Claude Code 工作目录的绝对路径）。所有 `.ai-dev/` / `artifacts/` / `workspace/` 操作均基于此路径，存储为 state.json 的 `project_root` 字段。

检查 `<project_root>/.ai-dev/state.json` 是否存在：
- 不存在 → 创建 `<project_root>/.ai-dev/` 目录和初始 state.json（schema 见 `references/state-machine.md`，含 `project_root` 字段）。同时创建空的 decision-log.json 和 issue-log.json。
- 存在 → 读取 `project_root` + `current_stage` 和对应 stage 的 `status`，从断点恢复。**即使恢复后调度 agent，也要把 `project_root` 注入 prompt。**

初始化时需要的信息（从用户消息中提取或询问）：
- 项目名称
- 项目描述（可选）
- 用户提供的需求输入（URL / 文档路径 / 文本描述）

**路径纪律（全局生效）：**
- orchestrator 读/写 `.ai-dev/` 时用 `<project_root>/.ai-dev/...`
- orchestrator 调度 agent 时在 prompt 中的路径全部拼绝对路径：`<project_root>/artifacts/...`、`<project_root>/workspace/...`
- 不要依赖 agent 或 subagent 的 CWD

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
  1. 读取 <project_root>/.ai-dev/state.json
  2. 找到 current_stage
  3. 根据 status 执行对应动作（调度 Agent / 展示 Gate / 推进）
  4. IF gate_decision = APPROVE:
       → 立即执行记忆沉淀（memory-protocol.md 第 3 节）— 生成候选 → AskUserQuestion → 写入
       → 然后从 state.json.stages[] 读当前 order，找 order+1 的 stage
       → 更新 current_stage = 该 stage.id, status = "pending"
       → 输出一句 "Stage {N} (order {n}) approved → 推进到 Stage {M} (order {n+1})"
       CONTINUE LOOP
  5. IF gate_decision = REVISE:
       → 带上 feedback + OQ/decision 答案重新调度 Agent，attempts+1
       → 状态切回 in_progress
       CONTINUE LOOP
  6. IF gate_decision = REJECT:
       → 按 state-machine.md 回退规则处理
       → 等待用户指示
       CONTINUE LOOP
  7. IF gate_decision = SKIP:
       → 当前 stage status = "skipped"
       → 按 order+1 推进
       CONTINUE LOOP
  8. IF pipeline 所有 stage approved 或 skipped:
       输出完成摘要
       EXIT
```

**推进是 `order + 1`，从 state.json.stages[] 读 order 字段，不能凭感觉跳。**
**记忆沉淀是 APPROVE 后的步骤 4 第一项，不能推到之后。**

## Agent 调度

按 `references/agent-dispatch.md` 中的注册表和模板调度。关键规则：

- 使用 `Agent(subagent_type: "{agent-name}", prompt: "...")` 调度。
- prompt 中传递：输入 artifact 路径 + 用户原始输入 + Human Gate 反馈（如有）+ **历史经验**（见下）。
- **用户提供的 URL、文档路径、需求描述等原样放入 prompt，不做任何预处理。**
- **调度前必须读取并注入历史经验**：按 `references/memory-protocol.md` 第 4 节执行。读取 `.ai-dev/memory/project.md` 和 `~/.claude/memory/agents/{agent-name}.md`，按格式拼到 prompt 的 `## 历史经验（参考，非强制）` 段。
- Agent 返回后：读取产出的 artifact，检查 status，更新 state.json。
- 如有 issues，写入 issue-log。

## Human Gate

### Gate 入口决策树（强约束，违反视为流程错误）

Agent 返回后**禁止直接进 APPROVE/REVISE/REJECT 问题**。必须按以下顺序判断走哪个 Case：

```
Agent 返回 artifact
  │
  ├─ 读取 artifact.status 字段（必须真读，不能假设）
  │
  ├─ status = "draft" AND open_questions[] 非空
  │    → Case 2 OQ 澄清（用 AskUserQuestion 一项一项问，全部收集后才能进 APPROVE）
  │
  ├─ status = "draft" AND open_decisions[] 非空
  │    → Case 2 决策澄清（同上）
  │
  ├─ status = "final"
  │    → Case 1 APPROVE/REVISE/REJECT（也用 AskUserQuestion）
  │
  ├─ Agent 返回 blocking issue
  │    → Case 3 阻塞处置（用 AskUserQuestion）
  │
  └─ Stage 是 optional 且 status = "pending"
       → Case 4 YES/SKIP（用 AskUserQuestion）
```

**红线：**
1. 看到 `status: "draft"` + `open_questions[]` 时**禁止跳过 OQ 直接问 APPROVE/REVISE/REJECT**。"draft" 字面意思就是产物未完成，必须先收集答案重新调度。
2. 所有用户决策（OQ 答案 / APPROVE/REVISE/REJECT / blocking 处置 / optional 选择）**必须用 `AskUserQuestion` 工具**，禁止纯文本列出让用户回答。
3. OQ 收集必须**逐项问完**，禁止只问第一项就跳走。
4. OQ 数量 > 4 → 分批用 AskUserQuestion（每批 ≤ 4 个 question），前一批答完才发下一批。

详细字段映射、推荐项标注、特殊处理见 `references/human-gate-protocol.md`。

### 决策后动作

- 记录决策到 decision-log（必填字段见 `human-gate-protocol.md` 第 4 节）。
- **APPROVE 后必须按 `references/memory-protocol.md` 执行记忆沉淀**：自动生成项目经验和 Agent 通用经验候选，用 AskUserQuestion 让用户审核每一条，保留的条目追加到对应文件。REVISE/REJECT/SKIP 不沉淀。
- REVISE → 把用户反馈 + OQ 答案带进下一次 Agent 调度 prompt。
- REJECT → Case 5 拒绝处置（询问回退到哪个阶段）。

## 编码阶段

按 `references/coding-phase-protocol.md` 执行。

### 编码阶段强制清单（违反任一视为流程错误）

进入编码阶段 (Stage 5) 时，**Orchestrator 必须按以下顺序执行**，禁止跳步：

1. **读 `artifacts/04_plan.json`** 获取 `execution_order` 和 `tasks`。
2. **检测 `workspace/backend/` 是否为空**：
   - 为空（首次编码） → **必须执行 Step 3 收集脚手架 yaml**，禁止直接调度 BackendAgent
   - 非空（增量编码） → 跳过 Step 3
3. **调用 `mcp__scaffold__get_form_schema()`** 拉取 SpringBoot 完整表单 schema，按 schema.type 动态生成 AskUserQuestion 逐项收集用户配置，写入 `.ai-dev/scaffold-defaults.yaml`。**禁止用静态 4 组写死问题，必须按 schema 动态化。** 详见 `references/coding-phase-protocol.md` 3.1-3.4。
4. **创建 `.ai-dev/task-board.json`**。
5. **按 phase 逐批并行调度 BackendAgent + FrontendAgent**，调度 BackendAgent 的 prompt 中必须嵌入 yaml 的 `backend.*` 全部字段。
6. **全部编码完成后调度 TestAgent**。
7. **进入 Human Gate** 确认编码结果（按上述 Gate 入口决策树）。

### 红线

- 看到 `workspace/backend/` 为空就直接调 BackendAgent，**没经 Step 3 收集 yaml**，视为流程错误 — BackendAgent 会因 yaml 缺失上报 issues，导致重跑。
- 用 Bash `curl` 拉脚手架代替 `mcp__scaffold__generate_backend`，视为流程错误 — 那是 BackendAgent 自身的红线，但 Orchestrator 不能放任。
- 跳过 `get_form_schema` 直接用旧版静态配置写死，视为流程错误 — schema 可能已更新。

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

# Agent 调度协议

## 概述

Orchestrator 通过 Claude Code 的 **Agent tool + subagent_type** 调度注册在 `.claude/agents/` 目录下的子 Agent。每个 Agent 在独立上下文中执行，不共享 Orchestrator 的会话状态。

## 架构关系

```
.claude/agents/{name}.md    → Agent 身份定义（角色、能力、约束、工具权限）
.claude/skills/{name}/      → 方法论（怎么做的详细步骤和规则）
```

Agent 被调度后，自动加载其 `.md` 定义文件中的身份和约束，然后通过 prompt 中的指令去读取对应 skill 的方法论执行。

## 调度方式

### 使用 subagent_type 调度

```
Agent(
  subagent_type: "{agent-name}",
  prompt: "{调度指令}"
)
```

`subagent_type` 的值对应 `.claude/agents/{agent-name}.md` 文件中 frontmatter 的 `name` 字段。

### Agent 注册表

| subagent_type | Agent 文件 | 对应 Skill | 输出 Artifact |
|---------------|-----------|------------|--------------|
| `requirement-agent` | `.claude/agents/requirement-agent.md` | requirement-analysis | artifacts/01_requirement.json |
| `design-agent` | `.claude/agents/design-agent.md` | solution-design | artifacts/02_solution.json |
| `prototype-agent` | `.claude/agents/prototype-agent.md` | prototype-design | artifacts/03_prototype.html |
| `planner-agent` | `.claude/agents/planner-agent.md` | task-planning | artifacts/04_plan.json |
| `backend-agent` | `.claude/agents/backend-agent.md` | backend-coding | artifacts/05_backend_report.md |
| `frontend-agent` | `.claude/agents/frontend-agent.md` | frontend-coding | artifacts/06_frontend_report.md |
| `test-agent` | `.claude/agents/test-agent.md` | testing | artifacts/07_test_report.md |
| `review-agent` | `.claude/agents/review-agent.md` | delivery-review | artifacts/08_final_report.md |

## 调度 Prompt 模板

### 单阶段 Agent（Stage 1-4, 6）

```
## 任务
完成 {阶段名称} 阶段工作。

## 输入
- 读取：{input_artifact_paths}
- 项目根目录：{project_root}
{IF revision_feedback:}

## Human Gate 反馈
决策 ID：{decision_id}
类型：REVISE
修改意见：{user_feedback}
{IF questions_answered:}
问题回答：
- {question_id}: {answer}
{ENDIF}
请在已有 artifact 基础上按反馈修改，不要从头开始。
{ENDIF}

## 输出要求
完成后汇报：
1. artifact 路径
2. status（final 或 draft）
3. 如果 draft：open_questions 或 open_decisions 清单
4. 阶段摘要（3-5 句话）
5. 发现的 issues（如有）
```

注意：不需要在 prompt 里声明"你是 XXAgent" — Agent 身份已由 `.claude/agents/` 定义文件提供。

### 编码阶段 Agent

编码阶段 prompt 需额外指定任务范围：

```
## 任务
完成本轮编码任务。

## 输入
- 方案设计：artifacts/02_solution.json
- 任务计划：artifacts/04_plan.json
- 你本次负责的任务：{task_ids}
- 相关接口契约：
  {contract_details}
- 项目根目录：{project_root}

## 输出要求
完成后汇报：
1. 完成的任务 ID 列表
2. 实现/消费的 API 列表
3. issues（如有）
```

## Agent 返回值解析

Orchestrator 从 Agent 返回中提取：

1. 检查 artifact 文件是否已创建。
2. 如果是 JSON artifact，读取其中的 `status` 字段。
3. 如果是 markdown/html artifact，从 Agent 返回文本中提取 status。
4. 提取 open_questions/open_decisions 列表。
5. 提取 issues 列表。

## 并行调度

编码阶段同一 phase 内的 BackendAgent 和 FrontendAgent **并行调度**：

```
在同一个消息中发起两个 Agent tool call：

Agent(subagent_type: "backend-agent", prompt: "...")
Agent(subagent_type: "frontend-agent", prompt: "...")

两个 Agent 独立工作，文件所有权不重叠：
- backend-agent → workspace/backend/
- frontend-agent → workspace/frontend/

等待所有并行 Agent 返回后，汇总结果。
```

## 调度失败处理

如果 Agent 调度失败（Agent tool 报错、超时等）：
1. 不更新 state.json 的 status。
2. 告知用户调度失败。
3. 提供选项：重试 / 手动执行 / 终止。

## 重新调度（REVISE 场景）

- 增加 `attempts` 计数。
- 在 prompt 中附加 Human Gate 反馈块。
- Agent 定义文件中已包含 REVISE 处理规则（读取已有 artifact 修改）。

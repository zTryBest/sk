# Project Run Command

你是 Project Orchestrator。

用户输入项目描述后，按以下流程推进。Command 只负责调度、检查 artifact、执行 Human Gate，不直接替代阶段 Agent 完成专业工作。

## 全局规则

- 每个阶段必须读取上一个阶段 artifact。
- 每个阶段必须写入 `artifacts/`。
- 不允许跳过 Human Gate。
- Human Gate 通过前，不得启动下一阶段。
- 编码阶段不得修改需求、方案、原型和计划 artifact。
- MCP 是工具，不是阶段调度器。
- Skill 是方法论，Agent 是执行角色。

## 阶段流程

### 1. RequirementAgent

调用 `.claude/agents/requirement-agent.md`。

要求：
- 使用 `.claude/skills/requirement-analysis/SKILL.md`。
- 输出 `artifacts/01_requirement.json`。
- 如果 `status=draft` 或存在 `open_questions`，暂停并要求用户确认。

Human Gate 通过后继续。

### 2. DesignAgent

调用 `.claude/agents/design-agent.md`。

要求：
- 使用 `.claude/skills/solution-design/SKILL.md`。
- 必须调用 baseline-api MCP 查询可复用 API、组件和技术基线。
- 输出 `artifacts/02_solution.json`。
- 如果 `status=draft` 或存在 `open_decisions`，暂停并要求用户确认。

Human Gate 通过后继续。

### 3. PrototypeAgent

调用 `.claude/agents/prototype-agent.md`。

要求：
- 使用 `.claude/skills/prototype-design/SKILL.md`。
- 输出 `artifacts/03_prototype.html`。
- 暂停并要求用户确认。

Human Gate 通过后继续。

### 4. PlannerAgent

调用 `.claude/agents/planner-agent.md`。

要求：
- 使用 `.claude/skills/task-planning/SKILL.md`。
- 输出 `artifacts/04_plan.json`。
- 暂停并要求用户确认。

Human Gate 通过后继续。

### 5. BackendAgent 和 FrontendAgent

根据计划顺序并行或顺序调用：
- `.claude/agents/backend-agent.md`
- `.claude/agents/frontend-agent.md`

要求：
- BackendAgent 输出 `artifacts/05_backend_report.md`，代码写入 `workspace/backend/`。
- FrontendAgent 输出 `artifacts/06_frontend_report.md`，代码写入 `workspace/frontend/`。
- 不得修改需求、方案、原型和计划 artifact。

### 6. TestAgent

调用 `.claude/agents/test-agent.md`。

要求：
- 使用 `.claude/skills/testing/SKILL.md`。
- 执行可用测试。
- 输出 `artifacts/07_test_report.md`。

### 7. ReviewAgent

调用 `.claude/agents/review-agent.md`。

要求：
- 使用 `.claude/skills/delivery-review/SKILL.md`。
- 汇总最终交付报告。
- 输出 `artifacts/08_final_report.md`。

## Human Gate 输出格式

每次暂停时，用简洁中文告诉用户：
- 当前阶段。
- 已生成 artifact 路径。
- 需要确认的问题。
- 推荐选项和影响。
- 用户确认后将进入哪个阶段。

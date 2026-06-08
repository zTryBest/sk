---
name: task-planning
description: >
  当 PlannerAgent 需要根据需求、方案和原型拆解开发任务时使用。本 Skill 负责生成
  `artifacts/04_plan.json`，包含后端任务、前端任务、测试任务、接口契约、执行顺序和验收标准。
---

# 任务规划 Skill

## 职责

- 读取 `01_requirement.json`、`02_solution.json` 和 `03_prototype.html`。
- 拆解后端、前端、联调和测试任务。
- 定义接口契约和任务依赖。
- 定义每个任务的验收标准。
- 输出 `artifacts/04_plan.json`。

## 禁止

- 不写代码。
- 不新增需求。
- 不修改方案。
- 不替代 Human Gate 做重大范围变更。

## 输出结构

```json
{
  "schema_version": "1.0",
  "status": "final|draft",
  "backend_tasks": [],
  "frontend_tasks": [],
  "test_tasks": [],
  "api_contracts": [],
  "execution_order": [],
  "acceptance_criteria": [],
  "open_decisions": []
}
```

## 完成标准

- 每个需求都有对应开发或测试任务。
- 后端和前端任务边界清晰。
- 接口契约足以指导编码。
- 任务顺序和依赖清晰。
- 无关键 `open_decisions`。

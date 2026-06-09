---
name: task-planning
description: >
  当 PlannerAgent 需要根据需求、方案和原型拆解开发任务时使用。本 Skill 负责生成 `artifacts/04_plan.json`，
  包含后端任务、前端任务、测试任务、接口契约、执行顺序和验收标准；不负责编码、测试、流程调度或 Human Gate 持久化。
---

# 任务规划 Skill

本 Skill 说明"如何把方案拆成可执行的开发任务"。PlannerAgent 负责调用本 Skill，Orchestrator 在编码阶段消费本阶段产物。

## 阶段边界

应该做：
- 读取 `01_requirement.json`、`02_solution.json` 和 `03_prototype.html`（如存在）。
- 按职责拆出 backend / frontend / test 三类任务。
- 定义前后端的接口契约（API 路径、方法、请求体、响应体、错误码）。
- 编排执行顺序和依赖关系。
- 每个任务关联到来源需求和验收标准。
- 输出 `artifacts/04_plan.json`。

禁止做：
- 不写代码。
- 不修改需求或方案 artifact。
- 不跳过接口契约定义。
- 不调度 Agent。
- 不创建 task-board.json（运行时由 Orchestrator 从 04_plan.json 初始化）。

## 输入

必须读取：

```text
artifacts/01_requirement.json
artifacts/02_solution.json
```

可选读取：

```text
artifacts/03_prototype.html
```

## 拆解流程

### 1. 来源分析

从需求和方案中提取：
- 功能需求清单（F-01, F-02...）
- 模块划分（来自 `02_solution.json.modules`）
- 数据模型（来自 `02_solution.json.data_model`）
- API 设计（来自 `02_solution.json.api_design`）
- 外部集成（来自 `02_solution.json.external_integrations`）
- 前端页面规划（来自 `02_solution.json.frontend_design` 和原型）

### 2. 任务拆解

按 `references/decomposition-rules.md` 的规则拆解：
- backend 任务：服务、模块、API 实现、数据访问、外部集成、定时任务。
- frontend 任务：页面、组件、状态管理、API 集成、表单验证。
- test 任务：单元测试、集成测试、端到端测试。

每个任务必须：
- 关联到至少一个需求 ID。
- 有明确的验收标准（来源于需求验收标准或方案设计）。
- 标注复杂度（low / medium / high）。
- 有 type（backend / frontend / test）。

### 3. 接口契约定义

对每个前后端交互的 API：
- 路径、HTTP 方法。
- 提供方任务（provider_task）和消费方任务（consumer_tasks）。
- 请求 schema（content type、headers、body）。
- 成功响应 schema 和错误响应 schema。
- 错误码列表。

接口契约一旦定义，前后端必须严格遵守。变更需通过 Orchestrator + Human Gate。

### 4. 执行顺序编排

按依赖关系分 phase：
- Phase 1：基础任务（无依赖），如脚手架、数据库 schema、登录认证。
- Phase 2：核心业务任务（依赖 Phase 1），如主功能 API + 对应前端页面。
- Phase 3：扩展任务（依赖 Phase 2），如统计、导出、复杂集成。
- Test phase：所有编码完成后执行。

同 phase 内的任务无依赖，可并行执行。

### 5. Agent Team 配置

输出 agent_team 配置：

```json
{
  "agent_team": {
    "backend": {"agent": "BackendAgent", "skill": "backend-coding"},
    "frontend": {"agent": "FrontendAgent", "skill": "frontend-coding"},
    "test": {"agent": "TestAgent", "skill": "testing"}
  }
}
```

### 6. 输出 artifact

输出 `artifacts/04_plan.json`，详见 `references/output-contracts.md`。

## 完成标准

只有满足以下条件，PlannerAgent 才能把本阶段标为 `final`：
- 所有功能需求都有至少一个对应任务。
- 每个 backend 任务有明确的 API 契约（如涉及前端调用）。
- 每个 frontend 任务的 API 消费都引用了 interface_contracts。
- 执行顺序无循环依赖。
- 每个任务有验收标准。
- 测试任务覆盖所有功能需求。
- `artifacts/04_plan.json` 可被 JSON 解析。

否则必须输出 `draft` 并在 `open_decisions` 中说明。

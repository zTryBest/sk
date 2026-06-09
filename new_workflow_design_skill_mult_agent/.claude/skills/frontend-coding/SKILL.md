---
name: frontend-coding
description: >
  当 FrontendAgent 需要根据 `artifacts/04_plan.json` 和 `artifacts/03_prototype.html` 完成前端编码时使用。
  本 Skill 负责 `workspace/frontend/` 实现和 `artifacts/06_frontend_report.md` 输出；
  不负责需求、方案、后端、测试总控或流程调度。
---

# 前端编码 Skill

本 Skill 说明"前端代码怎么写"。FrontendAgent 负责调用本 Skill，Orchestrator 负责阶段调度和 Human Gate。

## 阶段边界

应该做：
- 读取 `artifacts/04_plan.json` 获取分配给自己的 frontend 任务。
- 读取 `artifacts/02_solution.json` 获取前端架构设计。
- 读取 `artifacts/03_prototype.html`（如存在）作为 UI 参考。
- 按 interface_contracts 精确消费 API。
- 在 `workspace/frontend/` 目录下输出代码。
- 产出 `artifacts/06_frontend_report.md`。
- 发现问题时记录 issues。

禁止做：
- 不修改 `workspace/backend/` 或 `workspace/tests/` 目录。
- 不修改上游 artifact。
- 不自行变更 interface_contracts。
- 不调度其他 Agent。
- 不写流程控制文件。

## 输入

必须读取：

```text
artifacts/04_plan.json
artifacts/02_solution.json
```

可选读取：

```text
artifacts/03_prototype.html
```

## 实现流程

### 1. 任务理解

从 `04_plan.json` 提取分配的 frontend 任务：
- 页面和组件需求。
- interfaces_consumed（要调用的 API）。
- 验收标准。

从 `02_solution.json` 提取：
- frontend_design 中的技术栈选择。
- 页面和组件规划。
- 状态管理方案。

从 `03_prototype.html` 提取：
- 页面布局参考。
- 导航流程。
- 表单字段。

### 2. 脚手架

如果是第一次编码（workspace/frontend/ 为空）：
- 创建项目结构（React/Vue/Angular/...）。
- 配置构建工具。
- 设置路由、状态管理、HTTP 客户端。
- 配置 API base URL 和请求拦截器。

如果非首次调度：
- 读取现有代码结构。
- 在已有代码基础上新增页面/组件。

### 3. 代码实现

按任务逐个实现：
- 页面组件：布局、数据展示、交互。
- 表单组件：字段、校验、提交。
- 状态管理：全局状态、缓存、加载状态。
- API 集成：按 interface_contracts 调用后端 API。
- 路由：页面间导航。
- 响应式：适配不同屏幕尺寸。

代码规范：
- 组件拆分合理，职责清晰。
- 状态管理与 UI 分离。
- 错误处理和加载状态完整。
- 表单校验与 API request_schema 对应。
- 无障碍基础支持（semantic HTML、aria 属性）。

### 4. 接口消费验证

对每个消费的 interface_contract：
- 请求路径和方法正确。
- 请求参数/body 匹配 request_schema。
- 正确处理成功响应（展示/跳转）。
- 正确处理错误响应（提示/重试）。
- 错误码有对应的用户提示。

发现契约问题：
- 不自行修改后端代码或契约。
- 记录到 issues（category: contract_violation）。
- Mock 当前契约的行为，标注 TODO。

### 5. 构建验证

- 执行前端构建命令，确保无编译错误。
- 检查 lint 和 type check（如配置）。
- 记录构建结果。

### 6. 产出报告

输出 `artifacts/06_frontend_report.md`。

## 完成标准

FrontendAgent 完成的条件：
- 所有分配任务的页面/组件已实现。
- 构建通过。
- API 调用匹配 interface_contracts。
- issues 已完整记录。
- `artifacts/06_frontend_report.md` 已产出。

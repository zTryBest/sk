---
name: backend-coding
description: >
  当 BackendAgent 需要根据 `artifacts/04_plan.json` 和 `artifacts/02_solution.json` 完成后端编码时使用。
  本 Skill 负责脚手架搭建、后端代码实现、编译测试和 `artifacts/05_backend_report.md` 输出；
  不负责需求、方案、前端、测试总控或流程调度。
---

# 后端编码 Skill

本 Skill 说明"后端代码怎么写"。BackendAgent 负责调用本 Skill，Orchestrator 负责阶段调度和 Human Gate。

## 阶段边界

应该做：
- 读取 `artifacts/04_plan.json` 获取分配给自己的 backend 任务。
- 读取 `artifacts/02_solution.json` 获取架构设计和数据模型。
- 按 interface_contracts 精确实现 API 端点。
- 在 `workspace/backend/` 目录下输出代码。
- 执行编译/构建验证。
- 编写基础单元测试。
- 产出 `artifacts/05_backend_report.md`。
- 发现问题时记录 issues（不修改上游 artifact）。

禁止做：
- 不修改 `workspace/frontend/` 或 `workspace/tests/` 目录。
- 不修改上游 artifact（01_requirement, 02_solution, 04_plan）。
- 不自行变更 interface_contracts。
- 不调度其他 Agent。
- 不写流程控制文件。

## 输入

必须读取：

```text
artifacts/04_plan.json
artifacts/02_solution.json
```

从 Orchestrator 调度指令中获取：
- 本次负责的任务 ID 列表。
- 对应的 interface_contracts。

## 实现流程

### 1. 任务理解

从 `04_plan.json` 提取分配的 backend 任务：
- 每个任务的 description 和 acceptance_criteria。
- interfaces_provided（自己要实现的 API）。
- interfaces_consumed（需要调用的外部 API）。
- 依赖关系。

从 `02_solution.json` 提取：
- 架构（framework、语言、数据库类型）。
- 数据模型（表结构、字段、关系）。
- API 详细设计。
- 外部集成方案。

### 2. 脚手架

如果是第一次编码（workspace/backend/ 为空）：
- 创建项目结构。
- 配置构建工具（Maven/Gradle/npm/...）。
- 设置数据库连接配置。
- 创建通用基础类（异常处理、响应包装、日志）。

如果非首次调度（已有代码）：
- 读取现有代码结构。
- 在已有代码基础上新增功能。

### 3. 代码实现

按任务逐个实现：
- 数据层：实体类/模型、数据库 migration、Repository/DAO。
- 业务层：Service 实现、业务规则。
- API 层：Controller、路由、参数校验、响应格式。
- 集成层：外部 API 调用、消息队列。

代码规范：
- 方法和变量命名清晰，自文档化。
- 合理分层，职责分离。
- 参数校验在 API 入口层完成。
- 异常处理统一。
- 数据库操作使用事务保证一致性。

### 4. 接口契约验证

对每个 interface_contract：
- 路径和方法完全匹配。
- 请求参数/body 完全匹配 request_schema。
- 成功响应格式匹配 response_schema.success。
- 错误响应格式匹配 response_schema.error。
- 错误码列表完整实现。

发现契约问题：
- 不自行修改契约。
- 记录到 issues（category: contract_violation）。
- 按当前契约尽力实现，标注 TODO。

### 5. 编译验证

- 执行构建命令，确保代码可编译通过。
- 如有单元测试框架，运行测试。
- 记录编译结果和测试结果。

### 6. 产出报告

输出 `artifacts/05_backend_report.md`。

## 完成标准

BackendAgent 完成的条件：
- 所有分配任务的代码已实现。
- 编译通过。
- interface_contracts 中的 API 已按契约实现。
- issues 已完整记录。
- `artifacts/05_backend_report.md` 已产出。

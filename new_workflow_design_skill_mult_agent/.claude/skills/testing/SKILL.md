---
name: testing
description: >
  当 TestAgent 需要基于需求、方案、计划、后端报告和前端报告执行测试时使用。
  本 Skill 负责测试执行、缺陷归类和 `artifacts/07_test_report.md` 输出；
  不负责编码修复、需求变更、方案修改或流程调度。
---

# 测试 Skill

本 Skill 说明"测试怎么做"。TestAgent 负责调用本 Skill，Orchestrator 负责阶段调度和 Human Gate。

## 阶段边界

应该做：
- 读取所有上游 artifact（01-06）了解系统全貌。
- 读取 `artifacts/04_plan.json` 获取分配的 test 任务。
- 编写和执行测试（单元测试、集成测试、E2E 测试）。
- 验证 acceptance_criteria 是否通过。
- 验证 interface_contracts 前后端是否一致。
- 记录缺陷并分类。
- 产出 `artifacts/07_test_report.md`。

禁止做：
- 不修复代码（发现缺陷只记录，不 fix）。
- 不修改上游 artifact。
- 不修改 `workspace/backend/` 或 `workspace/frontend/`（只读取）。
- 不调度其他 Agent。
- 不写流程控制文件。

## 输入

必须读取：

```text
artifacts/01_requirement.json      (验收标准来源)
artifacts/02_solution.json         (架构和接口设计)
artifacts/04_plan.json             (测试任务和 interface_contracts)
artifacts/05_backend_report.md     (后端实现情况)
artifacts/06_frontend_report.md    (前端实现情况)
```

可选读取：

```text
workspace/backend/                 (后端源码)
workspace/frontend/                (前端源码)
```

## 测试流程

### 1. 测试计划

从 `04_plan.json` 提取 test 任务：
- 每个 TEST 任务的 test_type（unit/integration/e2e）。
- covers_tasks 和 covers_requirements。
- acceptance_criteria。

从 `01_requirement.json` 提取：
- 每个功能需求的验收标准（Given/When/Then）。

### 2. 测试用例设计

为每个 test 任务设计用例：

| 用例 ID | 来源需求 | 测试类型 | 场景 | 预期结果 |
|---------|---------|---------|------|---------|
| TC-01 | F-01 | integration | 正常登录 | 返回 token |
| TC-02 | F-01 | integration | 密码错误 | 返回 401 |

用例覆盖策略：
- 正常路径（happy path）。
- 边界条件。
- 异常处理。
- 权限校验。
- 数据校验。

### 3. 测试执行

按测试类型分层执行：

#### 单元测试
- 验证核心业务逻辑函数。
- 在 `workspace/tests/unit/` 下编写。

#### 集成测试
- 验证 API 端点（请求/响应/错误码）。
- 验证数据库 CRUD 操作。
- 在 `workspace/tests/integration/` 下编写。

#### E2E 测试
- 验证完整用户流程。
- 使用 Playwright 或等价工具模拟用户操作。
- 在 `workspace/tests/e2e/` 下编写。

### 4. 接口一致性检查

对每个 interface_contract：
- 检查后端实现是否匹配契约（路径、方法、schema）。
- 检查前端调用是否匹配契约。
- 检查前后端对同一 API 的理解是否一致。

### 5. 缺陷记录

发现的问题按格式记录：

```markdown
### BUG-{NNN}: {标题}

- 严重程度：critical / major / minor / trivial
- 影响需求：F-XX
- 影响任务：BE-XX / FE-XX
- 复现步骤：
  1. ...
  2. ...
- 预期结果：...
- 实际结果：...
- 建议修复：...
```

### 6. 产出报告

输出 `artifacts/07_test_report.md`。

## 完成标准

TestAgent 完成的条件：
- 所有 test 任务对应的用例已设计并执行。
- 测试结果记录完整。
- 缺陷已归类和记录。
- `artifacts/07_test_report.md` 已产出。

注意：测试有缺陷不代表测试阶段失败。TestAgent 的任务是发现和记录问题，不是保证全部通过。

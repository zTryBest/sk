# 编码阶段协作协议

## 概述

编码阶段（Stage 5: coding）与其他阶段不同，它涉及多个 Agent 协作完成实际代码实现。Orchestrator 在此阶段作为 Agent Team 的调度器。

## Agent Team 组成

| Agent | Skill | 职责 | 文件所有权 |
|-------|-------|------|-----------|
| BackendAgent | backend-coding | 后端代码实现 | `workspace/backend/` |
| FrontendAgent | frontend-coding | 前端代码实现 | `workspace/frontend/` |
| TestAgent | testing | 测试编写和执行 | `workspace/tests/` |

## 接口契约（Interface Contract）

接口契约是前后端协作的"法律"，定义在 `artifacts/04_plan.json` 的 `interface_contracts` 中：

```json
{
  "interface_contracts": [
    {
      "id": "API-01",
      "path": "/api/v1/users",
      "method": "POST",
      "provider_task": "BE-01",
      "consumer_tasks": ["FE-01"],
      "request_schema": {
        "content_type": "application/json",
        "body": {}
      },
      "response_schema": {
        "success": {},
        "error": {}
      },
      "error_codes": [],
      "notes": ""
    }
  ]
}
```

规则：
- BackendAgent 必须按契约实现 API（路径、方法、请求/响应格式）。
- FrontendAgent 必须按契约消费 API。
- 任何一方发现契约不合理，通过 issue 上报，不自行修改。
- 只有经过 Human Gate 确认，Orchestrator 才能更新契约。

## 执行流程

### Phase 初始化

1. Orchestrator 读取 `artifacts/04_plan.json`。
2. 提取 `execution_order` 和 `tasks`。
3. 创建 `.ai-dev/task-board.json`：

```json
{
  "schema_version": "1.0",
  "initialized_from": "artifacts/04_plan.json",
  "created_at": "<ISO8601>",
  "current_phase": 1,
  "phases": [
    {
      "phase": 1,
      "status": "pending",
      "backend_tasks": ["BE-01", "BE-02"],
      "frontend_tasks": ["FE-01"],
      "test_tasks": []
    }
  ],
  "task_status": {
    "BE-01": {"status": "pending", "agent_run": 0},
    "BE-02": {"status": "pending", "agent_run": 0},
    "FE-01": {"status": "pending", "agent_run": 0}
  },
  "blocking_issues": []
}
```

### Phase 执行循环

```
FOR each phase in execution_order:
  1. 检查依赖 phase 是否全部完成
  2. 提取本 phase 的 backend_tasks 和 frontend_tasks
  3. 并行调度 BackendAgent 和 FrontendAgent：
     - BackendAgent: 本 phase 的所有 backend tasks
     - FrontendAgent: 本 phase 的所有 frontend tasks
  4. 等待两个 Agent 返回
  5. 更新 task-board.json
  6. 收集 issues
  7. IF blocking_issues 非空:
       进入 Human Gate
       根据决策处理（修复/跳过/回退）
  8. 推进到下一个 phase
```

### 测试阶段

所有编码 phase 完成后：

```
1. 调度 TestAgent（所有 test tasks）
2. TestAgent 执行测试，产出 artifacts/07_test_report.md
3. IF 有失败测试:
     进入 Human Gate
     选项：
       - RETRY: 重新调度相关编码 Agent 修复后再测
       - SKIP: 接受当前测试结果
       - ESCALATE: 手动介入
4. IF 测试通过或用户接受:
     编码阶段完成
```

## 并行调度模板

同一 phase 内并行调度 BackendAgent 和 FrontendAgent：

### BackendAgent 调度 prompt

```
你是 BackendAgent。

## 任务
按照 `.claude/skills/backend-coding/SKILL.md` 的方法论完成后端编码。

## 输入
- 方案设计：artifacts/02_solution.json
- 任务计划：artifacts/04_plan.json
- 你负责的任务：{task_ids}
- 接口契约：{related_contracts}
- 项目根目录：{project_root}

## 输出
- 代码输出到：workspace/backend/
- 完成报告：artifacts/05_backend_report.md
- 汇报：完成的任务、实现的接口、发现的 issues

## 约束
- 只修改 workspace/backend/ 目录。
- 严格按接口契约实现 API。
- 发现契约问题不要自行修改，写入 issues。
- 不修改上游 artifact。
```

### FrontendAgent 调度 prompt

```
你是 FrontendAgent。

## 任务
按照 `.claude/skills/frontend-coding/SKILL.md` 的方法论完成前端编码。

## 输入
- 方案设计：artifacts/02_solution.json
- 原型：artifacts/03_prototype.html（如存在）
- 任务计划：artifacts/04_plan.json
- 你负责的任务：{task_ids}
- 接口契约：{related_contracts}
- 项目根目录：{project_root}

## 输出
- 代码输出到：workspace/frontend/
- 完成报告：artifacts/06_frontend_report.md
- 汇报：完成的任务、消费的接口、发现的 issues

## 约束
- 只修改 workspace/frontend/ 目录。
- 严格按接口契约消费 API。
- 发现契约问题不要自行修改，写入 issues。
- 不修改上游 artifact。
```

## Task Status 更新

Orchestrator 根据 Agent 返回更新 `.ai-dev/task-board.json`：

| Agent 返回 | task status |
|-----------|-------------|
| 任务完成 | `completed` |
| 任务部分完成（有 issue） | `partial` |
| 任务失败 | `failed` |
| 任务被 Agent 标记跳过 | `skipped` |

## 编码阶段完成条件

编码阶段整体完成（可进入 delivery-review）的条件：
1. 所有非 optional task 状态为 `completed`。
2. 测试报告已产出。
3. 无 unresolved blocking issues。
4. Human Gate 确认编码结果。

## 契约变更流程

如果编码过程中发现接口契约需要变更：
1. 发现方 Agent 上报 issue（category: `contract_violation`）。
2. Orchestrator 通过 Human Gate 展示问题。
3. 用户确认变更后，Orchestrator 更新 `artifacts/04_plan.json` 中的 contract。
4. 重新调度受影响的 Agent。

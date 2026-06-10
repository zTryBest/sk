# 编码阶段协作协议

> **STOP — 进入编码阶段时，调度 BackendAgent 之前必须先做完 Phase 初始化的 Step 3。**
>
> 具体：
> 1. 检测 `workspace/backend/` 是否为空
> 2. 为空 → 必须调 `mcp__scaffold__get_form_schema()` → 按 schema.type 动态生成 AskUserQuestion 逐项收集 → 写入 `.ai-dev/scaffold-defaults.yaml`
> 3. 写完 yaml 才能调度 BackendAgent，调度 prompt 必须嵌入 yaml 的 backend.* 全部字段
>
> **禁止 workspace/backend/ 为空时直接调度 BackendAgent**（BackendAgent 会因 yaml 缺失上报 issues 浪费一次调度）。
> **禁止用 Bash curl 拉脚手架代替 mcp__scaffold__generate_backend。**

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
3. **检查并填充脚手架配置**（仅当 `workspace/backend/` 不存在或为空，即首次编码时）：

   **3.1 拉取表单 schema**

   调 `mcp__scaffold__get_form_schema()` 拉取 SpringBoot 的完整表单定义。返回结构：
   ```
   data.baseInfos[]  — 9 项基础字段，每项含 {label, value, defaultValue, type, order}
   data.configInfo[] — 7 类配置，每项含 {label, value, type, options[], order}
                      type 取值: radio (单选) / checkbox (多选) / cascader-multi (二级级联多选)
   ```

   失败（`SCHEMA_FETCH_FAILED`）→ blocking issue，提示用户检查 MCP server 和 SpringBoot 连通性。

   **3.2 读取已存在的 yaml**

   读 `.ai-dev/scaffold-defaults.yaml` 的 `backend.*` 字段。不存在则视作全部缺失。

   **3.3 对每个未在 yaml 中或值为空的字段，用 AskUserQuestion 收集**

   字段名与 schema 的 `value` 一致（camelCase）。按 schema 的 `order` 排序，每批 ≤ 4 项。

   每个字段的 AskUserQuestion 渲染规则（按 schema.type）：

   | schema.type | AskUserQuestion 渲染 |
   |---|---|
   | `input` / `number` / `custominput` | label = schema.label，options 给 2-3 项：`defaultValue (推荐)` + `自定义输入` |
   | `radio` | label = schema.label，options 用 schema.options[].label/value 平铺 |
   | `checkbox` | 拆成多个 `是否启用 {option.label}?` 问题（每项单选 是/否），最终在 yaml 里组装成 list |
   | `cascader-multi` | 先问父级（radio），再问每个父级下的子项（checkbox），yaml 存 `[[parent,child],[parent,child2]]` |

   推荐项策略：
   - baseInfos 字段：`defaultValue` 作为推荐
   - configInfo 字段：根据 02_solution.json 的技术栈推断（如方案选了 Redis → cache 推荐 redisson）；无推断依据用 `defaultValue` 或第一个 option

   **3.4 写回 yaml**

   把答案按以下结构写入 `.ai-dev/scaffold-defaults.yaml`（camelCase，匹配 schema）：
   ```yaml
   backend:
     # baseInfos
     version: "..."
     packageName: "..."
     componentId: "..."
     serviceId: ["..."]
     port: "..."
     errorCode: "..."
     dependenciesVersion: "..."
     email: "..."
     author: "..."
     # configInfo (key 用 schema.value)
     config:
       database: "mysql"                    # radio → string
       cache: "redisson"                    # radio → string
       mq: ["kafka"]                        # checkbox → list[str]
       reference: [["consul","bic"]]        # cascader-multi → list[[parent,child]]
       javaVersion: "11"                    # radio → string
       basicFeatures: ["cloudstore"]        # checkbox → list[str]
       controller: []                       # 用户未选 → 空 list
   ```

   写回后 **调度 BackendAgent 时不再重复问**。
4. 创建 `.ai-dev/task-board.json`：

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
{IF 首次编码（workspace/backend/ 为空）:}

## 脚手架默认配置（由 Orchestrator 注入，直接使用，不要再问）

`.ai-dev/scaffold-defaults.yaml` 已就绪，关键字段（camelCase 与 SpringBoot DTO 一致）：

backend:
  version: "{yaml.backend.version}"
  packageName: "{yaml.backend.packageName}"
  componentId: "{yaml.backend.componentId}"
  serviceId: {yaml.backend.serviceId}
  port: "{yaml.backend.port}"
  errorCode: "{yaml.backend.errorCode}"
  dependenciesVersion: "{yaml.backend.dependenciesVersion}"
  email: "{yaml.backend.email}"
  author: "{yaml.backend.author}"
  config: {yaml.backend.config}    # dict, 含 database/cache/mq/reference/javaVersion/basicFeatures/controller

按 references/scaffold.md 的 3 步流程，用 mcp__scaffold__generate_backend 拉取脚手架。
**禁止 Bash curl，禁止凭空猜参数（含 author/email），禁止用 git config，禁止假调用，禁止 BackendAgent 自己调 get_form_schema。**
{ENDIF}

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

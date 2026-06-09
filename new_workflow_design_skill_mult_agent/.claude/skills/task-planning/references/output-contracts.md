# 输出契约

任务规划阶段只写当前阶段 artifact：

```text
artifacts/04_plan.json
```

## JSON Schema

```json
{
  "schema_version": "1.0",
  "status": "final|draft",
  "project_name": "",
  "agent_team": {
    "backend": {"agent": "BackendAgent", "skill": "backend-coding"},
    "frontend": {"agent": "FrontendAgent", "skill": "frontend-coding"},
    "test": {"agent": "TestAgent", "skill": "testing"}
  },
  "execution_order": [
    {
      "phase": 1,
      "description": "基础脚手架和核心模块",
      "tasks": ["BE-01", "BE-02", "FE-01"],
      "parallel": true,
      "depends_on_phase": null
    },
    {
      "phase": 2,
      "description": "核心业务功能",
      "tasks": ["BE-03", "FE-02", "FE-03"],
      "parallel": true,
      "depends_on_phase": 1
    }
  ],
  "tasks": [
    {
      "id": "BE-01",
      "type": "backend",
      "title": "",
      "from_requirement": ["F-01"],
      "from_solution_module": "",
      "description": "",
      "acceptance_criteria": [],
      "interfaces_provided": [],
      "interfaces_consumed": [],
      "estimated_complexity": "low|medium|high",
      "depends_on": [],
      "status": "pending"
    },
    {
      "id": "FE-01",
      "type": "frontend",
      "title": "",
      "from_requirement": ["F-01"],
      "description": "",
      "acceptance_criteria": [],
      "interfaces_consumed": ["/api/v1/xxx"],
      "depends_on": ["BE-01"],
      "estimated_complexity": "medium",
      "status": "pending"
    },
    {
      "id": "TEST-01",
      "type": "test",
      "title": "",
      "test_type": "unit|integration|e2e",
      "covers_tasks": ["BE-01", "FE-01"],
      "covers_requirements": ["F-01"],
      "depends_on": ["BE-01", "FE-01"],
      "description": "",
      "acceptance_criteria": [],
      "status": "pending"
    }
  ],
  "interface_contracts": [
    {
      "id": "API-01",
      "path": "/api/v1/users",
      "method": "POST",
      "provider_task": "BE-01",
      "consumer_tasks": ["FE-01"],
      "request_schema": {
        "content_type": "application/json",
        "headers": {},
        "body": {
          "type": "object",
          "properties": {},
          "required": []
        }
      },
      "response_schema": {
        "success": {
          "status_code": 200,
          "body": {}
        },
        "error": {
          "status_code": 400,
          "body": {}
        }
      },
      "error_codes": [
        {"code": "AUTH_FAILED", "message": "", "http_status": 401}
      ],
      "notes": ""
    }
  ],
  "open_decisions": [],
  "risks": []
}
```

## 任务 ID 规范

- Backend 任务：`BE-{NN}`（从 01 开始）
- Frontend 任务：`FE-{NN}`（从 01 开始）
- Test 任务：`TEST-{NN}`（从 01 开始）
- Interface Contract：`API-{NN}`（从 01 开始）

## 写入规则

- 使用 Write 工具直接写入 JSON 文件，不要通过 Bash/Python 写入。
- 写完后用 Read 工具重新读取文件，确认 JSON 格式正确。
- 不输出非本阶段约定的文件。
- `status=final` 时 `open_decisions` 必须为空。
- 每个 interface_contract 必须有至少一个 provider_task 和 consumer_task。

## 完成检查

- [ ] 所有功能需求都有对应任务。
- [ ] 每个 backend API 任务有 interface_contract。
- [ ] 每个 frontend API 消费任务引用了对应 contract。
- [ ] execution_order 无循环依赖。
- [ ] 每个任务有 acceptance_criteria。
- [ ] test 任务覆盖所有核心需求。
- [ ] JSON 可正确解析。

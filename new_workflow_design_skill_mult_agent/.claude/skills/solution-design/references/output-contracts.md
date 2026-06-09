# 输出契约

方案设计阶段只写当前阶段 artifact：

```text
artifacts/02_solution.json
```

## JSON Schema

```json
{
  "schema_version": "1.0",
  "status": "final|draft",
  "project_name": "",
  "architecture": {
    "application_shape": "",
    "frontend_shape": "",
    "backend_shape": "",
    "database_type": "",
    "middleware": [],
    "deployment": "",
    "security": [],
    "observability": []
  },
  "implementation_classification": [
    {
      "id": "IC-01",
      "from_requirement": "F-01",
      "sub_capability": "",
      "mode": "BASELINE_API_REUSE|CUSTOM_CODE|EXTERNAL_INTEGRATION|HYBRID|NO_API_NEEDED|UNDECIDED",
      "rationale": "",
      "confirmed": true
    }
  ],
  "mcp_search_plan": [],
  "mcp_call_log": [],
  "selected_baseline_apis": [
    {
      "task_id": "",
      "component_id": "",
      "component_version": "",
      "method": "",
      "api_path": "",
      "request": {},
      "response": {},
      "resolved_doc_version": "",
      "contract_doc_version": "",
      "version_compatibility": "PASS|FAIL",
      "risk": ""
    }
  ],
  "modules": [],
  "data_model": [],
  "api_design": [],
  "external_integrations": [],
  "frontend_design": [],
  "test_points": [],
  "open_decisions": [],
  "risks": []
}
```

## 写入规则

- 使用 `json.dump(..., ensure_ascii=False, indent=2)` 或等价 serializer。
- 写完立即用 `json.load` 重新读取。
- 不要输出非本阶段约定的历史设计文件或流程控制文件。
- `status=final` 时 `open_decisions` 必须为空。
- 使用 baseline API 时，必须写入 MCP 证据（通过 `mcp__knowledge-base__get_api_detail` 获取）和 API 详情契约。

## 校验

```text
python scripts/validate_solution.py --input artifacts/02_solution.json
```

## 完成检查

- [ ] 已读取 `artifacts/01_requirement.json`。
- [ ] 架构、模块、数据库和接口设计已完成。
- [ ] 每个功能项都有实现方式分类。
- [ ] baseline API 复用均有 MCP 证据。
- [ ] 选中 API 有 method、api_path、request、response 和版本兼容证据。
- [ ] 定制实现和外部集成有明确设计。
- [ ] `status=final` 时没有关键 `open_decisions`。

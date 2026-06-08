# 输出契约

需求分析阶段只写当前阶段 artifact：

```text
artifacts/01_requirement.json
```

## JSON Schema

```json
{
  "schema_version": "1.0",
  "status": "final|draft",
  "project_name": "",
  "business_goal": "",
  "source": {
    "source_type": "ticket|manual|document|mixed",
    "source_ref": "",
    "summary": ""
  },
  "product": {
    "product_id": "",
    "product_version": "",
    "aliases": []
  },
  "user_roles": [
    {
      "name": "",
      "description": "",
      "permissions": []
    }
  ],
  "functional_requirements": [
    {
      "id": "F-01",
      "title": "",
      "summary": "",
      "priority": "P0|P1|P2",
      "evidence_level": "明确|澄清|推断|待确认",
      "trigger": "",
      "inputs": [],
      "outputs": [],
      "business_rules": [],
      "data_rules": [],
      "permission_rules": [],
      "state_flow": [],
      "exceptions_or_boundaries": [],
      "acceptance_criteria": []
    }
  ],
  "non_functional_requirements": [],
  "constraints": [],
  "acceptance_criteria": [],
  "platform_dependency_tasks": [
    {
      "task_id": "PDT-01",
      "from_requirement": "F-01",
      "dependency_type": "",
      "target_object_or_data_source": "",
      "solution_search_intent": "",
      "evidence_level": "明确|澄清|推断|待确认",
      "critical": true
    }
  ],
  "target_object_resolution": [],
  "open_questions": [],
  "risks": []
}
```

## 写入规则

- 使用 `json.dump(..., ensure_ascii=False, indent=2)` 或等价 serializer。
- 写完立即用 `json.load` 重新读取。
- 不要输出非本阶段约定的历史 handoff 文件或流程控制文件。
- `status=final` 时 `open_questions` 必须为空。
- `status=draft` 时必须写清楚 `open_questions`。

## 校验

```text
python scripts/validate_requirement.py --input artifacts/01_requirement.json
```

## 完成检查

- [ ] `project_name` 已填写。
- [ ] `business_goal` 已填写。
- [ ] `product.product_id` 已确认。
- [ ] `product.product_version` 已确认。
- [ ] `functional_requirements` 非空。
- [ ] 每个功能项都有验收标准。
- [ ] 每个功能项都有平台依赖或数据来源分析。
- [ ] `status=final` 时没有关键 `open_questions`。

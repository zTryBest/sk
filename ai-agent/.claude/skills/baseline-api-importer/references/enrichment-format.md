# Enrichment JSON 格式

当 Swagger 的接口摘要、标签、描述不足以支撑语义检索时，使用 enrichment JSON 补充业务语义。

```json
{
  "operations": {
    "GET /api/users/{userId}": {
      "api_name": "查询用户详情",
      "capability_tags": ["用户", "用户资料", "组织机构"],
      "scene": "根据用户 ID 查询姓名、状态、部门、身份等展示信息。",
      "description": "用于定制页面、流程参与人、用户展示字段等场景的用户基础资料查询。",
      "params_desc": "userId: 用户主键",
      "request_headers": {
        "Authorization": "Bearer token"
      },
      "request_example": {},
      "response_example": {
        "id": "u001",
        "name": "张三",
        "status": "ACTIVE",
        "departmentName": "销售部"
      },
      "response_demo": "{\"id\":\"u001\",\"name\":\"张三\",\"status\":\"ACTIVE\"}",
      "usage_notes": "当需求需要用户展示字段时优先考虑该接口。状态枚举需要结合目标测试环境确认。"
    }
  }
}
```

`operations` 的 key 使用 `METHOD path`，其中 `METHOD` 大写，`path` 和 Swagger 路径完全一致。

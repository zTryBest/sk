---
name: baseline-api-importer
description: 将组件的 Swagger/OpenAPI JSON 文档导入 ai-agent 项目的方案设计阶段 API 知识库。用于用户提供一个或多个组件接口文档版本的 swagger.json/openapi.json，并需要 Claude Code 解析接口、补充能力标签和业务场景、写入 api_identity/api_contract/api_lifecycle、重建 FAISS 向量索引、验证 MCP 查询结果。
---

# 基线组件接口导入

你在 Claude Code 中使用该 skill 时，目标是把下载好的组件接口文档导入项目知识库，服务于方案设计阶段的 API 检索。优先运行仓库脚本，不要手写 SQL。

## 执行步骤

1. 确认输入：
   - 必填：`component_id`。
   - 必填：一个或多个 `doc_version=swagger_file`，例如 `v1.0=D:\docs\user-v1.0.swagger.json`。
   - 建议：`component_name`、组件描述、业务场景。
   - 可选：`product_id`、`product_version`、实际 `component_version`，用于同步维护平台基线。

2. 检查文档质量：
   - 打开 Swagger/OpenAPI JSON，判断是 Swagger 2.0 还是 OpenAPI 3.x。
   - 查看接口是否有可用的 `summary`、`tags`、`description`。
   - 如果语义不足，先生成 enrichment 模板，再由 AI 补全接口名称、能力标签、场景、示例和使用注意事项。

```powershell
python jobs\import_swagger.py `
  --component-id USER_CENTER `
  --doc-version v1.2 `
  --swagger-file D:\docs\user-center-v1.2.swagger.json `
  --emit-enrichment-template D:\docs\user-center-v1.2.enrichment.json
```

3. 导入单个版本：

```powershell
python jobs\import_swagger.py `
  --component-id USER_CENTER `
  --doc-version v1.2 `
  --swagger-file D:\docs\user-center-v1.2.swagger.json `
  --component-name "用户中心" `
  --component-description "用户、组织、身份相关接口" `
  --component-scene "用于用户详情、部门、状态、身份查询" `
  --rebuild-index
```

4. 导入多个版本：

```powershell
python jobs\import_component_versions.py `
  --component-id USER_CENTER `
  --component-name "用户中心" `
  --component-description "用户、组织、身份相关接口" `
  --component-scene "用于用户详情、部门、状态、身份查询" `
  --version v1.0=D:\docs\user-center-v1.0.swagger.json `
  --version v1.2=D:\docs\user-center-v1.2.swagger.json `
  --rebuild-index
```

5. 如果要维护平台基线，追加：

```powershell
--product-id SIM_PLATFORM_V2 `
--product-version 5.0 `
--product-name "仿真平台 V2" `
--component-version v1.3
```

6. 验证：
   - 运行 `python -m compileall .`。
   - 用 `KnowledgeService().list_component_doc_versions(component_id)` 检查文档版本。
   - 用 `KnowledgeService().resolve_component_doc_version(component_id, component_version)` 检查版本兼容回落。
   - 如已有平台基线，用 `KnowledgeService().find_apis_for_requirement(...)` 验证需求项是否能命中接口。

## 约束

- 同一个组件跨版本保持同一个 `component_id`。
- 接口是否新增、变更、删除由 `api_lifecycle` 表表达。
- 高版本重复低版本接口时，不应强行写重复契约；导入脚本会在契约 hash 一致时记录 `UNCHANGED`。
- 现场单独升级组件时，优先在查询时传 `component_overrides`，不要默认创建现场级基线。
- 批量导入时只在最后重建一次向量索引。

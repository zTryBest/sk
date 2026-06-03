---
name: baseline-api-importer
description: 将组件的 Swagger/OpenAPI JSON 文档导入当前项目的方案设计阶段 API 知识库。当用户已经下载一个或多个组件接口文档版本的 swagger.json/openapi.json，并希望 AI 解析接口、补充能力标签和业务场景、写入 api_identity/api_contract/api_lifecycle、重建 FAISS 向量索引、验证 MCP 查询结果时使用。
---

# 基线组件接口导入

这个 skill 用于把下载好的组件接口文档转成 MCP 可检索的方案设计知识。优先使用仓库里的确定性脚本，不要手写 SQL 入库。

## 工作流

1. 确认组件信息：
   - 必填：`component_id`，以及一个或多个 `doc_version=swagger_file`。
   - 建议填写：`component_name`、组件描述、组件适用场景。
   - 可选：如果本次导入也要维护平台基线，补充 `product_id`、`product_version`、实际 `component_version`。

2. 快速检查 Swagger/OpenAPI 文件：
   - 判断是 Swagger 2.0 还是 OpenAPI 3.x。
   - 检查 `summary`、`tags`、`description` 是否足够支撑语义检索。
   - 如果接口元信息较弱，先生成 enrichment 模板：

```powershell
python jobs\import_swagger.py `
  --component-id USER_CENTER `
  --doc-version v1.2 `
  --swagger-file D:\docs\user-center-v1.2.swagger.json `
  --emit-enrichment-template D:\docs\user-center-v1.2.enrichment.json
```

3. 如需补充接口能力标签、业务场景、请求示例、响应示例，读取 `references/enrichment-format.md`，按其中格式生成 enrichment JSON。

4. 导入单个文档版本：

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

5. 导入同一组件的多个文档版本：

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

6. 如果要同时绑定平台基线，在导入命令中追加：

```powershell
--product-id SIM_PLATFORM_V2 `
--product-version 5.0 `
--product-name "仿真平台 V2" `
--component-version v1.3
```

7. 导入后验证：
   - 执行 `python -m compileall .`。
   - 调用 `KnowledgeService().list_component_doc_versions(component_id)`。
   - 调用 `KnowledgeService().resolve_component_doc_version(component_id, component_version)`。
   - 如果已有平台基线，调用 `KnowledgeService().find_apis_for_requirement(product_id, product_version, requirement_item, component_overrides=...)` 验证需求项能否找到 API。

## 规则

- 同一个组件跨版本必须保持同一个 `component_id`。版本差异写入 `api_contract` 和 `api_lifecycle`，不要拆成多个组件。
- `doc_version` 表示接口文档版本，例如 `v1.0`、`v1.2`、`v2.1`。
- 平台基线只记录平台版本默认包含的组件版本。现场单独升级组件时，优先在 MCP 查询时通过 `component_overrides` 传入，不要默认给每个现场建基线。
- 实验阶段默认全部审核入库。用户后续觉得查询为空或查询错误时，把人工确认结果转成 enrichment 或版本映射，再重新导入。
- 批量导入多个版本时，最后统一重建向量索引，不要每导入一个版本就重建一次。

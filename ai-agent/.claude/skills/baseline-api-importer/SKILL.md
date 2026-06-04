---
name: baseline-api-importer
description: 当用户要把一个或多个组件段的 Swagger/OpenAPI JSON 导入 ai-agent 项目的方案设计 API 知识库时必须使用本 skill。适用于 Claude Code 中执行清理旧数据、生成 enrichment 模板、让 AI 补充中文业务语义、批量导入多个接口文档版本、重建 FAISS 向量索引、验证 MCP 查询效果的完整流程。
---

# 基线组件 API 知识导入

本 skill 用于把组件接口文档导入 ai-agent 的 design-phase 知识库，供 MCP 在方案设计阶段根据需求项检索接口。

原则：优先运行项目内脚本，不要手写 SQL 入库。

## 数据分层

必须把两类数据分开处理：

1. 组件 API 知识：某个组件/组件段的多个 Swagger/OpenAPI 文档版本，例如 `XRES` 的 `1.7.0`、`2.4.0`。这一步只导入接口身份、接口契约、接口生命周期和向量索引，不绑定具体平台。
2. 平台基线：某个平台版本包含哪些组件，以及每个组件的实际版本，例如 `PPP 2.5.0` 的基线组件 `XRES=2.4.0`。这一步写入 `product_release` 和 `product_component_baseline`。

推荐流程：

- 先批量导入组件 API 多版本知识。
- 再批量录入平台版本的基线组件清单。
- MCP 查询时根据 `product_id + product_version` 找到组件版本，再解析到最接近的接口文档版本和契约。

## 必须先确认的信息

开始前必须确认：

- `product_id`：平台 ID，例如 `PLATFORM_X`
- `product_version`：平台版本，例如 `5.0`
- `component_id`：组件 ID，例如 `AAA`
- `segment_id`：组件段 ID，例如 `AAA_SEARCH`
- Swagger/OpenAPI JSON 文件目录
- 是否需要清理旧数据

建议确认：

- `product_name`
- `component_name`
- `segment_name`
- 组件/组件段的业务描述

约定：

- `product_id`、`component_id`、`segment_id` 可由用户小写输入，但脚本会规范化为大写。
- 同一组件跨版本必须保持同一个 `component_id`。
- 同一组件下不同服务段用 `segment_id` 区分，服务段不是独立组件。
- `doc_version` 表示接口文档版本，例如 `v1.0`、`v1.1`、`v2.1`。
- `component_version` 只在绑定平台基线时需要，表示某个平台版本实际使用的组件版本。批量导入多个 Swagger 文档版本时不要强制要求它。

## 推荐文件目录

建议让用户按下面结构放文件：

```text
E:\AI\kb-import\
  PLATFORM_X\5.0\
    AAA\
      AAA_SEARCH\
        swagger\
          v1.0.swagger.json
          v1.1.swagger.json
          v1.2.swagger.json
        enrichment\
          v1.0.enrichment.json
          v1.1.enrichment.json
          v1.2.enrichment.json
```

`swagger` 目录放原始接口文档。  
`enrichment` 目录放 AI/人工补充后的增强文件。

## enrichment 文件是什么

Swagger 经常缺少中文业务描述，尤其是请求字段、响应字段和示例值。`enrichment-file` 用来补充这些语义。

重点补充字段：

- `api_name`：更清晰的中文接口名
- `description`：接口业务说明
- `business_terms`：业务词，例如“资源检索”“权限查询”
- `search_keywords`：检索关键词，例如字段名、业务别名、英文缩写
- `request_field_notes`：请求字段中文含义
- `response_field_notes`：响应字段中文含义
- `request_value_notes`：请求值说明
- `response_value_notes`：响应值说明
- `usage_notes`：使用建议

这些内容会进入 `api_contract.usage_notes` 和 `api_identity.content`，并参与向量索引和关键词召回。

## 清理旧数据

如果用户要重新导入，先 dry-run：

```powershell
python jobs\cleanup_dirty_knowledge.py --all-design --delete-current-vector-files
```

确认数量无误后执行：

```powershell
python jobs\cleanup_dirty_knowledge.py --all-design --delete-current-vector-files --confirm
```

只清理某个组件段：

```powershell
python jobs\cleanup_dirty_knowledge.py `
  --component-id AAA `
  --segment-id AAA_SEARCH `
  --include-baseline `
  --include-component-metadata `
  --delete-current-vector-files `
  --confirm
```

## 生成 enrichment 模板

如果 enrichment 目录为空，Claude Code 必须自动生成 enrichment 文件并保存到 enrichment 目录，不能要求用户人工创建。

优先批量生成：

```powershell
python jobs\prepare_enrichment_files.py `
  --swagger-dir E:\AI\kb-import\PLATFORM_X\5.0\AAA\AAA_SEARCH\swagger `
  --enrichment-dir E:\AI\kb-import\PLATFORM_X\5.0\AAA\AAA_SEARCH\enrichment
```

也可以对单个 Swagger 版本生成 enrichment 模板：

```powershell
python jobs\import_swagger.py `
  --component-id AAA `
  --segment-id AAA_SEARCH `
  --doc-version v1.0 `
  --swagger-file E:\AI\kb-import\PLATFORM_X\5.0\AAA\AAA_SEARCH\swagger\v1.0.swagger.json `
  --emit-enrichment-template E:\AI\kb-import\PLATFORM_X\5.0\AAA\AAA_SEARCH\enrichment\v1.0.enrichment.json
```

生成的 enrichment 文件必须保留在 enrichment 目录，作为 AI 生成知识的审计记录。

## AI 补充 enrichment

读取生成的 enrichment 模板，让 AI 基于 Swagger 原文补充中文语义。

补充要求：

- 不要改变 operation key，例如 `GET /xxx/yyy`。
- 不要编造不存在的接口路径和字段。
- 字段名必须保留原始英文名，同时补中文含义。
- 优先分析 `request_schema`、`response_schema`、`request_field_candidates`、`response_field_candidates`。
- 用请求参数和响应参数反推 `api_name`、`description`、`scene`、`business_terms` 和 `search_keywords`。
- 对没有中文描述的返回字段，优先根据字段名、接口名、上下文推断，并在 `usage_notes` 标注“根据字段名推断”。
- 如果请求参数或响应参数不明确，降低 `contract_confidence`，并在 `confidence_reason` 中说明原因。
- `business_terms` 和 `search_keywords` 应覆盖需求分析里用户可能说出的业务词。
- 补充完成后必须写回 enrichment 文件，导入时优先通过 `--enrichment-dir` 自动匹配这些文件。

示例：

```json
{
  "operations": {
    "GET /xres-search/service/rs/resource/query": {
      "api_name": "查询资源列表",
      "description": "根据资源名称、资源类型查询资源列表。",
      "business_terms": ["资源查询", "资源检索", "资源列表"],
      "search_keywords": ["资源", "目录", "resource", "resId"],
      "request_field_notes": {
        "resName": "资源名称",
        "resType": "资源类型"
      },
      "response_field_notes": {
        "resId": "资源ID",
        "resName": "资源名称",
        "permissionName": "权限名称"
      },
      "request_value_notes": {},
      "response_value_notes": {},
      "usage_notes": "方案设计阶段需要查询资源并返回权限信息时可优先考虑。"
    }
  }
}
```

## 批量导入多个版本

同一个组件段的多个接口文档版本用 `jobs\import_component_versions.py` 一次导入。脚本会按版本排序导入，最后只重建一次向量索引。

如果当前只是导入组件多版本接口知识，还不能确定某个平台版本使用哪个组件版本，不要传 `--component-version`，也不要传平台绑定参数。使用 `--allow-unbound` 表示这次只建立组件知识，后续再绑定平台基线。

```powershell
python jobs\import_component_versions.py `
  --component-id AAA `
  --segment-id AAA_SEARCH `
  --segment-name "AAA检索服务" `
  --component-name "AAA组件" `
  --version v1.0=E:\AI\kb-import\PLATFORM_X\5.0\AAA\AAA_SEARCH\swagger\v1.0.swagger.json `
  --version v1.1=E:\AI\kb-import\PLATFORM_X\5.0\AAA\AAA_SEARCH\swagger\v1.1.swagger.json `
  --version v1.2=E:\AI\kb-import\PLATFORM_X\5.0\AAA\AAA_SEARCH\swagger\v1.2.swagger.json `
  --enrichment-dir E:\AI\kb-import\PLATFORM_X\5.0\AAA\AAA_SEARCH\enrichment `
  --allow-unbound `
  --rebuild-index
```

如果多个版本共用一个 enrichment 文件，可使用：

```powershell
--enrichment-file E:\AI\kb-import\common.enrichment.json
```

优先使用 `--enrichment-dir`。如果 enrichment 文件名不是 `doc_version.enrichment.json`，再使用 `--enrichment-version` 单独指定。

## 可选：绑定平台基线

只有当用户明确知道某个平台版本实际使用哪些组件版本时，才绑定平台基线。MCP 的 `find_apis_for_requirement` 依赖平台基线来确定组件范围。

优先使用批量脚本 `jobs\import_product_baseline.py`。

baseline JSON 示例：

```json
{
  "product_id": "PPP",
  "product_version": "2.5.0",
  "product_name": "PPP平台",
  "components": [
    {
      "component_id": "XRES",
      "component_version": "2.4.0",
      "component_name": "资源服务"
    },
    {
      "component_id": "USER_CENTER",
      "component_version": "1.7.0",
      "component_name": "用户中心"
    }
  ]
}
```

先 dry-run：

```powershell
python jobs\import_product_baseline.py `
  --baseline-file E:\AI\kb-import\PPP\2.5.0\baseline.json `
  --dry-run
```

确认后入库：

```powershell
python jobs\import_product_baseline.py `
  --baseline-file E:\AI\kb-import\PPP\2.5.0\baseline.json
```

也可以不用文件，直接传组件：

```powershell
python jobs\import_product_baseline.py `
  --product-id PLATFORM_X `
  --product-version 5.0 `
  --product-name "某某平台" `
  --component XRES=2.4.0 `
  --component USER_CENTER=1.7.0
```

如果平台版本下组件版本未知，不要猜测 `component_version`。

## 去重和版本规则

- `api_identity` 不按版本重复入库。同一 `component_id + segment_id + method + api_path` 只有一条接口身份。
- `api_contract` 按 `doc_version` 存契约。
- 如果高版本接口契约与低版本完全一致，脚本会记录 `UNCHANGED`，避免重复保存相同契约。
- `api_lifecycle` 记录 `ADDED`、`CHANGED`、`UNCHANGED`、`REMOVED`。
- 建议按版本从低到高导入。批量脚本会自动排序。

## 验证

导入后先检查脚本是否能编译：

```powershell
python -m py_compile jobs\import_component_versions.py jobs\import_swagger.py jobs\debug_api_search.py jobs\prepare_enrichment_files.py jobs\export_validation_enrichment.py
```

再跑检索诊断：

```powershell
python jobs\debug_api_search.py `
  --product-id PLATFORM_X `
  --product-version 5.0 `
  --requirement "查询资源列表并返回权限名称" `
  --vector-top-k 20 `
  --json
```

查看：

- `raw_vector_top`：原始向量候选是否随需求变化
- `filtered_vector_top`：组件基线过滤后是否合理
- `final_matches`：最终接口是否命中预期

如果不同需求仍然返回固定接口，提醒用户先运行：

```powershell
python jobs\rebuild_vector_indexes.py
```

如果已经配置真实测试环境并运行接口验证任务，验证结果要反哺 enrichment：

```powershell
python jobs\export_validation_enrichment.py `
  --component-id AAA `
  --segment-id AAA_SEARCH `
  --output-file E:\AI\kb-import\AAA\AAA_SEARCH\enrichment\validation.suggestions.json
```

生成的 `validation.suggestions.json` 只作为建议文件。Claude Code 需要读取它，与正式 `*.enrichment.json` 对比后再合并，不能无审计地覆盖正式 enrichment。

## Claude Code 执行原则

- 先确认导入模式：组件多版本知识导入，还是平台基线绑定导入。
- 组件多版本知识导入不要强制要求 `component_version`。
- 用户要求清理时，先 dry-run，再执行 `--confirm`。
- 生成 enrichment 模板后，必须补充中文业务语义再导入。
- 批量导入时，最后统一 `--rebuild-index`，不要每个版本单独重建。
- 允许先用 `--allow-unbound` 导入组件多版本接口知识；但在使用 MCP 按平台需求查询前，必须通过 `import_product_baseline.py` 或等价流程绑定平台基线。

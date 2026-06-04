---
name: design-phase
description: 在需求分析已确认平台名称和平台版本后，进入方案设计阶段。使用当前 ai-agent MCP 工具校验平台基线组件、检索组件段和 API 契约，为每个需求分解项产出有证据链的组件/API 选择、前后端方案、数据库和接口设计。用户说“方案设计”“设计阶段”“根据需求分解做设计”时使用。
---

# 方案设计

本 skill 用于让 AI 在方案设计阶段高准确率使用 MCP。核心原则：先确认平台基线，再逐需求检索 API，最后二次确认 API 详情；没有证据就不要猜。

## 当前 MCP 工具

- `health_check()`：检查 MCP 是否可用。
- `list_products()`：列出已入库的平台/产品版本。
- `list_product_components(product_id, product_version, component_overrides)`：列出平台版本的基线组件。
- `list_component_segments(component_id)`：列出组件段，如 `AAA-WEB`、`AAA-SEARCH`。
- `list_component_doc_versions(component_id, segment_id?)`：查看文档版本。
- `resolve_component_doc_version(component_id, segment_id, component_version)`：解析组件版本到文档版本。
- `find_apis_for_requirement(product_id, product_version, requirement_item, component_overrides, limit)`：按需求项检索候选 API。
- `get_api_detail(component_id, segment_id, component_version, method, api_path)`：确认 API 契约。
- `submit_component_version_doc_mapping(...)`：仅在用户人工确认版本映射后调用。

不要调用旧版搜索类或候选提交类 MCP 工具；只按上面的当前工具清单执行。

## 高准确率流程

1. 需求分析结果必须包含 `product_id` 和 `product_version`。缺失就先问用户。
2. 调用 `health_check()`。
3. 调用 `list_products()`，确认平台版本已入库；没有则停止，提示先导入平台基线。
4. 调用 `list_product_components(...)`，展示组件范围；现场组件升级必须写入 `component_overrides` 后重查。
5. 逐个需求项确认是否需要调用基线组件；不需要的需求项不调用 MCP。
6. 对每个需要基线调用的需求项，单独调用 `find_apis_for_requirement(..., limit=8)`。
7. 过滤候选：必须有 `api_identity`、`api_contract`，组件在基线范围内，`lifecycle_status` 不能是 `REMOVED`。
8. 对 Top 3 候选逐个调用 `get_api_detail(...)` 二次确认。
9. 向用户展示候选 API 和风险，让用户选择 API、改为定制实现、指定其他 API 或要求补知识库。
10. 在设计文档中保存 MCP 证据链。

## 置信度规则

- 高：`match_level=EXACT` 或 `MANUAL`，契约存在，risk 为空或很低。
- 中：同 major 最近文档版本回退，契约存在，字段基本覆盖。
- 低：只有关键词匹配、契约回退明显、字段覆盖不完整。
- 不可用：无契约、接口删除、组件不在平台基线范围内。

低置信度或不可用时不能直接采用，必须问用户。

## MCP 证据表

每个最终 API 都输出：

| 需求项 | 组件 | 段 | 组件版本 | API | 文档版本 | match_level | risk | 请求/响应覆盖 |
|---|---|---|---|---|---|---|---|---|

API 路径保持 MCP 返回的完整 `api_path`，不要裁剪 Swagger `basePath`。

## 不确定时

按顺序排查：

1. 平台版本是否入库。
2. 组件范围是否正确。
3. 是否存在 `component_overrides`。
4. 组件段是否缺失，调用 `list_component_segments`。
5. 文档版本是否缺失，调用 `list_component_doc_versions`。
6. 用户确认版本映射后再调用 `submit_component_version_doc_mapping`。
7. 知识库缺 API 时，提示使用 `baseline-api-importer` skill 导入 Swagger。

## 设计输出要求

- 前端页面只调用本项目 Gateway API，不直连基线组件。
- 后端 Gateway API 说明如何映射到已确认的基线 API。
- 每个跨组件调用必须包含 fallback、错误处理、请求映射、响应映射和 MCP 证据编号。
- 写 DDL 前先问数据库类型。
- 完成前确认没有使用旧版搜索类或候选提交类 MCP 工具，也没有编造组件/API。

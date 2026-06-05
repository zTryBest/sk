---
name: design-phase
description: 在需求分析已确认平台名称和平台版本后，进入方案设计阶段。使用当前 ai-agent MCP 工具校验平台基线组件、检索组件段和 API 契约，为每个需求分解项产出有证据链的组件/API 选择、前后端方案、数据库和接口设计。用户说“方案设计”“设计阶段”“根据需求分解做设计”时使用。
---

# 方案设计

本 skill 的目标是把需求分析结果转成可执行详细设计，并在涉及基线组件/API 时通过 MCP 获取证据。禁止凭模型记忆编造组件、接口、版本或路径。

## 当前 MCP 工具

只使用当前项目真实存在的工具：

- `health_check()`：检查 MCP 是否可用。
- `list_products()`：列出已入库的平台/产品版本。
- `list_product_components(product_id, product_version, component_overrides)`：列出平台版本的基线组件，支持现场组件版本覆盖。
- `list_component_segments(component_id)`：列出组件段，如 `AAA-WEB`、`AAA-SEARCH`。
- `list_component_doc_versions(component_id, segment_id?)`：查看组件或组件段已导入的文档版本。
- `resolve_component_doc_version(component_id, segment_id, component_version)`：解析实际组件版本对应的接口文档版本。
- `find_apis_for_requirement(product_id, product_version, requirement_item, component_overrides, limit)`：按需求项检索候选 API。
- `get_api_detail(component_id, segment_id, component_version, method, api_path)`：二次确认 API 详情和契约。
- `submit_component_version_doc_mapping(...)`：仅在用户人工确认版本映射后调用。

不要调用旧版搜索类或候选提交类 MCP 工具；只按上面的当前工具清单执行。

## 高准确率原则

- 需求分析阶段必须已经明确 `product_id` 和 `product_version`。缺失时先用 `AskQuestion` 问用户，不调用 MCP。
- `product_id`、`component_id`、`segment_id` 按不区分大小写处理，展示时统一大写。
- API 路径保持 MCP 返回值，Swagger `basePath` 已经在入库阶段拼入 `api_path`，不要自行裁剪。
- 每个需求分解项单独检索，不要把多个需求合成一个 MCP 查询。
- 判断是否调用基线组件时，必须做平台依赖分析：识别该需求是否需要读取、写入、订阅、校验、展示、关联或补全平台既有对象、事件、规则、状态、权限和配置。
- “定制实现”只表示代码归属，不等于“不调用基线组件”。只要定制功能依赖平台既有能力或既有数据，就必须标记为“需要调用基线组件”或“待用户确认”，并说明依赖来源。
- 每个最终选中的 API 必须经过 `get_api_detail` 二次确认。
- 输出方案时必须带 MCP 证据：组件版本、组件段、文档版本、`match_level`、`risk`、请求/响应契约。
- 若 MCP 为空、契约为空、风险不可接受或版本跨 major 不确定，停止并用 `AskQuestion` 问用户；不要猜。

## 用户交互规则

design-phase 涉及用户交互时必须使用 `AskQuestion`，不能用普通助手消息直接提问或让用户选择。

适用范围包括但不限于：

- 缺少 `product_id`、`product_version`、数据库类型、运行环境等必要信息。
- 每个阶段结束后的确认。
- 需求项是否调用基线组件的逐项确认。
- 现场组件版本覆盖、组件版本到文档版本映射确认。
- 候选 API 选择、改为定制实现、用户指定其他 API、要求补知识库。
- MCP 为空、契约为空、低置信度、风险不可接受、版本跨 major 不确定等需要用户决策的场景。

`AskQuestion` 内容必须包含：

- 当前阶段和阻塞原因。
- 已知事实和 MCP 证据摘要。
- 需要用户回答的明确问题。
- 可选项；当需要选择时，每个选项必须有稳定编号或 key。
- 推荐项和推荐理由；没有足够证据时明确写“无推荐项”。

`AskQuestion` 发出后立即停止当前阶段，等待用户回复。收到回复后，把用户选择写入设计上下文，再继续下一阶段。

## 执行节奏

一次只执行一个阶段。每个阶段结束后必须用 `AskQuestion` 向用户确认，等待用户回复后再进入下一阶段。

1. Phase 1：加载需求分析结果
2. Phase 2：架构选型和中间件确认
3. Phase 2.5：确认哪些需求项需要调用基线组件
4. Phase 3：MCP 基线范围校验和候选 API 检索
5. Phase 4：API 详情确认和用户选择
6. Phase 5：前端页面设计
7. Phase 6：后端 Gateway REST + 基线组件调用设计
8. Phase 7：数据库设计
9. Phase 8：内部协议设计
10. Phase 9：输出详细设计文档

## Phase 1：加载需求分析结果

提取并记录：

- `product_id`
- `product_version`
- 是否存在现场组件版本覆盖，形成 `component_overrides`，例如 `{ "AAA": "v1.3" }`
- 需求分解项列表，编号为 `R-01`、`R-02`
- 用户角色、页面、数据对象、外部调用线索
- 每个需求项的输入来源、输出去向、关键数据对象、状态流转和平台依赖
- 每个需求项是否依赖平台既有对象、事件、规则、权限、配置、主数据或展示字段
- 每个需求项中需要用户确认的数据来源、对象归属和系统边界

如果 `product_id` 或 `product_version` 缺失，使用 `AskQuestion` 询问用户并停止。

## Phase 2：架构选型

默认定制代码使用 SpringBoot 单体，除非用户明确要求拆分微服务。调用平台基线组件时，优先通过注册中心和平台规范调用，不设计前端直连基线组件。

使用 `AskQuestion` 向用户确认架构、中间件类别和关键运行环境，确认后停止。

## Phase 2.5：基线调用预检

先对每个需求分解项做“显式功能 + 平台依赖”分析，再使用 `AskQuestion` 逐个需求分解项询问是否需要调用平台基线组件。不要替用户批量决定。

平台依赖按以下类型检查，不要把它们写死到某个业务域：

- 触发依赖：需求是否由平台既有事件、流程、任务、状态变化或业务动作触发。
- 主数据依赖：需求是否需要平台既有人员、组织、角色、权限、资源、设备、客户、项目、区域、业务对象等数据。
- 详情补全依赖：需求是否需要根据平台对象 ID 补全名称、属性、归属、状态、标签、上下文等展示字段。
- 规则策略依赖：需求是否需要读取或关联平台既有规则、策略、配置、阈值、权限范围或租户上下文。
- 状态写回依赖：需求是否需要把处理结果、回执、审批结果、执行状态等写回平台既有模块。
- 查询统计依赖：需求的历史查询、统计口径、筛选条件是否依赖平台既有字段或维表。
- 外部系统边界：需求是否只是调用外部系统；若外部调用的入参来自平台对象，也仍然存在平台依赖。

只要任一平台依赖成立，即使页面、表或服务本身是定制实现，也不能直接标记为“不调用基线组件”；应标记为“需要”或“待确认”，并进入 MCP 检索或用 `AskQuestion` 让用户确认。

只有同时满足以下条件，才可以标记为“不调用基线组件”：

- 输入完全来自用户手工录入、外部系统回调或定制库自身数据。
- 输出不需要补全、校验、关联或写回平台既有对象。
- 查询和统计不依赖平台既有维度、权限范围或状态字段。
- 不需要订阅平台事件或调用平台既有规则/配置/权限能力。

输出表格：

| 需求项 | 显式功能 | 平台依赖类型 | 依赖对象/数据来源 | 是否调用基线组件 | MCP 检索意图 | 备注 |
|---|---|---|---|---|---|---|

只有标记为“需要调用基线组件”的需求项进入 MCP 阶段。

## Phase 3：MCP 基线范围和候选 API

### 3.1 健康检查

先调用 `health_check()`。失败则停止，并用 `AskQuestion` 提示用户启动 MCP 服务或确认 MCP 连接方式。

### 3.2 校验平台版本

调用 `list_products()`，确认目标 `product_id/product_version` 已入库。

如果未入库：

- 不继续检索 API。
- 使用 `AskQuestion` 告诉用户需要先导入平台基线或通过后续 Playwright 抓取平台基线组件，并询问下一步处理方式。
- 停止等待用户处理。

### 3.3 确认组件范围

调用：

```text
list_product_components({
  "product_id": "<PRODUCT_ID>",
  "product_version": "<PRODUCT_VERSION>",
  "component_overrides": { ... }
})
```

用 `AskQuestion` 向用户展示组件范围并确认是否继续：

| 组件 | 组件版本 | 来源 | 已知组件段 |
|---|---|---|---|

若用户提到现场单独升级某组件，必须放入 `component_overrides` 后重新调用。

如需确认现场组件版本覆盖，必须使用 `AskQuestion`。

### 3.4 逐需求检索候选 API

对每个需要基线调用的需求项，调用：

```text
find_apis_for_requirement({
  "product_id": "<PRODUCT_ID>",
  "product_version": "<PRODUCT_VERSION>",
  "requirement_item": "<只写当前需求项的动作、平台依赖类型、依赖对象/数据来源、查询条件、期望返回>",
  "component_overrides": { ... },
  "limit": 8
})
```

检索词要具体，包含业务对象、动作、平台依赖类型、依赖对象、输入、输出。不要只写“新增/修改/删除/查询配置”这类表面 CRUD；要写清楚它依赖哪个平台对象、事件、规则、状态或权限上下文。

### 3.5 候选过滤

候选 API 必须通过以下检查才可推荐：

- `api_identity` 存在。
- `api_contract` 存在。
- `lifecycle_status` 不是 `REMOVED`。
- 组件在 `list_product_components` 返回范围内。
- `risk` 可解释；若 risk 表示无精确文档、契约回退，必须降级置信度并展示。
- 需求字段能被请求参数或响应字段覆盖。

置信度规则：

- 高：`match_level=EXACT` 或 `MANUAL`，契约存在，risk 为空或很低。
- 中：同 major 最近文档版本回退，契约存在，字段基本覆盖。
- 低：只有关键词匹配、契约回退明显、字段覆盖不完整。
- 不可用：无契约、接口删除、组件不在平台基线范围内。

## Phase 4：API 详情确认

对每个候选 Top 3 调用 `get_api_detail` 二次确认：

```text
get_api_detail({
  "component_id": "<COMPONENT_ID>",
  "segment_id": "<SEGMENT_ID>",
  "component_version": "<COMPONENT_VERSION>",
  "method": "<GET|POST|...>",
  "api_path": "<完整 api_path>"
})
```

通过 `AskQuestion` 输出用户可选择的表格：

| 排名 | 组件/段 | API | 文档版本 | 请求字段 | 响应字段 | 风险 | 推荐级别 |
|---|---|---|---|---|---|---|---|

每个需求项都要使用 `AskQuestion` 让用户确认：

- 选择某个 API
- 改为定制实现
- 以上都不合适，用户指定组件/API
- 需要先补知识库

用户确认后，将选中 API 写入设计上下文。

## MCP 为空或不确定时

不要编造。按顺序处理：

1. 检查平台基线是否存在。
2. 检查组件是否被现场覆盖。
3. 调用 `list_component_segments` 和 `list_component_doc_versions` 看是否缺组件段或文档版本。
4. 若用户通过 `AskQuestion` 确认某组件版本应使用某文档版本，调用 `submit_component_version_doc_mapping`。
5. 若知识库缺 API，使用 `AskQuestion` 提示用户使用 `baseline-api-importer` skill 导入 Swagger，并询问是否先补知识库。

以上任何需要用户判断或确认的步骤都必须使用 `AskQuestion`。

## Phase 5：前端页面设计

页面只调用本项目 Gateway API，不直连基线组件 API。

每个页面输出：

- Route
- 初始状态
- 查询/提交/错误交互流程
- 依赖的 Gateway API
- 间接依赖的基线 API 证据编号

使用 `AskQuestion` 确认后停止。

## Phase 6：后端 API 设计

设计本项目 Gateway REST API，并说明每个接口如何调用已确认的基线 API。

每个跨组件调用必须包含：

- 调用场景
- 组件和组件段
- 实际组件版本
- HTTP method + api_path
- 请求映射
- 响应映射
- fallback 和错误处理
- MCP 证据编号

使用 `AskQuestion` 确认后停止。

## Phase 7：数据库设计

写 DDL 前先用 `AskQuestion` 询问数据库类型。每张表标注 `NEW` 或 `EXTEND`。使用 `AskQuestion` 确认后停止。

## Phase 8：内部协议设计

设计 MQ、Feign、异步任务、幂等、补偿和 fallback。使用 `AskQuestion` 确认后停止。

## Phase 9：设计文档

文档必须包含 MCP 证据表：

| 证据编号 | 需求项 | 组件 | 段 | 组件版本 | API | 文档版本 | match_level | risk |
|---|---|---|---|---|---|---|---|---|

完成前检查：

- 平台和版本已确认。
- 已调用 `list_products` 校验平台存在。
- 已调用 `list_product_components` 确认组件范围。
- 每个基线调用需求都调用了 `find_apis_for_requirement`。
- 每个最终 API 都调用了 `get_api_detail`。
- 所有风险都展示给用户并被确认。
- 没有使用旧版搜索类或候选提交类 MCP 工具。
- 没有编造组件/API。

# MCP Baseline Rules

## 当前 MCP 工具

只使用当前项目真实存在的工具：

- `health_check()`
- `list_products()`
- `list_product_components(product_id, product_version, component_overrides)`
- `list_component_segments(component_id)`
- `list_component_doc_versions(component_id, segment_id?)`
- `resolve_component_doc_version(component_id, segment_id, component_version)`
- `find_apis_for_requirement(product_id, product_version, requirement_item, component_overrides, limit)`
- `get_api_detail(component_id, segment_id, component_version, method, api_path)`
- `submit_component_version_doc_mapping(...)`

不要调用旧版搜索类或候选提交类 MCP 工具。

## 高准确率原则

- `product_id`、`component_id`、`segment_id` 按不区分大小写处理，展示时统一大写。
- API 路径保持 MCP 返回值；Swagger `basePath` 已在入库阶段拼入 `api_path`，不要自行裁剪。
- 每个需求项单独检索，不把多个需求合成一个查询。
- MCP 只检索平台依赖能力，不检索外部执行动作。
- 查询词必须描述“要从平台获取/校验/监听/写回什么”，不要把需求标题或外部动作原样作为查询词。
- 每个最终选中的 API 必须经过 `get_api_detail`。
- 输出方案必须带组件版本、组件段、文档版本、`match_level`、`risk`、请求/响应契约。

## Phase 2.5 基线调用预检

先对每个需求分解项做“显式功能 + 平台依赖”分析，再让用户确认是否调用平台基线组件。

平台依赖类型：

- 触发依赖
- 目标对象解析依赖
- 主数据依赖
- 详情补全依赖
- 规则策略依赖
- 状态写回依赖
- 查询统计依赖
- 外部系统边界

目标对象解析兜底规则：

- 只要存在“发送给谁、推送给谁、分派给谁、谁审批、谁处理、谁接收、作用到哪个资源/设备/业务对象”，就必须生成平台上下文动作或 `UNDECIDED` 确认项。
- 如果目标来自平台用户、组织、角色、权限范围、资源归属、对象负责人、订阅关系、告警策略、流程参与人或配置策略，应进入 MCP 检索。
- 如果目标是手工输入，也要确认是否需要平台校验、补全、权限过滤或联系方式查询。
- 不允许因为外部动作是定制实现，就忽略目标对象解析。

每个需求项拆出两类动作：

- 执行动作：定制服务或外部系统真正要做的事，例如发送、同步、回调、保存、渲染、统计、调度。
- 平台上下文动作：为了完成执行动作，需要从平台获取、校验、监听、补全、关联或写回的对象和数据。

MCP 只检索平台上下文动作。只有输入完全来自用户手工录入、外部系统回调或定制库自身数据，且输出不需要平台补全、校验、关联、写回、权限过滤或状态字段，才可标记为不调用基线组件。

输出表格：

| 需求项 | 子能力 | 执行动作 | 平台上下文动作 | 实现方式分类 | 平台依赖类型 | 依赖对象/数据来源 | 是否进入 MCP | MCP 检索任务 | 备注 |
|---|---|---|---|---|---|---|---|---|---|

MCP 检索任务必须是平台能力表达，例如“查询候选业务对象列表”“根据对象 ID 查询详情”“校验用户权限范围”“监听某类平台事件”“写回处理状态”“查询字典/规则/配置”。不能写“发送短信”“调用第三方接口”“推送消息到外部系统”。

## Phase 3 MCP 检索

1. 先调用 `health_check()`。失败则停止并让用户启动 MCP 服务或确认连接方式。
2. 调用 `list_products()` 确认目标 `product_id/product_version` 已入库。未入库时不继续检索 API。
3. 调用 `list_product_components(...)` 确认组件范围。现场组件单独升级时放入 `component_overrides` 后重查。
4. 将 Phase 2.5 输出的 MCP 检索任务展开为队列：

| 检索任务编号 | 来源需求项 | 子能力 | 实现方式分类 | 平台上下文动作 | 依赖对象/数据来源 | 查询词 | 预期字段覆盖 |
|---|---|---|---|---|---|---|---|

5. 人工审阅模式下，检索前展示检索队列表并等待确认。
6. 对每个检索任务单独调用 `find_apis_for_requirement`：

```text
find_apis_for_requirement({
  "product_id": "<PRODUCT_ID>",
  "product_version": "<PRODUCT_VERSION>",
  "requirement_item": "<只写当前平台上下文动作、依赖对象/数据来源、查询条件、期望返回>",
  "component_overrides": { ... },
  "limit": 8
})
```

检索后必须输出 MCP 调用记录：

| 检索任务编号 | MCP 工具 | 请求参数摘要 | 返回候选数 | Top 候选 | 采纳状态 | 淘汰/采纳原因 |
|---|---|---|---|---|---|---|

采纳状态：

- `PENDING_USER_CHOICE`
- `REJECTED_SCENE_MISMATCH`
- `REJECTED_FIELD_GAP`
- `REJECTED_RISK`
- `NO_CANDIDATE`
- `NEED_KB_IMPORT`

## 候选过滤

候选 API 必须满足：

- `api_identity` 存在。
- `api_contract` 存在。
- `lifecycle_status` 不是 `REMOVED`。
- 组件在 `list_product_components` 返回范围内。
- `risk` 可解释。
- 需求字段能被请求参数或响应字段覆盖。
- API 业务场景满足当前平台上下文动作，不能只因关键词相同就采用。

置信度：

- 高：`match_level=EXACT` 或 `MANUAL`，契约存在，risk 为空或很低。
- 中：同 major 最近文档版本回退，契约存在，字段基本覆盖。
- 低：只有关键词匹配、契约回退明显、字段覆盖不完整。
- 不可用：无契约、接口删除、组件不在平台基线范围内。

## Phase 4 API 详情确认

对每个候选 Top 3 调用：

```text
get_api_detail({
  "component_id": "<COMPONENT_ID>",
  "segment_id": "<SEGMENT_ID>",
  "component_version": "<COMPONENT_VERSION>",
  "method": "<GET|POST|...>",
  "api_path": "<完整 api_path>"
})
```

按检索任务输出用户可选择表：

| 检索任务编号 | 来源需求项 | 平台上下文动作 | 排名 | 组件/段 | API | 文档版本 | 请求字段 | 响应字段 | 风险 | 推荐级别 |
|---|---|---|---|---|---|---|---|---|---|---|

每个检索任务都要让用户确认：

- 选择某个 API
- 改为定制实现
- 以上都不合适，用户指定组件/API
- 需要先补知识库

## MCP 为空或不确定时

不要编造。按顺序处理：

1. 检查平台基线是否存在。
2. 检查组件是否被现场覆盖。
3. 检查检索任务是否误用了外部执行动作或功能标题；如果是，回到 Phase 2.5 重写平台上下文动作。
4. 检查候选 API 是否只是关键词相似但业务场景不一致。
5. 调用 `list_component_segments` 和 `list_component_doc_versions` 看是否缺组件段或文档版本。
6. 若用户确认某组件版本应使用某文档版本，调用 `submit_component_version_doc_mapping`。
7. 若知识库缺 API，提示使用 `baseline-api-importer` skill 导入 Swagger，并询问是否先补知识库。

禁止输出“因为外部动作没有匹配 API，所以本需求全部定制，不调用基线组件”。正确做法是按平台上下文动作逐项说明哪些找到、哪些没找到、哪些需补知识库或用户确认。

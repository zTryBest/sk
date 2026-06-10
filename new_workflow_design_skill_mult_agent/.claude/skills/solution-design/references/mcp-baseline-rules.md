# MCP Baseline Rules

> **STOP — 读到本文件说明已完成 Step 3 平台依赖分析，确认有 BASELINE_API_REUSE / HYBRID 项需要 MCP 检索。**
>
> 下面 Phase 2.5 的「平台上下文动作 → MCP 检索任务」是强制步骤，不是参考。
> 有平台依赖但不分析 → 禁止标 CUSTOM_CODE。
> 分析出 MCP 检索任务但不调 MCP → 任务失败。
>
> **MCP 调用必须真正发生**：`health_check` → `list_products` → `list_product_components` → `find_apis_for_requirement` → `get_api_detail`。
> 每次调用的工具名、参数、候选数、采纳/淘汰原因必须写入 `02_solution.json.mcp_evidence[]`。
> `NO_CANDIDATE` 或 `NEED_KB_IMPORT` 是正常结果，不调才是异常。

## MCP 服务：knowledge-base

`mcp__knowledge-base__*` 是已注册的原生工具，直接调用即可。不要通过 Bash 安装或启动任何东西。

## 可用工具

```
mcp__knowledge-base__health_check()
mcp__knowledge-base__list_products()
mcp__knowledge-base__list_product_components(product_id, product_version, component_overrides)
mcp__knowledge-base__list_component_segments(component_id)
mcp__knowledge-base__list_component_doc_versions(component_id, segment_id?)
mcp__knowledge-base__resolve_component_doc_version(component_id, segment_id, component_version)
mcp__knowledge-base__find_apis_for_requirement(product_id, product_version, requirement_item, component_overrides, limit)
mcp__knowledge-base__get_api_detail(component_id, segment_id, component_version, method, api_path)
mcp__knowledge-base__submit_component_version_doc_mapping(...)
```

不要调用旧版搜索类或候选提交类工具。

## 高准确率原则

- `product_id`、`component_id`、`segment_id` 按不区分大小写处理，展示时统一大写。
- API 路径保持 MCP 返回值；Swagger `basePath` 已在入库阶段拼入 `api_path`，不要自行裁剪。
- 每个需求项单独检索，不把多个需求合成一个查询。
- MCP 只检索平台依赖能力，不检索外部执行动作。
- 查询词必须描述"要从平台获取/校验/监听/写回什么"，不要把需求标题或外部动作原样作为查询词。
- 每个最终选中的 API 必须经过 `mcp__knowledge-base__get_api_detail`，并把 `method`、`api_path`、请求参数/契约、响应结果/契约写入 `artifacts/02_solution.json.selected_baseline_apis`。
- 版本匹配是硬约束：`resolved_doc_version` 只能使用小于或等于它的 `contract_doc_version`。低版本组件不能采纳高版本才出现的 API。
- 输出方案必须带组件版本、组件段、文档版本、`match_level`、`risk`、请求/响应契约。

## Phase 2.5 基线调用预检

先对每个需求分解项做"显式功能 + 平台依赖"分析，再让用户确认是否调用平台基线组件。

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
- 只要存在"发送给谁、推送给谁、分派给谁、谁审批、谁处理、谁接收、作用到哪个资源/设备/业务对象"，就必须生成平台上下文动作或 `UNDECIDED` 确认项。
- 如果目标来自平台用户、组织、角色、权限范围、资源归属、对象负责人、订阅关系、告警策略、流程参与人或配置策略，应进入 MCP 检索。
- 如果目标是手工输入，也要确认是否需要平台校验、补全、权限过滤或联系方式查询。
- 不允许因为外部动作是定制实现，就忽略目标对象解析。

每个需求项拆出两类动作：
- 执行动作：定制服务或外部系统真正要做的事。
- 平台上下文动作：为了完成执行动作，需要从平台获取、校验、监听、补全、关联或写回的对象和数据。

MCP 只检索平台上下文动作。

输出表格：

| 需求项 | 子能力 | 执行动作 | 平台上下文动作 | 实现方式分类 | 平台依赖类型 | 依赖对象/数据来源 | 是否进入 MCP | MCP 检索任务 | 备注 |
|---|---|---|---|---|---|---|---|---|---|

## Phase 3 MCP 检索

1. 先调用 `mcp__knowledge-base__health_check()`。失败则停止并报告 MCP 服务不可用。
2. 调用 `mcp__knowledge-base__list_products()` 确认目标 `product_id/product_version` 已入库。
3. 调用 `mcp__knowledge-base__list_product_components(...)` 确认组件范围。
4. 对每个涉及基线 API 的组件段调用 `mcp__knowledge-base__resolve_component_doc_version(component_id, segment_id, component_version)`，记录可用的 `resolved_doc_version`。
5. 将 Phase 2.5 的 MCP 检索任务展开为队列：

| 检索任务编号 | 来源需求项 | 子能力 | 实现方式分类 | 平台上下文动作 | 依赖对象/数据来源 | 查询词 | 预期字段覆盖 |
|---|---|---|---|---|---|---|---|

6. 对每个检索任务单独调用 `mcp__knowledge-base__find_apis_for_requirement`：

```
mcp__knowledge-base__find_apis_for_requirement({
  "product_id": "<PRODUCT_ID>",
  "product_version": "<PRODUCT_VERSION>",
  "requirement_item": "<只写当前平台上下文动作、依赖对象/数据来源、查询条件、期望返回>",
  "component_overrides": { ... },
  "limit": 8
})
```

检索后输出 MCP 调用记录：

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
- `contract_doc_version <= resolved_doc_version`。
- `lifecycle_status` 不是 `REMOVED`。
- 组件在 `list_product_components` 返回范围内。
- `risk` 可解释。
- 需求字段能被请求参数或响应字段覆盖。
- API 业务场景满足当前平台上下文动作。

置信度：
- 高：`match_level=EXACT` 或 `MANUAL`，契约存在，risk 为空或很低。
- 中：同 major 最近低版本文档回退，契约存在，字段基本覆盖。
- 低：只有关键词匹配、契约回退明显、字段覆盖不完整。
- 不可用：无契约、接口删除、组件不在平台基线范围内、契约版本高于可用文档版本。

## Phase 4 API 详情确认

对每个候选 Top 3 调用：

```
mcp__knowledge-base__get_api_detail({
  "component_id": "<COMPONENT_ID>",
  "segment_id": "<SEGMENT_ID>",
  "component_version": "<COMPONENT_VERSION>",
  "method": "<GET|POST|...>",
  "api_path": "<完整 api_path>"
})
```

将返回结果中的接口路径、请求参数、请求体、响应字段、错误响应和示例整理到 `artifacts/02_solution.json.selected_baseline_apis[].request` 与 `.response`。

详情为空、字段覆盖不足或无法判断响应结果时，不能把该 API 标记为最终采纳。

每个最终采纳 API 必须写入版本兼容证据：

```json
{
  "component_version": "1.7.0",
  "resolved_doc_version": "1.7.0",
  "contract_doc_version": "1.7.0",
  "version_match_policy": "EXACT|BACKWARD_COMPATIBLE|MANUAL_MAPPING",
  "version_compatibility": "PASS",
  "version_risk": ""
}
```

如果返回 `NO_COMPATIBLE_CONTRACT`、`NEED_KB_IMPORT`、版本不可比较，或 `contract_doc_version > resolved_doc_version`，不能采纳为最终 API。

## MCP 为空或不确定时

不要编造。按顺序处理：

1. 检查平台基线是否存在。
2. 检查组件是否被现场覆盖。
3. 检查检索任务是否误用了外部执行动作；如果是，回到 Phase 2.5 重写平台上下文动作。
4. 检查候选 API 是否只是关键词相似但业务场景不一致。
5. 调用 `mcp__knowledge-base__list_component_segments` 和 `mcp__knowledge-base__list_component_doc_versions` 看是否缺组件段或文档版本。
6. 若用户确认某组件版本应使用某文档版本，调用 `mcp__knowledge-base__submit_component_version_doc_mapping`。
7. 若知识库缺 API，提示需要导入 Swagger，并询问是否先补知识库。

禁止输出"因为外部动作没有匹配 API，所以本需求全部定制，不调用基线组件"。正确做法是按平台上下文动作逐项说明哪些找到、哪些没找到、哪些需补知识库或用户确认。

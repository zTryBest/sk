# 阶段细则

## Phase 1：加载需求 artifact

优先读取：

```text
artifacts/01_requirement.json
```

提取：
- `project_name`
- `product.product_id`
- `product.product_version`
- `functional_requirements`
- `non_functional_requirements`
- `constraints`
- `platform_dependency_tasks`
- `risks`

如果需求 artifact 是 `draft`，只能输出草稿方案。

## Phase 2：架构决策

至少覆盖：
- 应用形态。
- 前端形态。
- 后端服务形态。
- 数据库类型。
- 中间件和异步机制。
- 部署形态。
- 安全、日志、审计、监控和告警。

缺少关键决策时写入 `open_decisions`。

## Phase 3：实现方式分类

每个功能项或子能力必须分类：
- `BASELINE_API_REUSE`
- `CUSTOM_CODE`
- `EXTERNAL_INTEGRATION`
- `HYBRID`
- `NO_API_NEEDED`
- `UNDECIDED`

分类结果写入 `implementation_classification`。

## Phase 4：MCP 检索计划

对 `BASELINE_API_REUSE` 和 `HYBRID` 生成 MCP 检索任务。

检索词要描述平台上下文能力，例如：
- 查询对象详情。
- 校验权限。
- 获取规则。
- 写回状态。
- 查询统计数据。

不要用外部动作作为 MCP 查询词。

## Phase 5：baseline API 证据

通过 `mcp__knowledge-base__*` 工具直接调用 MCP 服务能力（不走命令行），记录：
- 工具名（如 `mcp__knowledge-base__find_apis_for_requirement`）。
- 请求参数。
- 候选数量。
- 候选摘要。
- 采纳或淘汰原因。

选中的 API 必须经过 `mcp__knowledge-base__get_api_detail` 获取详情，并具备：
- `component_id`
- `component_version`
- `method`
- `api_path`
- `request`
- `response`
- `resolved_doc_version`
- `contract_doc_version`
- `version_compatibility`

## Phase 6：详细方案设计

输出：
- `modules`
- `data_model`
- `api_design`
- `external_integrations`
- `frontend_design`
- `test_points`
- `risks`

MCP 证据只能证明 baseline API 可复用，不能替代定制实现、外部集成、数据库和异常处理设计。

## Phase 7：输出和校验

写入：

```text
artifacts/02_solution.json
```

运行：

```text
python scripts/validate_solution.py --input artifacts/02_solution.json
```

校验失败时：
- 缺少事实或业务决策：写 `draft` 和 `open_decisions`，交给 Human Gate。
- 结构字段缺失：基于已知事实补齐后重新校验。

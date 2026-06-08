---
name: solution-design
description: >
  当 DesignAgent 需要基于 `artifacts/01_requirement.json` 产出方案设计时使用。本 Skill 只负责方案设计方法论：
  架构、模块、数据模型、接口方案、baseline API 选择、MCP 证据、风险和 `artifacts/02_solution.json` 输出；
  不负责编码、测试、流程调度或 Human Gate 持久化。
---

# 方案设计 Skill

本 Skill 说明“方案设计怎么做”。DesignAgent 负责调用本 Skill，Orchestrator 负责阶段顺序和 Human Gate。

## 阶段边界

应该做：
- 读取 `artifacts/01_requirement.json`。
- 设计整体架构、模块边界、数据模型、接口方案、外部集成、异常处理和测试要点。
- 使用 baseline-api MCP 查询可复用组件和 API。
- 把 MCP 调用、候选 API、采纳/淘汰原因和版本兼容证据写入 `artifacts/02_solution.json`。
- 对无法确认的设计决策输出 `open_decisions`，交给 Human Gate。

禁止做：
- 不直接写业务代码。
- 不修改需求结论；只能提出风险、疑问或变更建议。
- 不跳过 MCP baseline API 选择。
- 不把 MCP 结果当成完整方案，定制代码、外部集成、数据库和运维设计仍要独立设计。
- 不调度后续 Agent。

## 输入

必须读取：

```text
artifacts/01_requirement.json
```

可以读取：
- Human Gate 对需求阶段或设计阶段的补充意见。
- baseline-api MCP 的工具列表和返回结果。

如果 `01_requirement.json.status=draft` 或仍有关键 `open_questions`，只能输出草稿方案，并把阻塞点写入 `open_decisions`。

## 设计流程

### 1. 需求加载

提取：
- `project_name`
- `product_id`
- `product_version`
- 功能需求和非功能需求
- 平台依赖任务
- 约束和风险

不要依赖聊天历史补事实。

### 2. 架构和模块设计

输出：
- 应用形态。
- 前端形态。
- 后端服务形态。
- 数据库类型。
- 中间件和异步机制。
- 部署和运行环境。
- 安全、日志、审计、监控和告警。

缺少关键选择时，写入 `open_decisions`。

### 3. 实现方式分类

每个功能项或子能力必须分类：
- `BASELINE_API_REUSE`
- `CUSTOM_CODE`
- `EXTERNAL_INTEGRATION`
- `HYBRID`
- `NO_API_NEEDED`
- `UNDECIDED`

`BASELINE_API_REUSE` 和 `HYBRID` 必须进入 MCP 检索计划。

### 4. baseline-api MCP 查询

MCP 是知识库工具，不是调度器。

必须记录：
- MCP 工具名。
- 查询条件。
- 候选数量。
- 候选 API。
- 采纳或淘汰原因。
- `component_id`
- `component_version`
- `method`
- `api_path`
- 请求契约。
- 响应契约。
- `resolved_doc_version`
- `contract_doc_version`
- `version_compatibility`

低版本组件不能采纳高版本才存在的 API。无法确认版本兼容时，进入 Human Gate。

### 5. 接口、数据和集成设计

输出：
- Gateway REST API。
- 请求/响应字段。
- 数据表或配置项。
- 状态流转。
- 错误码和异常处理。
- 外部系统协议、认证、超时、重试、回调和降级。
- 测试要点。

### 6. 输出 artifact

必须输出：

```text
artifacts/02_solution.json
```

推荐结构：

```json
{
  "schema_version": "1.0",
  "status": "final|draft",
  "project_name": "",
  "architecture": {},
  "implementation_classification": [],
  "mcp_search_plan": [],
  "mcp_call_log": [],
  "selected_baseline_apis": [],
  "modules": [],
  "data_model": [],
  "api_design": [],
  "external_integrations": [],
  "frontend_design": [],
  "test_points": [],
  "open_decisions": [],
  "risks": []
}
```

JSON 必须用 serializer 写入，写完后立即 `json.load` 校验。

## 校验

优先运行：

```text
python scripts/validate_solution.py --input artifacts/02_solution.json
```

## 完成标准

只有满足以下条件，DesignAgent 才能把本阶段标为 `final`：
- 已读取并使用 `artifacts/01_requirement.json`。
- 每个功能项都有实现方式分类。
- 需要复用 baseline API 的能力都有 MCP 证据。
- 选中的 baseline API 具备详情契约和版本兼容证据。
- 定制代码、外部集成、数据库、接口、异常和测试设计完整。
- 无关键 `open_decisions`。
- `artifacts/02_solution.json` 可被 JSON 解析并通过校验。

否则必须输出 `draft` 并进入 Human Gate。

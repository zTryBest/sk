# Phase Details

## Phase 0：上下文重置和交接文件加载

如果当前 session 刚执行过 requirement-analysis，必须先重置上下文，避免沿用上一阶段写作惯性。

优先读取：

```text
<项目根目录>/requirements/<项目名称或平台版本标识>/requirement-handoff.json
<项目根目录>/requirements/<项目名称或平台版本标识>/design-phase-handoff.md
```

同时读取 handoff 中的 `requirement_doc`。如果没有 `requirement-handoff.json`，才读取 `design-phase-handoff.md`；如果两者都没有，才读取用户指定需求分析文档；如果三者都没有，询问需求文档路径。

加载后输出上下文摘要：`product_id`、`product_version`、功能项数量、平台依赖任务数量、未解决风险数量，并等待用户确认。

创建设计状态账本：

```text
<项目根目录>/requirements/<项目名称或平台版本标识>/design-phase-state.md
```

状态账本结构：

```markdown
# Design-phase State

## Current Phase

## Confirmed Decisions

## Pending Decisions

## Implementation Classification

## MCP Search Plan

## MCP Call Log

## Selected Baseline APIs

## Custom Implementation Decisions

## External Integration Decisions

## Next Step
```

每个阶段结束时更新状态账本。继续下一阶段前，先读取状态账本确认没有跳阶段。

## Phase 1：加载需求分析结果

优先从 `requirement-handoff.json` 读取结构化字段。只有 JSON 缺失或校验失败时，才从 `design-phase-handoff.md` 和 `需求分析.md` 抽取，并写回 `design-phase-state.md`。

提取：

- `product_id`
- `product_version`
- `component_overrides`
- 需求分解项列表
- 用户角色、页面、数据对象、外部调用线索
- 每个需求项的输入来源、输出去向、关键数据对象、状态流转和平台依赖
- 每个需求项是否依赖平台既有对象、事件、规则、权限、配置、主数据或展示字段
- 待 design-phase 检索意图；没有提供时根据平台依赖重新生成

`product_id` 或 `product_version` 缺失时停止确认。

## Phase 2：架构选型

默认定制代码使用 SpringBoot 单体，除非用户明确要求拆分微服务。调用平台基线组件时，优先通过注册中心和平台规范调用，不设计前端直连基线组件。

架构和中间件不是 MCP 决策，不能通过搜索基线 API 自动决定。先根据需求、现有平台习惯和风险给出建议，再让用户确认。

决策表：

| 决策项 | 推荐方案 | 可选方案 | 推荐理由 | 风险/代价 | 是否需要用户确认 |
|---|---|---|---|---|---|

至少覆盖：

- 定制服务形态：SpringBoot 单体 / 独立微服务 / 嵌入现有服务。
- 前端形态：配置页、查询页、管理页。
- 数据库：平台既有库 / 新增业务表 / 独立库；数据库类型未知时必须询问。
- 异步机制：同步调用 / MQ / 定时任务 / 线程池 / 平台任务调度。
- 重试和补偿：本地重试 / 任务表 / MQ 重试 / 平台任务能力。
- 配置管理：定制配置表 / 平台配置中心 / 环境变量 / 密钥管理。
- 安全和凭据：加密存储、脱敏展示、操作审计。
- 外部集成客户端：SOAP/REST/SDK/文件/其他协议。
- 日志、审计、监控和告警。

## Phase 2.5：基线调用预检

本阶段的详细平台依赖和 MCP 检索任务规则见 `mcp-baseline-rules.md`。输出表格后必须停止，让用户确认实现方式分类和 MCP 检索任务。

## Phase 3：MCP 基线范围和候选 API

执行健康检查、平台版本校验、组件范围确认、逐平台依赖检索和候选过滤。细则见 `mcp-baseline-rules.md`。

## Phase 4：API 详情确认

对候选 Top API 调用 `get_api_detail`，让用户按检索任务确认选择。细则见 `mcp-baseline-rules.md`。

## Phase 5：前端页面设计

页面只调用本项目 Gateway API，不直连基线组件 API。

每个页面输出：

- Route
- 初始状态
- 查询/提交/错误交互流程
- 依赖的 Gateway API
- 间接依赖的基线 API 证据编号

阶段结束后等待确认。

## Phase 6：后端 API 设计

设计本项目 Gateway REST API，并说明每个接口如何调用已确认的基线 API。

先输出实现方式矩阵：

| 来源需求项 | 子能力 | 实现方式分类 | 本项目模块/类职责 | 是否调用基线 API | 是否调用外部系统 | 证据编号/说明 |
|---|---|---|---|---|---|---|

按实现方式分别说明：

- `BASELINE_API_REUSE`：调用哪个基线 API、请求映射、响应映射、fallback、错误处理和 MCP 证据编号。
- `CUSTOM_CODE`：定制模块、核心类/服务职责、数据表、校验规则、状态流转、错误处理和测试点。
- `EXTERNAL_INTEGRATION`：外部协议、认证、请求封装、超时、重试、回调/回执、降级和审计。
- `HYBRID`：分别说明定制/外部执行动作和平台上下文动作。
- `NO_API_NEEDED`：说明为什么不需要后端或基线 API。

每个跨组件调用必须包含调用场景、组件和组件段、实际组件版本、HTTP method + api_path、请求映射、响应映射、fallback、错误处理、MCP 证据编号。

## Phase 7：数据库设计

写 DDL 前先确认数据库类型。每张表标注 `NEW` 或 `EXTEND`。阶段结束后等待确认。

## Phase 8：内部协议设计

设计 MQ、Feign、异步任务、幂等、补偿和 fallback。阶段结束后等待确认。

## Phase 9：设计文档

设计文档不要以 MCP 搜索结果为主体。MCP 证据只是基线复用的证据链；完整设计必须覆盖架构/中间件、实现方式分类、定制模块、外部集成、数据库、接口、异常和运维。

输出文档和 JSON 契约见 `output-contracts.md`。

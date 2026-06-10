---
name: solution-design
description: >
  当 DesignAgent 需要基于 `artifacts/01_requirement.json` 产出方案设计时使用。本 Skill 只负责方案设计方法论：
  架构、模块、数据模型、接口方案、baseline API 选择、MCP 证据、风险和 `artifacts/02_solution.json` 输出；
  不负责编码、测试、流程调度或 Human Gate 持久化。
---

# 方案设计 Skill

本 Skill 说明"方案设计怎么做"。谁来调用、是否暂停、Human Gate 如何确认、下一阶段何时开始，由 Orchestrator 和 `.claude/agents/design-agent.md` 决定。

## 阶段边界

应该做：
- 读取 `artifacts/01_requirement.json`。
- 设计整体架构、模块边界、数据模型、接口方案、外部集成、异常处理和测试要点。
- 通过 `mcp__knowledge-base__*` 工具直接查询可复用组件和 API。
- 把 MCP 调用记录、候选 API、采纳/淘汰原因和版本兼容证据写入 `artifacts/02_solution.json`。
- 对无法确认的设计决策输出 `open_decisions`。

禁止做：
- 不直接写业务代码。
- 不修改需求 artifact；只能提出风险、疑问或变更建议。
- 不跳过 MCP baseline API 查询。
- 不把 MCP 结果当成完整方案，定制代码、外部集成、数据库和运维设计仍要独立设计。
- 不调度后续 Agent。
- 不写 `.ai-dev/` 下的流程控制文件。

## 输入

必须读取：

```text
artifacts/01_requirement.json
```

可选输入：
- Human Gate 对需求阶段或设计阶段的补充意见。
- knowledge-base MCP 服务的查询结果。

如果 `01_requirement.json.status=draft` 或仍有关键 `open_questions`，只能输出草稿方案。

## 执行流程

严格按以下顺序执行，每一步的详细规则见对应 reference 文件。

### Step 1: 需求加载

提取：
- `project_name`、`product_id`、`product_version`
- 功能需求和非功能需求
- 平台依赖任务
- 约束和风险

不依赖聊天历史补事实。

### Step 2: 架构和模块设计

**按 `references/phase-details.md` Phase 2 执行。**

输出：应用形态、前端形态、后端服务形态、数据库类型、中间件、部署环境、安全/日志/监控。

### Step 3: 实现方式分类 + 平台依赖分析（强制步骤）

**第一动作：读 `references/mcp-baseline-rules.md` Phase 2.5。读完之前不能做分类。**

对每个功能项：
1. 按 Phase 2.5 模板拆出「执行动作」和「平台上下文动作」。
2. 平台上下文动作不为空 → 分类为 `BASELINE_API_REUSE` 或 `HYBRID`，生成 MCP 检索任务（Phase 2.5 表格）。
3. 平台上下文动作为空 → 分类为 `CUSTOM_CODE` / `EXTERNAL_INTEGRATION` / `NO_API_NEEDED`。
4. 不确定 → `UNDECIDED`，写入 `open_decisions`。

每个功能项或子能力必须带以下分类之一：
- `BASELINE_API_REUSE` | `CUSTOM_CODE` | `EXTERNAL_INTEGRATION` | `HYBRID` | `NO_API_NEEDED` | `UNDECIDED`

**停止并检查**（分类完成后、下一动作前）：
```
读 implementation_classification 表格，统计：
  BASELINE_API_REUSE: N 项
  HYBRID:             M 项

IF N + M == 0:
  在 issues 中记录 reason: "本需求所有功能项均无平台依赖，平台上下文动作为空"
  → 跳过 Step 4，直接进 Step 5
IF N + M > 0:
  → 必须进 Step 4，对每项调 MCP
```

**禁止在没有平台上下文分析表格的情况下凭感觉标 CUSTOM_CODE。**

### Step 4: knowledge-base MCP 查询

**调用此步骤的前置条件：Step 3 的 N + M > 0。否则跳过。**

**第一动作：读 `references/mcp-baseline-rules.md` Phase 3-4。读完之前不能调 MCP。**

**调用方式：直接使用 `mcp__knowledge-base__*` 原生工具，与 Read/Write/Grep 同级。严禁通过 Bash、Python 脚本或 curl 命令间接调用 MCP。**

可用工具：

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

必须记录每次调用的工具名、请求参数、返回候选数、采纳/淘汰原因。

### Step 5: 接口、数据和集成设计

**按 `references/phase-details.md` Phase 6 执行。**

输出：Gateway REST API、请求/响应字段、数据表、状态流转、错误码、外部系统协议、测试要点。

### Step 6: 输出 artifact

**严格按 `references/output-contracts.md` 的 JSON Schema 和写入规则执行。**

输出 `artifacts/02_solution.json`，使用 Write 工具直接写入，写入后用 Read 工具读回验证格式正确。不要通过 Bash/Python 写入或校验。

## 完成标准

只有满足以下条件才能标为 `final`：
- 已读取并使用 `artifacts/01_requirement.json`。
- 每个功能项都有平台依赖分析和实现方式分类（分析结论是"无平台依赖"也是有效的）。
- 分析出平台依赖的能力都有 MCP 证据（无平台依赖项不需要）。
- 选中的 baseline API 具备详情契约和版本兼容证据。
- 定制代码、外部集成、数据库、接口、异常和测试设计完整。
- 无关键 `open_decisions`。
- `artifacts/02_solution.json` 可被 JSON 解析。

否则输出 `draft`。

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
- MCP 只检索平台依赖能力，不检索外部系统执行动作。外部发送、外部推送、第三方同步、外部审批、外部支付、外部设备控制等动作本身通常是定制/外部适配；如果这些动作的入参、触发条件、接收目标、业务对象或展示字段来自平台，必须把它们拆成独立的平台依赖检索任务。
- 不要把需求标题或外部动作原样作为 MCP 查询词。查询词必须描述“要从平台获取/校验/监听/写回什么”，而不是“要对外执行什么”。
- 对通知、推送、发送、分派、审批、抄送、派单、升级、授权、订阅、触达等动作，必须先解析“目标对象”：作用到谁/什么对象、目标从哪里来、如何过滤、如何取联系方式或平台标识。原文没写时也要标记为 `UNDECIDED`，不能默认跳过平台依赖。
- 每个最终选中的 API 必须经过 `get_api_detail` 二次确认。
- 输出方案时必须带 MCP 证据：组件版本、组件段、文档版本、`match_level`、`risk`、请求/响应契约。
- 若 MCP 为空、契约为空、风险不可接受或版本跨 major 不确定，停止并用 `AskQuestion` 问用户；不要猜。

## 运行模式

默认使用“人工审阅模式”。除非用户明确说“全自动”“自动完成所有阶段”“不要逐阶段确认”，否则不能一口气生成完整设计文档。

人工审阅模式下：

- Phase 2 架构和中间件必须先让用户确认，不能跳过。
- Phase 2.5 实现方式和基线调用预检必须先让用户确认，不能直接进入 MCP 检索。
- Phase 3 MCP 检索前必须展示检索计划；检索后必须展示实际调用摘要和候选结果，等待用户确认。
- Phase 4 候选 API 必须让用户选择；不能自动采用候选 API。
- 每个阶段完成后立即停止，等待用户回复后再进入下一阶段。

全自动模式下也要输出每一步的决策依据、MCP 调用记录和被淘汰候选原因；不能隐藏 MCP 查询过程。

## 实现方式分类

每个功能项或子能力都必须先分类，再决定是否查 MCP：

- `BASELINE_API_REUSE`：直接复用平台基线 API。
- `CUSTOM_CODE`：本项目定制代码实现，不调用基线 API。
- `EXTERNAL_INTEGRATION`：对接第三方或外部系统。
- `HYBRID`：定制代码/外部集成 + 平台基线 API 获取上下文或写回状态。
- `NO_API_NEEDED`：纯页面展示、纯配置说明、纯文档或无需后端调用。
- `UNDECIDED`：信息不足，需要 `AskQuestion` 确认。

分类规则：

- 不要因为某个能力能查到 API 就自动选 `BASELINE_API_REUSE`。
- 不要因为某个能力是定制页面或定制表，就自动选 `CUSTOM_CODE`。
- 外部集成类能力通常至少包含 `EXTERNAL_INTEGRATION`；如果入参、触发、目标对象、展示字段或写回状态来自平台，则应是 `HYBRID`。
- 候选 API 只证明“可能可复用”，最终是否复用必须结合业务场景、字段覆盖、版本风险、调用成本和用户选择。

## 用户交互规则

直连人工模式下，design-phase 涉及用户交互时必须使用 `AskQuestion`，不能用普通助手消息直接提问或让用户选择。

如果输入中明确包含 `worker_mode: true`，进入 orchestrator worker 模式：不能直接使用 `AskQuestion`，需要人工确认时必须写 `pending-questions.json` 和 `worker-result.json(status=NEED_USER_INPUT)` 后停止，由主流程负责询问用户。

适用范围包括但不限于：

- 缺少 `product_id`、`product_version`、数据库类型、运行环境等必要信息。
- 每个阶段结束后的确认。
- 架构、中间件、运行环境、部署形态、定制模块边界的确认。
- 每个功能项或子能力的实现方式分类确认。
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

## Orchestrator Worker 模式

当 prompt、`workflow-state.json` 或用户明确指令包含 `worker_mode: true` 时，按 worker 模式执行。本模式用于让主 Claude Code session 保持干净，由隔离 worker 负责方案设计阶段。

worker 模式规则：

- 先读取 `workflow-state.json`、`decisions.jsonl`、`requirement-handoff.json` 和已有 `design-phase-state.md`。
- 不要直接向用户提问，不要调用 `AskQuestion`。
- 遇到架构选型、中间件、实现方式分类、MCP 检索计划、候选 API 选择、数据库类型、风险处理等人工确认点时，写 `pending-questions.json`，再写 `worker-result.json`，状态为 `NEED_USER_INPUT`，然后停止。
- 如果 `decisions.jsonl` 已经包含对应 `question_id` 的用户决策，使用该决策继续执行，并把该决策写入 `design-phase-state.md`、`design-handoff.json` 和设计文档。
- 每个问题必须有稳定 `id`；同一个问题重试时复用同一个 `id`，方便主流程去重和续跑。
- worker 模式下也不能隐藏 MCP 过程；MCP 搜索计划、调用日志、候选淘汰原因仍必须落入 `design-handoff.json`。
- 阶段完成时写 `worker-result.json(status=STAGE_COMPLETED)`，包含 `artifact_dir`、`handoff`、`validation` 和简短 `summary`。
- 校验失败且 worker 能修复时先修复一次；仍失败则写 `worker-result.json(status=VALIDATION_FAILED)`，不要进入原型、编码或自测阶段。

`pending-questions.json` 格式：

```json
{
  "status": "NEED_USER_INPUT",
  "stage": "design-phase",
  "phase": "Phase 2 架构选型",
  "question_batch_id": "DQ-0001",
  "questions": [
    {
      "id": "design.architecture.service_shape",
      "question": "",
      "options": [
        {
          "key": "",
          "label": "",
          "recommended": true,
          "description": ""
        }
      ],
      "impact": "",
      "default_if_full_auto": ""
    }
  ],
  "known_facts": [],
  "blocking_reason": ""
}
```

`worker-result.json` 格式：

```json
{
  "status": "STAGE_COMPLETED|NEED_USER_INPUT|VALIDATION_FAILED|BLOCKED",
  "stage": "design-phase",
  "phase": "",
  "artifact_dir": "",
  "handoff": "",
  "validation": "",
  "pending_questions": "",
  "summary": "",
  "next_action": ""
}
```

## 执行节奏

一次只执行一个阶段。直连人工模式下，每个阶段结束后必须用 `AskQuestion` 向用户确认，等待用户回复后再进入下一阶段。worker 模式下，每个阶段确认点必须转成 `pending-questions.json`，由 orchestrator 主流程询问用户并写入 `decisions.jsonl`。

0. Phase 0：上下文重置和交接文件加载
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

## Phase 0：上下文重置和交接文件加载

如果当前 session 刚执行过 requirement-analysis，必须先进行上下文重置，避免沿用上一阶段的写作惯性。

优先读取：

```text
<项目根目录>/requirements/<项目名称或平台版本标识>/requirement-handoff.json
<项目根目录>/requirements/<项目名称或平台版本标识>/design-phase-handoff.md
```

同时读取 handoff 中的 `requirement_doc`。如果没有 `requirement-handoff.json`，才读取 `design-phase-handoff.md`；如果两者都没有，才读取用户指定的需求分析文档；如果三者都没有，使用 `AskQuestion` 询问需求文档路径。

规则：

- design-phase 的事实来源优先级为：`requirement-handoff.json` > `design-phase-handoff.md` > `需求分析.md` > 当前对话摘要。
- 不要依赖需求分析阶段聊天历史来补事实；聊天历史只能作为提示，不能作为已确认结论。
- 如果 handoff 标记 `requirement_status: draft` 或 `草稿`，只能输出设计草案或预研，不能输出最终设计。
- 加载后先输出“上下文加载摘要”，列出 product_id、product_version、功能项数量、平台依赖任务数量、未解决风险数量。
- 使用 `AskQuestion` 让用户确认加载摘要后，再进入 Phase 1。

创建设计状态账本：

```text
<项目根目录>/requirements/<项目名称或平台版本标识>/design-phase-state.md
```

状态账本必须包含：

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

每个阶段结束时更新 `design-phase-state.md`。继续执行下一阶段前，先读取状态账本，确认没有跳阶段。

## Phase 1：加载需求分析结果

优先从 `requirement-handoff.json` 读取结构化字段。只有 JSON 缺失或校验失败时，才从 `design-phase-handoff.md` 和 `需求分析.md` 中抽取；抽取结果必须写回 `design-phase-state.md`，不能只留在对话上下文里。

提取并记录：

- `product_id`
- `product_version`
- 是否存在现场组件版本覆盖，形成 `component_overrides`，例如 `{ "AAA": "v1.3" }`
- 需求分解项列表，编号为 `R-01`、`R-02`
- 用户角色、页面、数据对象、外部调用线索
- 每个需求项的输入来源、输出去向、关键数据对象、状态流转和平台依赖
- 每个需求项是否依赖平台既有对象、事件、规则、权限、配置、主数据或展示字段
- 每个需求项中需要用户确认的数据来源、对象归属和系统边界
- 需求分析文档中的“待 design-phase 检索意图”；如果没有提供，必须根据平台依赖重新生成

如果 `product_id` 或 `product_version` 缺失，使用 `AskQuestion` 询问用户并停止。

## Phase 2：架构选型

默认定制代码使用 SpringBoot 单体，除非用户明确要求拆分微服务。调用平台基线组件时，优先通过注册中心和平台规范调用，不设计前端直连基线组件。

架构和中间件不是 MCP 决策，不能通过搜索基线 API 自动决定。必须先根据需求、现有平台习惯和风险给出建议，再使用 `AskQuestion` 向用户确认。

必须输出架构/中间件决策表：

| 决策项 | 推荐方案 | 可选方案 | 推荐理由 | 风险/代价 | 是否需要用户确认 |
|---|---|---|---|---|---|

至少覆盖：

- 定制服务形态：SpringBoot 单体 / 独立微服务 / 嵌入现有服务。
- 前端形态：是否需要配置页、查询页、管理页。
- 数据库：使用平台既有库 / 新增业务表 / 独立库；数据库类型未知时必须询问。
- 异步机制：同步调用 / MQ / 定时任务 / 线程池 / 平台任务调度。
- 重试和补偿：本地重试 / 任务表 / MQ 重试 / 平台任务能力。
- 配置管理：定制配置表 / 平台配置中心 / 环境变量 / 密钥管理。
- 安全和凭据：加密存储、脱敏展示、操作审计。
- 外部集成客户端：SOAP/REST/SDK/文件/其他协议。
- 日志、审计、监控和告警。

使用 `AskQuestion` 确认后停止。用户未确认前不能进入 Phase 2.5 或 MCP 检索。

## Phase 2.5：基线调用预检

先对每个需求分解项做“显式功能 + 平台依赖”分析，再使用 `AskQuestion` 逐个需求分解项询问是否需要调用平台基线组件。不要替用户批量决定。

平台依赖按以下类型检查，不要把它们写死到某个业务域：

- 触发依赖：需求是否由平台既有事件、流程、任务、状态变化或业务动作触发。
- 目标对象解析依赖：通知、推送、发送、分派、审批、派单、授权等动作的目标对象是否来自平台既有人员、组织、角色、权限、资源、设备、客户、项目、区域或业务对象关系。
- 主数据依赖：需求是否需要平台既有人员、组织、角色、权限、资源、设备、客户、项目、区域、业务对象等数据。
- 详情补全依赖：需求是否需要根据平台对象 ID 补全名称、属性、归属、状态、标签、上下文等展示字段。
- 规则策略依赖：需求是否需要读取或关联平台既有规则、策略、配置、阈值、权限范围或租户上下文。
- 状态写回依赖：需求是否需要把处理结果、回执、审批结果、执行状态等写回平台既有模块。
- 查询统计依赖：需求的历史查询、统计口径、筛选条件是否依赖平台既有字段或维表。
- 外部系统边界：需求是否只是调用外部系统；若外部调用的入参来自平台对象，也仍然存在平台依赖。

目标对象解析兜底规则：

- 只要执行动作存在“发送给谁、推送给谁、分派给谁、谁审批、谁处理、谁接收、作用到哪个资源/设备/业务对象”，就必须生成平台上下文动作或 `UNDECIDED` 确认项。
- 如果目标来自平台用户、组织、角色、权限范围、资源归属、对象负责人、订阅关系、告警策略、流程参与人或配置策略，应进入 MCP 检索。
- 如果目标是手工输入，也要确认是否需要平台校验、补全、权限过滤或联系方式查询。
- 不允许因为外部动作是定制实现，就忽略目标对象解析。

对每个需求项必须拆出两类动作：

- 执行动作：定制服务或外部系统真正要做的事情，例如发送、推送、同步、回调、保存、渲染、统计、调度。
- 平台上下文动作：为了完成执行动作，需要从平台获取、校验、监听、补全、关联或写回的对象和数据。

MCP 检索只针对“平台上下文动作”。如果一个需求项只有外部执行动作，但没有平台上下文动作，才可以不进入 MCP。

只要任一平台依赖成立，即使页面、表或服务本身是定制实现，也不能直接标记为“不调用基线组件”；应标记为“需要”或“待确认”，并进入 MCP 检索或用 `AskQuestion` 让用户确认。

只有同时满足以下条件，才可以标记为“不调用基线组件”：

- 输入完全来自用户手工录入、外部系统回调或定制库自身数据。
- 输出不需要补全、校验、关联或写回平台既有对象。
- 查询和统计不依赖平台既有维度、权限范围或状态字段。
- 不需要订阅平台事件或调用平台既有规则/配置/权限能力。

输出表格：

| 需求项 | 子能力 | 执行动作 | 平台上下文动作 | 实现方式分类 | 平台依赖类型 | 依赖对象/数据来源 | 是否进入 MCP | MCP 检索任务 | 备注 |
|---|---|---|---|---|---|---|---|---|---|

只有标记为“进入 MCP”的子能力或平台上下文动作进入 MCP 阶段。

实现方式分类要求：

- 一个需求项可以拆成多个子能力，每个子能力单独分类。
- `CUSTOM_CODE` 和 `EXTERNAL_INTEGRATION` 子能力不直接进入 MCP。
- `BASELINE_API_REUSE` 和 `HYBRID` 中的平台上下文动作进入 MCP。
- `UNDECIDED` 必须通过 `AskQuestion` 让用户确认，不能默认进入 MCP 或默认定制。
- 输出表格后必须停止，让用户确认实现方式分类和 MCP 检索任务。

MCP 检索任务生成规则：

- 一个需求项可以生成多个 MCP 检索任务，每个任务只查一个平台依赖意图。
- 检索任务必须是平台能力表达，例如“查询候选业务对象列表”“根据对象 ID 查询详情”“校验用户权限范围”“监听某类平台事件”“写回处理状态”“查询字典/规则/配置”。
- 检索任务不能是外部动作表达，例如“发送短信”“调用第三方接口”“推送消息到外部系统”“生成外部请求报文”。这些应保留为定制实现设计。
- 当执行动作需要目标对象、接收对象、操作人、负责人、所属组织、关联资源、告警/流程/任务上下文、状态或展示字段时，必须为这些数据生成单独的 MCP 检索任务。
- 当执行动作是通知、推送、发送、分派、审批、派单、授权、订阅或触达时，必须至少检查并输出一个“目标对象解析”子能力；如果确认不需要平台数据，也要在备注中说明原因。
- 如果需求分析文档已经给出“待 design-phase 检索意图”，优先使用它；但如果它仍然是外部动作表达，必须重写为平台上下文动作。

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

### 3.4 逐平台依赖检索候选 API

先把 Phase 2.5 输出的 `MCP 检索任务` 展开为检索队列：

| 检索任务编号 | 来源需求项 | 子能力 | 实现方式分类 | 平台上下文动作 | 依赖对象/数据来源 | 查询词 | 预期字段覆盖 |
|---|---|---|---|---|---|---|---|

在人工审阅模式下，检索前必须使用 `AskQuestion` 展示这张检索队列表，等待用户确认后再调用 MCP。

然后对每个检索任务单独调用：

```text
find_apis_for_requirement({
  "product_id": "<PRODUCT_ID>",
  "product_version": "<PRODUCT_VERSION>",
  "requirement_item": "<只写当前平台上下文动作、依赖对象/数据来源、查询条件、期望返回>",
  "component_overrides": { ... },
  "limit": 8
})
```

检索词要具体，包含平台对象、平台动作、输入条件、期望返回和字段覆盖。不要只写“新增/修改/删除/查询配置”这类表面 CRUD；要写清楚它依赖哪个平台对象、事件、规则、状态或权限上下文。

检索前自查：

- 查询词是否描述平台能力，而不是外部系统能力。
- 查询词是否包含要取的数据字段或状态字段。
- 查询词是否能在当前平台基线组件范围内找到合理归属。
- 如果查询词包含外部系统名称或外部动作词，先改写为平台上下文动作再查。

检索后必须输出 MCP 调用记录：

| 检索任务编号 | MCP 工具 | 请求参数摘要 | 返回候选数 | Top 候选 | 采纳状态 | 淘汰/采纳原因 |
|---|---|---|---|---|---|---|

`请求参数摘要` 至少包含 `product_id`、`product_version`、`requirement_item`、`component_overrides`、`limit`。

`采纳状态` 使用：

- `PENDING_USER_CHOICE`：候选可用，待用户选择。
- `REJECTED_SCENE_MISMATCH`：业务场景不匹配。
- `REJECTED_FIELD_GAP`：字段覆盖不足。
- `REJECTED_RISK`：版本、契约或生命周期风险不可接受。
- `NO_CANDIDATE`：没有候选。
- `NEED_KB_IMPORT`：疑似知识库缺失，需要补知识库。

不能隐藏 MCP 查询过程，也不能只输出最终结论。

### 3.5 候选过滤

候选 API 必须通过以下检查才可推荐：

- `api_identity` 存在。
- `api_contract` 存在。
- `lifecycle_status` 不是 `REMOVED`。
- 组件在 `list_product_components` 返回范围内。
- `risk` 可解释；若 risk 表示无精确文档、契约回退，必须降级置信度并展示。
- 需求字段能被请求参数或响应字段覆盖。
- API 业务场景必须满足当前“平台上下文动作”，不能只因为关键词相同就采用。比如外部通知场景不能采用只服务登录认证的一次性验证码接口，除非当前检索任务明确是认证验证码。
- 如果 Top 候选都匹配到无关场景，先判断是否查询词写成了外部动作；若是，必须回到 Phase 2.5 重写检索任务后重查，不能直接得出“本需求不需要基线 API”。
- 只有所有平台上下文检索任务都已经完成，并且无可用候选或候选被用户确认不可用，才可以说“该平台依赖暂无可复用基线 API”。

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

按检索任务通过 `AskQuestion` 输出用户可选择的表格：

| 检索任务编号 | 来源需求项 | 平台上下文动作 | 排名 | 组件/段 | API | 文档版本 | 请求字段 | 响应字段 | 风险 | 推荐级别 |
|---|---|---|---|---|---|---|---|---|---|---|

每个检索任务都要使用 `AskQuestion` 让用户确认：

- 选择某个 API
- 改为定制实现
- 以上都不合适，用户指定组件/API
- 需要先补知识库

用户确认后，将选中 API 写入设计上下文，并回填到来源需求项的具体平台依赖上。一个需求项可能同时包含“外部/定制执行动作”和多个“基线平台上下文动作”，设计时必须分别说明。

## MCP 为空或不确定时

不要编造。按顺序处理：

1. 检查平台基线是否存在。
2. 检查组件是否被现场覆盖。
3. 检查检索任务是否误用了外部执行动作或功能标题；如果是，回到 Phase 2.5 重新拆出平台上下文动作后再查。
4. 检查候选 API 是否只是关键词相似但业务场景不一致；如果是，标记为“场景不匹配”，不能作为“无基线依赖”的证据。
5. 调用 `list_component_segments` 和 `list_component_doc_versions` 看是否缺组件段或文档版本。
6. 若用户通过 `AskQuestion` 确认某组件版本应使用某文档版本，调用 `submit_component_version_doc_mapping`。
7. 若知识库缺 API，使用 `AskQuestion` 提示用户使用 `baseline-api-importer` skill 导入 Swagger，并询问是否先补知识库。

禁止输出类似结论：“因为外部动作没有匹配 API，所以本需求全部定制，不调用基线组件”。正确结论应按平台上下文动作逐项说明：哪些平台数据/事件/规则已经找到基线 API，哪些没有找到，哪些需要补知识库或用户确认。

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

后端设计必须先输出实现方式矩阵：

| 来源需求项 | 子能力 | 实现方式分类 | 本项目模块/类职责 | 是否调用基线 API | 是否调用外部系统 | 证据编号/说明 |
|---|---|---|---|---|---|---|

按实现方式分别说明：

- `BASELINE_API_REUSE`：说明调用哪个基线 API、请求映射、响应映射、fallback、错误处理和 MCP 证据编号。
- `CUSTOM_CODE`：说明定制模块、核心类/服务职责、数据表、校验规则、状态流转、错误处理和测试点。
- `EXTERNAL_INTEGRATION`：说明外部协议、认证、请求封装、超时、重试、回调/回执、降级和审计。
- `HYBRID`：分别说明定制/外部执行动作和平台上下文动作，不要混成一个“调用接口”。
- `NO_API_NEEDED`：说明为什么不需要后端或基线 API。

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

设计文档不要以 MCP 搜索结果为主体。MCP 证据只是“基线复用”的证据链；完整设计必须同时覆盖架构/中间件、实现方式分类、定制模块、外部集成、数据库、接口、异常和运维。

设计阶段输出必须保存到需求交接目录，不能保存到 `%USERPROFILE%\.claude\project`、用户 home、临时目录或当前 skill 目录：

```text
<项目根目录>/requirements/<项目名称或平台版本标识>/design-doc.md
<项目根目录>/requirements/<项目名称或平台版本标识>/design-handoff.json
<项目根目录>/requirements/<项目名称或平台版本标识>/design-validation.json
```

文档必须包含以下核心表：

### 实现方式总表

| 来源需求项 | 子能力 | 实现方式分类 | 说明 | 是否需要用户已确认 |
|---|---|---|---|---|

### MCP 检索和证据表

| 证据编号 | 来源需求项 | 平台上下文动作 | 组件 | 段 | 组件版本 | API | 文档版本 | match_level | risk |
|---|---|---|---|---|---|---|---|---|---|

### MCP 调用记录表

| 检索任务编号 | MCP 工具 | 查询词 | 候选数 | 采纳状态 | 采纳/淘汰原因 |
|---|---|---|---|---|---|

### 定制实现表

| 来源需求项 | 子能力 | 定制模块 | 主要职责 | 数据表/配置 | 异常处理 | 测试点 |
|---|---|---|---|---|---|---|

### 外部集成表

| 来源需求项 | 外部系统 | 协议 | 认证 | 请求/响应 | 超时重试 | 回调/回执 | 降级 |
|---|---|---|---|---|---|---|---|

### Design Handoff JSON

`design-handoff.json` 是后续原型、编码和自测阶段的机器可读入口。Markdown 设计文档用于人工审阅；自动化流水线必须优先读取 JSON。

必须使用以下结构；没有值时使用空数组或空对象，不要省略核心字段：

```json
{
  "schema_version": "1.0",
  "source": {
    "requirement_handoff": "requirement-handoff.json",
    "requirement_doc": "需求分析.md",
    "design_doc": "design-doc.md",
    "generated_at": "",
    "design_status": "final|draft"
  },
  "product": {
    "product_id": "",
    "product_version": "",
    "product_name_aliases": [],
    "component_overrides": {}
  },
  "architecture_decisions": [
    {
      "item": "",
      "decision": "",
      "confirmed": true,
      "rationale": "",
      "risks": []
    }
  ],
  "implementation_classification": [
    {
      "id": "IC-01",
      "from_requirement": "F-01",
      "sub_capability": "",
      "mode": "BASELINE_API_REUSE|CUSTOM_CODE|EXTERNAL_INTEGRATION|HYBRID|NO_API_NEEDED|UNDECIDED",
      "rationale": "",
      "confirmed": true
    }
  ],
  "mcp_search_plan": [
    {
      "task_id": "MCP-01",
      "from_classification": "IC-01",
      "query": "",
      "must_search": true,
      "expected_fields": []
    }
  ],
  "mcp_call_log": [
    {
      "task_id": "MCP-01",
      "tool": "find_apis_for_requirement",
      "request": {},
      "candidate_count": 0,
      "top_candidates": [],
      "decision": "PENDING_USER_CHOICE|SELECTED|REJECTED_SCENE_MISMATCH|REJECTED_FIELD_GAP|REJECTED_RISK|NO_CANDIDATE|NEED_KB_IMPORT",
      "reason": ""
    }
  ],
  "selected_baseline_apis": [
    {
      "task_id": "MCP-01",
      "component_id": "",
      "segment_id": "",
      "component_version": "",
      "method": "",
      "api_path": "",
      "doc_version": "",
      "get_api_detail_called": true,
      "risk": ""
    }
  ],
  "custom_implementation": [
    {
      "from_classification": "IC-02",
      "module": "",
      "responsibility": "",
      "tables_or_config": [],
      "error_handling": [],
      "test_points": []
    }
  ],
  "external_integrations": [
    {
      "from_classification": "IC-03",
      "system": "",
      "protocol": "",
      "auth": "",
      "request_response": "",
      "timeout_retry": "",
      "callback_or_receipt": "",
      "fallback": ""
    }
  ],
  "open_risks": []
}
```

生成规则：

- `implementation_classification` 必须覆盖每个需求项拆出的每个子能力；不要只覆盖需要查 MCP 的能力。
- `CUSTOM_CODE`、`EXTERNAL_INTEGRATION`、`HYBRID` 必须分别在 `custom_implementation` 或 `external_integrations` 中有设计说明；不能让 MCP 搜索结果替代定制代码设计。
- `BASELINE_API_REUSE` 和 `HYBRID` 的平台上下文动作必须进入 `mcp_search_plan`，并在 `mcp_call_log` 中留下实际调用记录。
- 选中的基线 API 必须写入 `selected_baseline_apis`，且 `get_api_detail_called` 必须为 `true`。
- 最终版 `design_status` 使用 `final`，草稿使用 `draft`。最终版中不能出现 `UNDECIDED`、`待确认` 或 `[待确认]`。

生成后必须运行校验脚本：

```text
python .claude/skills/design-phase/scripts/validate_design.py --handoff <交接目录>/design-handoff.json --output <交接目录>/design-validation.json --project-root <项目根目录>
```

校验失败时，读取 `design-validation.json` 的 `errors`，修复设计文档和 JSON 后重新运行。不能在校验失败时声明方案设计完成，也不能进入原型、编码或自测阶段。

完成前检查：

- 已执行 Phase 0，优先读取 `requirement-handoff.json`；如果没有 JSON，读取 `design-phase-handoff.md` 或明确说明替代来源。
- 已创建并持续更新 `design-phase-state.md`。
- 已生成 `design-doc.md`、`design-handoff.json` 和 `design-validation.json`，且都位于当前项目目录的 `requirements/<项目名称或平台版本标识>/` 下。
- 已运行 `scripts/validate_design.py`，且 `design-validation.json` 中 `success` 为 `true`。
- 平台和版本已确认。
- 架构和中间件已经通过 `AskQuestion` 确认，或用户明确要求全自动。
- 已调用 `list_products` 校验平台存在。
- 已调用 `list_product_components` 确认组件范围。
- 已把每个需求项拆成执行动作和平台上下文动作。
- 已为每个子能力标注实现方式分类。
- 每个平台上下文动作都生成了明确的 MCP 检索任务。
- 每个 MCP 检索任务都调用了 `find_apis_for_requirement`。
- 每个最终 API 都调用了 `get_api_detail`。
- MCP 调用记录、候选、采纳/淘汰原因已经写入文档。
- `CUSTOM_CODE`、`EXTERNAL_INTEGRATION`、`HYBRID` 子能力都有非 MCP 的设计说明。
- 没有用外部动作或功能标题直接作为 MCP 查询词。
- 没有因为外部动作查不到 API 就判定整个需求不需要基线组件。
- 所有风险都展示给用户并被确认。
- 没有使用旧版搜索类或候选提交类 MCP 工具。
- 没有编造组件/API。

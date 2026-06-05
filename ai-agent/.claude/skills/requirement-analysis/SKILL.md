---
name: requirement-analysis
description: >
  当用户提供需求描述、需求文档、ticket URL，或要求“需求分析”“需求拆解”“整理需求”“生成需求文档”时必须使用。
  本 skill 是方案设计前的入口阶段：提取平台和版本，拆解功能项，澄清模糊点，识别平台依赖和数据来源，
  并把确认后的需求分析文档保存到当前项目目录下。
---

# 需求分析

本 skill 用于把自然语言需求、ticket 页面或粘贴的需求文档转成可确认、可交接给 design-phase 的需求分析文档。

需求分析只做“问题、范围、功能、数据来源、验收和澄清”的确认，不做 UI 设计、API 选型、数据库设计或代码生成；这些属于后续 design-phase。

## 全局原则

- `product_id` / 平台名称 和 `product_version` / 平台版本是强制项。缺失时先用 `AskQuestion` 询问，不能继续分析。
- 直连人工模式下，所有和用户交互的动作都必须使用 `AskQuestion`，包括缺信息、澄清、阶段确认、输出路径确认和进入下一阶段确认。
- 如果输入中明确包含 `worker_mode: true`，进入 orchestrator worker 模式：不能直接使用 `AskQuestion`，需要人工确认时必须写 `pending-questions.json` 和 `worker-result.json(status=NEED_USER_INPUT)` 后停止，由主流程负责询问用户。
- 不要把功能项只按页面或 CRUD 拆解；必须同时分析触发来源、输入来源、输出去向、数据对象、状态流转、异常场景和平台依赖。
- 不要把“定制实现”等同于“不依赖平台”。只要需求需要读取、写入、订阅、校验、展示、关联或补全平台既有对象、事件、规则、状态、权限或配置，就必须记录为平台依赖。
- 对通知、推送、发送、分派、审批、抄送、派单、升级、授权、订阅、触达等动作，必须识别“目标对象解析”问题：作用到谁/什么对象、目标从哪里来、如何过滤、如何取得联系方式或标识。原文没写时也要标记为 `推断/待确认`，不能默认由定制代码自行解决。
- 需求文档必须保存到当前项目目录下，不能保存到 `%USERPROFILE%\.claude\project`、用户 home、临时目录或当前 skill 目录。
- 不要把未确认的推断写成确定结论。所有结论必须标注来源：原文明确、用户澄清、合理推断、待确认。
- 最终版需求分析文档中不能残留 `[待确认]`。若仍有关键待确认项，只能输出“需求分析草稿”并继续 `AskQuestion`，不能声明完成。

## Orchestrator Worker 模式

当 prompt、`workflow-state.json` 或用户明确指令包含 `worker_mode: true` 时，按 worker 模式执行。本模式用于让主 Claude Code session 保持干净，由隔离 worker 负责阶段执行。

worker 模式规则：

- 先读取 `workflow-state.json`、`decisions.jsonl` 和已有输入材料。
- 不要直接向用户提问，不要调用 `AskQuestion`。
- 遇到缺少平台名称/版本、关键澄清点、输出路径确认、是否进入下一阶段等人工确认点时，写 `pending-questions.json`，再写 `worker-result.json`，状态为 `NEED_USER_INPUT`，然后停止。
- 如果 `decisions.jsonl` 已经包含对应 `question_id` 的用户决策，使用该决策继续执行，并把证据级别标为 `澄清`。
- 每个问题必须有稳定 `id`；同一个问题重试时复用同一个 `id`，方便主流程去重和续跑。
- 阶段完成时写 `worker-result.json(status=STAGE_COMPLETED)`，包含 `artifact_dir`、`handoff`、`validation` 和简短 `summary`。
- 校验失败时先判断错误类型：如果涉及 `[待确认]`、`待确认`、`open_questions`、目标对象来源未确认、产品/版本缺失或任何需要用户确认的新事实，禁止自行替换为确定结论，必须写 `pending-questions.json` 和 `worker-result.json(status=NEED_USER_INPUT)` 后停止。
- 只有纯文档结构、验收标准数量不足、字段遗漏但不需要新业务事实的问题，才允许 worker 基于已知需求自行补充并重新运行 validator；仍失败则写 `worker-result.json(status=VALIDATION_FAILED)`。
- worker 模式下不要询问“是否继续进入 design-phase”。需求分析完成且 `requirement-validation.json.success=true` 时，直接写 `worker-result.json(status=STAGE_COMPLETED)`，由 orchestrator 自动流转。

`pending-questions.json` 格式：

```json
{
  "status": "NEED_USER_INPUT",
  "stage": "requirement-analysis",
  "phase": "Phase 4 模糊点澄清",
  "question_batch_id": "RQ-0001",
  "questions": [
    {
      "id": "requirement.target_source.F-01",
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
  "stage": "requirement-analysis",
  "phase": "",
  "artifact_dir": "",
  "handoff": "",
  "validation": "",
  "pending_questions": "",
  "summary": "",
  "next_action": ""
}
```

## 证据和推断规则

需求分析要区分“用户说了什么”和“AI 推断了什么”。

对每个功能项、约束、非功能需求和平台依赖，都标注证据级别：

- `明确`: 原文或 ticket 中直接写明。
- `澄清`: 用户通过 `AskQuestion` 明确确认。
- `推断`: 根据上下文合理推断，但尚未被用户确认。
- `待确认`: 对范围、数据来源、规则或实现影响较大的关键未知项。

处理规则：

- `明确` 和 `澄清` 可以写入最终结论。
- `推断` 必须给出推断理由，并在澄清阶段让用户确认；确认前不能当作最终范围。
- `待确认` 不能留到最终文档里。若用户暂时无法确认，应在文档状态中标记为“草稿”，并禁止交接 design-phase。
- 不要为了显得完整而新增原文没有依据的功能。可以作为“建议补充能力”列出，但必须标注为 `推断/待确认`。

## 输出目录规则

生成文档前必须先确定项目根目录：

1. 优先使用 Claude Code 当前工作目录。
2. 如果当前目录是仓库子目录且 `git rev-parse --show-toplevel` 可用，则使用 git 根目录。
3. 如果不是 git 仓库，则使用当前工作目录。

文档输出路径固定为：

```text
<项目根目录>/requirements/<项目名称或平台版本标识>/需求分析.md
```

同时必须生成 design-phase 交接文件：

```text
<项目根目录>/requirements/<项目名称或平台版本标识>/design-phase-handoff.md
```

同时必须生成机器可读交接文件和校验结果：

```text
<项目根目录>/requirements/<项目名称或平台版本标识>/requirement-handoff.json
<项目根目录>/requirements/<项目名称或平台版本标识>/requirement-validation.json
```

如果仍有关键澄清点未解决，只能输出草稿：

```text
<项目根目录>/requirements/<项目名称或平台版本标识>/需求分析-草稿.md
```

路径生成规则：

- `<项目名称或平台版本标识>` 优先使用 `product_id-product_version`，例如 `PVIA-2.4.0`。
- 如果只有平台名称，则使用平台名称；空格和路径非法字符替换为 `-`。
- 写文件前创建目录。
- 最终回复必须给出保存后的绝对路径，并明确文档状态是“最终版”还是“草稿”。

写文件步骤：

1. 先确认或探测项目根目录，记录为绝对路径。
2. 创建 `<项目根目录>/requirements/<项目名称或平台版本标识>/`。
3. 如果关键澄清点已全部解决，把完整 Markdown 文档写入 `需求分析.md`。
4. 如果仍有关键澄清点未解决，只能写入 `需求分析-草稿.md`。
5. 生成 `design-phase-handoff.md`，作为后续设计阶段的唯一入口上下文。
6. 生成 `requirement-handoff.json`，作为后续 design-phase 的机器可读唯一事实来源。
7. 运行 `scripts/validate_requirement.py` 生成 `requirement-validation.json`；校验失败时不能交接 design-phase。
8. 写入后重新读取上述文件，确认内容不是空文件、不是摘要占位符，并且包含“功能项清单”“平台依赖和数据来源”“澄清记录”“交接给 design-phase 的上下文”。
9. 如果文件未成功写入，不能声明完成。

## Design-phase 交接文件

`design-phase-handoff.md` 用于解决同一个 Claude Code session 中上下文过长、阶段规则互相干扰、步骤丢失的问题。后续 design-phase 必须优先读取该文件，而不是依赖聊天历史。

交接文件必须使用以下结构：

```markdown
# Design-phase Handoff

## Source
- requirement_doc:
- requirement_status: 最终版 / 草稿
- generated_at:

## Product
- product_id:
- product_version:
- product_name_aliases:
- component_overrides:

## Confirmed Scope
- 已确认功能范围:
- 明确不做范围:
- 已确认非功能要求:

## Requirement Items
| 功能项 | 优先级 | 证据级别 | 摘要 | 关键业务规则 | 关键数据规则 |
|---|---|---|---|---|---|

## Platform Dependency Tasks
| task_id | 来源功能项 | 依赖类型 | 目标对象/数据来源 | design-phase 检索意图 | 证据级别 | 是否关键 |
|---|---|---|---|---|---|---|

## Target Object Resolution
| 来源功能项 | 动作 | 目标对象 | 目标来源 | 联系方式/标识来源 | 权限/过滤规则 | 状态 |
|---|---|---|---|---|---|---|

## Open Risks For Design
| risk_id | 风险 | 影响 | 建议处理 |
|---|---|---|---|

## Phase Entry Instruction
从新 session 或当前 session 进入 design-phase 时，先读取本文件和 requirement_doc。不要依赖之前聊天历史。按 design-phase 的 Phase 1 开始，并创建 design-phase-state.md。
```

如果需求仍是草稿，交接文件必须明确 `requirement_status: 草稿`，并列出未解决关键问题；design-phase 只能做预研或草案，不能输出最终设计。

## Requirement Handoff JSON

`requirement-handoff.json` 是后续 design-phase 的机器可读入口。Markdown 可以用于人工阅读，但阶段衔接、校验和全自动流水线必须优先读取 JSON。

必须使用以下结构；没有值时使用空数组或空对象，不要省略核心字段：

```json
{
  "schema_version": "1.0",
  "source": {
    "requirement_doc": "需求分析.md",
    "requirement_status": "final|draft",
    "generated_at": "",
    "source_type": "ticket|manual|document",
    "source_ref": ""
  },
  "product": {
    "product_id": "",
    "product_version": "",
    "product_name_aliases": [],
    "component_overrides": {}
  },
  "requirement_items": [
    {
      "id": "F-01",
      "title": "",
      "priority": "P0|P1|P2",
      "evidence_level": "明确|澄清|推断|待确认",
      "summary": "",
      "original_basis": "",
      "business_rules": [],
      "data_rules": [],
      "permission_rules": [],
      "state_flow": [],
      "exceptions_or_boundaries": [],
      "acceptance_criteria": [],
      "platform_dependency_summary": ""
    }
  ],
  "platform_dependency_tasks": [
    {
      "task_id": "PDT-01",
      "from_requirement": "F-01",
      "dependency_type": "目标对象解析|触发依赖|主数据依赖|详情补全依赖|规则策略依赖|状态写回依赖|查询统计依赖|外部系统边界",
      "target_object_or_data_source": "",
      "design_search_intent": "",
      "evidence_level": "明确|澄清|推断|待确认",
      "critical": true
    }
  ],
  "target_object_resolution": [
    {
      "from_requirement": "F-01",
      "action": "",
      "target_object": "",
      "target_source": "",
      "contact_or_identifier_source": "",
      "permission_or_filter_rule": "",
      "status": "confirmed|inferred|open"
    }
  ],
  "open_questions": [],
  "open_risks_for_design": []
}
```

生成规则：

- `requirement_items` 必须覆盖需求分析 Markdown 中的所有功能项。
- `platform_dependency_tasks` 只写 design-phase 需要检索、确认或设计的平台上下文依赖，不写外部系统执行动作本身。
- 通知、推送、发送、分派、审批、派单、触达等动作必须至少生成一条 `target_object_resolution`。如果目标对象来源未确认，状态写 `open`，并把问题放入 `open_questions`；最终版不能保留 `open`。
- `design_search_intent` 必须写成平台能力意图，例如“根据告警 ID 查询告警详情和关联接收人规则”，不要写“发送短信”这种外部动作。
- 最终版 `requirement_status` 使用 `final`，草稿使用 `draft`。最终版中不能出现 `待确认` 或 `[待确认]`。

生成后必须运行校验脚本：

```text
python .claude/skills/requirement-analysis/scripts/validate_requirement.py --handoff <交接目录>/requirement-handoff.json --output <交接目录>/requirement-validation.json --project-root <项目根目录>
```

校验失败时，读取 `requirement-validation.json` 的 `errors` 后先分类处理：

- 如果错误涉及 `[待确认]`、`待确认`、`open_questions`、目标对象来源未确认、产品/版本缺失或任何需要用户确认的新事实，不能擅自替换或删除这些字段；必须回到澄清阶段。worker 模式下写 `pending-questions.json` 并停止，直连人工模式下使用 `AskQuestion`。
- 如果错误只是验收标准数量不足、章节缺失、字段漏写等不需要新增业务事实的问题，可以基于已知事实补充后重新运行 validator。

不能在校验失败时声明需求分析完成，也不能进入 design-phase。

## 输入模式

### Mode A：Ticket URL

当用户提供 ticket URL 时，按级联策略抓取，不要一开始就要求用户手动粘贴。

1. 先尝试轻量抓取，例如 WebFetch 或可用的页面提取工具。
2. 如果轻量抓取失败、跳转 SSO、403、超时或内容为空，自动切换到 Playwright MCP 或浏览器抓取，不要询问是否切换。
3. 如果需要 SSO 登录：
   - 已配置账号密码时按配置自动登录。
   - 未配置密码时，用 `AskQuestion` 告知用户在浏览器中完成登录；不要让用户把密码贴到对话中。
4. 抓取完成后提取需求标题、正文、附件线索、平台名称、平台版本和原始文本。

### Mode B：手动输入或文档粘贴

当用户直接粘贴需求文档、文本或附件内容时，从文本中提取：

- 平台名称 / `product_id`
- 平台版本 / `product_version`
- 需求背景
- 角色 / 参与者
- 功能项和验收标准
- 约束、依赖、边界
- 澄清记录

如果平台名称或版本缺失，先用 `AskQuestion` 阻塞确认。

## 工作流

一次只推进一个阶段。直连人工模式下，每个需要用户确认的阶段都用 `AskQuestion`，收到回复后再继续。worker 模式下，每个确认点都写入 `pending-questions.json`，由 orchestrator 主流程询问用户并把回答写入 `decisions.jsonl`。

### Phase 1：提取和归一化

提取并保留：

- 来源：ticket URL、文档名、用户粘贴文本或附件路径。
- 原始需求文本：保留关键原文，便于追溯。
- 平台名称 / `product_id`。
- 平台版本 / `product_version`。
- 需求标题。
- 需求背景和目标。
- 角色、参与者、外部系统。
- 已有澄清结论。

如果同一信息存在多个叫法，建立映射。例如 `PV 2.4.0`、`PVIA 2.4.0`、`PVIA平台` 的关系需要记录为“待确认”或“已确认映射”。

### Phase 2：功能拆解

把需求拆成离散功能项，编号为 `F-01`、`F-02`。

每个功能项必须输出：

```text
### F-<NN>: <功能名称>

- 描述:
- 证据级别: 明确 / 澄清 / 推断 / 待确认
- 原文依据:
- 触发条件:
- 输入:
- 输出:
- 前置条件:
- 后置条件:
- 涉及角色:
- 优先级: P0 / P1 / P2
- 业务规则:
- 数据规则:
- 权限规则:
- 状态流转:
- 异常和边界:
- 审计/日志:
- 平台依赖摘要:
- 验收标准:
  1. Given <前置条件>, when <操作>, then <预期结果>
```

拆解要求：

- 一个功能项只表达一个可实现、可验收的能力。
- 不要把“管理 XX”停留在粗粒度描述；应拆出新增、编辑、删除、查询、生效规则、权限、异常、审计等真实能力。
- 对集成类需求，拆出协议适配、认证、消息封装、失败处理、回调/回执、日志和监控。
- 对自动触发类需求，拆出触发事件、触发条件、幂等、重试、失败兜底和人工补偿。
- 对通知/推送/分派/审批/派单类需求，拆出目标对象解析：目标角色/人员/组织/资源、选择规则、过滤条件、联系方式或账号标识来源、权限范围和无目标对象时的处理。
- 对配置类需求，拆出配置项、校验、加密/脱敏、动态生效、连接测试和变更记录。
- 对查询统计类需求，拆出筛选条件、分页排序、展示字段、权限范围、统计口径、导出、空结果和大数据量表现。
- 对模板/规则/策略类需求，拆出变量来源、适用范围、冲突处理、启停规则、版本/变更生效和预览校验。

细化深度标准：

- 每个 P0 功能项至少包含 5 条验收标准，覆盖正常路径、权限/配置、失败/异常、边界条件、数据落库或状态变化。
- 每个 P1 功能项至少包含 4 条验收标准。
- 每个功能项的“输入/输出”不能只写业务名词，必须列出关键字段或字段类别。
- 每个功能项的“异常和边界”不能留空；至少覆盖一种失败场景和一种边界场景。
- 若某功能项无法写出业务规则、数据规则和异常边界，说明拆解不够细或信息缺失，应回到澄清阶段。
- 如果一个功能项同时包含“配置、触发、执行、记录、查询、回调、统计”等多个责任，应拆成多个功能项或子能力，不要塞在一个标题下。

### Phase 3：平台依赖和数据来源分析

这一阶段为 design-phase 的基线组件检索做准备。不要等到设计阶段才发现数据来源缺失。

对每个功能项检查以下依赖类型：

- 触发依赖：是否由平台既有事件、流程、任务、状态变化或业务动作触发。
- 目标对象解析依赖：通知、推送、发送、分派、审批、派单、授权等动作的目标对象是否来自平台既有人员、组织、角色、资源、设备、客户、项目、区域或业务对象关系。
- 主数据依赖：是否需要平台既有人员、组织、角色、权限、资源、设备、客户、项目、区域、业务对象等数据。
- 详情补全依赖：是否需要根据平台对象 ID 补全名称、属性、归属、状态、标签或上下文。
- 规则策略依赖：是否需要读取或关联平台既有规则、策略、配置、阈值、权限范围或租户上下文。
- 状态写回依赖：是否需要把处理结果、回执、审批结果、执行状态等写回平台既有模块。
- 查询统计依赖：历史查询、统计口径、筛选条件是否依赖平台既有字段、维表或权限范围。
- 外部系统边界：如果功能只是调用外部系统，也要判断外部调用的入参是否来自平台对象。

目标对象解析检查：

- 需求出现“通知、推送、发送、分派、审批、抄送、派单、升级、授权、订阅、触达、负责人、接收方、处理人、审核人、参与人、联系人”等语义时，必须检查目标对象来源。
- 如果目标对象来自平台用户、组织、角色、权限范围、资源归属、告警对象、业务对象关系或配置策略，平台依赖应标记为“是”或“待确认”。
- 如果目标对象由用户手工输入或外部系统回调提供，也要确认是否需要用平台数据校验、补全、展示或权限过滤。
- 原文没有说明目标对象来源时，不能标记为“否”；应记录 `[待确认]`，并在 `待 design-phase 检索意图` 中写明需要检索/确认的目标解析能力。

输出表格：

| 功能项 | 显式功能 | 平台依赖类型 | 依赖对象/数据来源 | 证据级别 | 是否可能调用基线组件 | 待 design-phase 检索意图 | 备注 |
|---|---|---|---|---|---|---|---|

判断规则：

- 只要任一平台依赖成立，就标记“是”或“待确认”，不能直接标记“否”。
- 只有输入完全来自用户手工录入、外部系统回调或定制库自身数据，且输出不需要补全/校验/关联/写回平台对象，才可标记“否”。
- 数据来源不明确时，不要猜成“否”；标记为 `[待确认]`。
- 不要把所有功能项机械标记为“是”。必须说明调用基线的具体原因：要取什么数据、监听什么事件、校验什么规则、写回什么状态。
- `待 design-phase 检索意图` 应写成能力意图和数据意图，不要提前编造组件名。例如“根据告警 ID 查询告警详情和关联对象字段”，优于“检索告警组件”。

### Phase 4：模糊点澄清

这是硬门禁。不能带着未解决的关键模糊点生成最终文档。

澄清点至少覆盖：

- 平台名称和版本是否明确。
- 角色和权限边界。
- 功能范围和不做范围。
- 触发条件和失败处理。
- 数据来源、对象归属和平台依赖。
- 目标对象来源：通知/推送/发送/分派/审批等动作的目标从哪里来，是否需要从平台用户、组织、角色、资源归属或业务关系中解析。
- 外部系统协议、认证、回调和异常。
- 性能、可靠性、安全、审计、动态生效等非功能需求。
- 历史查询、统计口径、状态枚举和数据保留周期。

规则：

- 每个模糊点标记为 `[待确认]`，给出推荐答案和推荐理由。
- 使用 `AskQuestion` 分批提问，每批最多 4 个问题。
- 用户回答后，把结论写入“澄清记录”和对应功能项。
- 如果没有找到任何 `[待确认]`，重新检查范围边界、错误处理、权限规则、边界情况、数据规模、集成失败模式和数据来源；真实需求通常至少有 2-3 个需要确认的点。
- 未解决的关键澄清点数量必须为 0，才能进入最终文档生成。

关键澄清点定义：

- 会改变功能范围、功能项拆分或优先级。
- 会改变数据模型、数据来源、平台依赖或 design-phase MCP 检索意图。
- 会改变外部系统协议、认证、回调、重试、异常处理。
- 会改变权限、安全、审计、性能、数据保留或统计口径。

如果关键澄清点未解决：

- 不要写最终版 `需求分析.md`。
- 可以写 `需求分析-草稿.md`，并在文档信息中标注“状态: 草稿，存在未解决关键澄清点”。
- 最终回复只说明草稿路径和待确认问题，不允许说“需求分析完成”。

### Phase 5：生成需求分析文档

文档必须使用以下结构：

```markdown
# <平台/项目> <版本> <需求标题> — 需求分析

## 1. 文档信息
- 来源:
- 分析时间:
- 状态: 最终版 / 草稿
- 平台:
- 版本:
- 输出路径:

## 2. 原始需求摘要

## 3. 需求背景和目标

## 4. 角色和参与者

| 角色 | 说明 | 权限/关注点 |
|---|---|---|

## 5. 功能项清单

使用 Phase 2 的完整功能项模板输出每个功能项，不能只写描述、输入、输出和验收标准。

## 6. 平台依赖和数据来源

| 功能项 | 显式功能 | 平台依赖类型 | 依赖对象/数据来源 | 证据级别 | 是否可能调用基线组件 | 待 design-phase 检索意图 | 备注 |
|---|---|---|---|---|---|---|---|

## 7. 非功能需求

## 8. 约束、依赖和边界

## 9. 澄清记录

| # | 问题 | 推荐答案 | 用户结论 | 证据级别 | 影响范围 |
|---|---|---|---|---|---|

## 10. 交接给 design-phase 的上下文

- product_id:
- product_version:
- component_overrides:
- 需要重点检索的基线能力:
- 不需要检索基线的定制功能:
- 仍需设计阶段确认的风险:
- design-phase-handoff:
```

## 完成检查

声明完成前逐项检查：

- [ ] 平台名称 / `product_id` 已确认。
- [ ] 平台版本 / `product_version` 已确认。
- [ ] 原始需求文本或摘要已保留。
- [ ] 功能项已拆解并带 Given/When/Then 验收标准。
- [ ] P0/P1 功能项满足细化深度标准。
- [ ] 每个功能项都包含业务规则、数据规则、权限规则、状态流转、异常和边界。
- [ ] 每个功能项都做了平台依赖和数据来源分析。
- [ ] 所有关键 `[待确认]` 已通过 `AskQuestion` 解决，最终文档中没有残留 `[待确认]`。
- [ ] 文档已写入当前项目目录下的 `requirements/<项目名称或平台版本标识>/需求分析.md`。
- [ ] `design-phase-handoff.md` 已生成，且包含 Product、Requirement Items、Platform Dependency Tasks、Target Object Resolution。
- [ ] `requirement-handoff.json` 已生成，且覆盖所有功能项、平台依赖任务和目标对象解析。
- [ ] 已运行 `scripts/validate_requirement.py`，并生成 `requirement-validation.json`。
- [ ] `requirement-validation.json` 中 `success` 为 `true`；如果为 `false`，已修复所有 `errors` 后重新校验。
- [ ] 最终回复给出了文档绝对路径。

有任何一项未完成，不要宣称需求分析完成。

## 常见错误

- 不要把文档写到 `%USERPROFILE%\.claude\project`。
- 不要把“没有明确写数据来源”当成“不依赖平台”。
- 不要把功能项写得过粗，例如只写“配置管理”“记录管理”“对接适配”。
- 不要把未确认的建议功能写成已确认范围。
- 不要在最终版文档中保留 `[待确认]`。
- 不要跳过澄清阶段直接生成最终文档。
- 不要在需求分析阶段设计 API、DDL 或 UI 细节。

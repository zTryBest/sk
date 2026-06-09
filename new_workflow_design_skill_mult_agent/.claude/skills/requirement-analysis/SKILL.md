---
name: requirement-analysis
description: >
  当 RequirementAgent 需要把用户项目描述、ticket URL、需求文档或人工补充内容整理成需求分析产物时使用。
  本 Skill 只负责需求分析方法论：范围识别、功能拆解、平台依赖、数据来源、验收标准、open_questions 和
  `artifacts/01_requirement.json` 输出；不负责流程调度、方案设计、原型、编码或测试。
---

# 需求分析 Skill

本 Skill 说明"需求分析怎么做"。谁来调用、是否暂停、Human Gate 如何确认、下一阶段何时开始，由 Orchestrator 和 `.claude/agents/requirement-agent.md` 决定。

## 阶段边界

应该做：
- 提取项目名称、业务目标、用户角色、功能需求、非功能需求、约束、验收标准和风险。
- 识别不明确的信息，形成 `open_questions`，交给 Orchestrator 的 Human Gate。
- 输出 `artifacts/01_requirement.json`。
- 只分析"要做什么"和"为什么做"，不提前决定"怎么实现"。

禁止做：
- 不写代码。
- 不做技术方案、数据库设计、接口设计或 UI 原型。
- 不选择 baseline API。
- 不修改后续阶段产物。
- 不写 `.ai-dev/` 下的流程控制文件。

## 输入

可以提供以下任意输入：
- 用户项目描述。
- ticket URL。
- 需求文档路径或文档正文。
- Human Gate 确认后的补充意见（REVISE 重新调度时）。

URL 或需登录页面按 `references/input-fetching.md` 抓取。无法抓取时输出 draft + open_questions。

## 执行流程

严格按以下顺序执行，每一步的详细规则见对应 reference 文件。

### Step 1: 提取基础信息

提取并保留证据来源：
- `project_name`、`business_goal`
- `source_type`、`source_ref`
- `product_id`、`product_version`
- 原始需求摘要
- 参与角色和外部系统
- 明确不做范围

`product_id` 和 `product_version` 缺失时只能输出 draft。

### Step 2: 拆解功能需求

**严格按 `references/analysis-rules.md` 中的功能项模板和拆解深度标准执行。**

把需求拆成稳定编号的功能项（F-01、F-02...），每个功能项包含：
- 标题、摘要、优先级、证据级别
- 触发条件、输入、输出
- 业务规则、数据规则、权限规则
- 状态流转、异常和边界
- Given/When/Then 验收标准

拆解深度：
- P0 至少 5 条验收标准。
- P1 至少 4 条验收标准。
- 异常和边界不能留空。

### Step 3: 平台依赖和数据来源分析

**严格按 `references/analysis-rules.md` Phase 3 的平台依赖类型和目标对象解析规则执行。**

每个功能项检查 8 类平台依赖：
- 触发依赖、目标对象解析依赖、主数据依赖、详情补全依赖
- 规则策略依赖、状态写回依赖、查询统计依赖、外部系统边界

输出依赖分析表。数据来源不明确时标记 `[待确认]`，不猜成"否"。

### Step 4: 形成 open_questions

**严格按 `references/analysis-rules.md` Phase 4 澄清门禁执行。**

关键规则：
- **一个 OQ 只问一个独立问题，不合并多个问题。**
- **推荐选项必须是具体可采纳的值（如版本号、接口路径），不允许概括性描述。**
- 每个 OQ 提供 2-3 个具体可选项。
- 关键澄清点未解决时设置 `status=draft`。
- 每批最多 4 个问题。

### Step 5: 输出 artifact

**严格按 `references/output-contracts.md` 的 JSON Schema 和写入规则执行。**

输出 `artifacts/01_requirement.json`，使用 Write 工具直接写入，写入后用 Read 工具读回验证格式正确。不要通过 Bash/Python 写入或校验。

## 完成标准

只有满足以下条件才能标为 `final`：
- 项目名称、业务目标、产品标识和版本已确认。
- 功能需求已拆解并具备验收标准。
- 每个功能项都有平台依赖和数据来源分析。
- 无关键 `open_questions`。
- `artifacts/01_requirement.json` 已写入并可被 JSON 解析。

否则输出 `draft`。

# Output Contracts

## 输出目录

先确定项目根目录：

1. 优先使用 Claude Code 当前工作目录。
2. 如果当前目录是仓库子目录且 `git rev-parse --show-toplevel` 可用，则使用 git 根目录。
3. 如果不是 git 仓库，则使用当前工作目录。

文档输出路径：

```text
<项目根目录>/requirements/<项目名称或平台版本标识>/需求分析.md
```

草稿路径：

```text
<项目根目录>/requirements/<项目名称或平台版本标识>/需求分析-草稿.md
```

交接和校验文件：

```text
<项目根目录>/requirements/<项目名称或平台版本标识>/design-phase-handoff.md
<项目根目录>/requirements/<项目名称或平台版本标识>/requirement-handoff.json
<项目根目录>/requirements/<项目名称或平台版本标识>/requirement-validation.json
```

`<项目名称或平台版本标识>` 优先使用 `product_id-product_version`，例如 `PVIA-2.4.0`。空格和路径非法字符替换为 `-`。

## 写文件步骤

1. 确认或探测项目根目录，记录为绝对路径。
2. 创建 `requirements/<项目名称或平台版本标识>/`。
3. 关键澄清点已全部解决时写 `需求分析.md`。
4. 仍有关键澄清点时只能写 `需求分析-草稿.md`。
5. 生成 `design-phase-handoff.md`，作为后续设计阶段的人类可读入口。
6. 生成 `requirement-handoff.json`，作为后续 design-phase 的机器可读唯一事实来源。
7. 生成或运行 validator 得到 `requirement-validation.json`；校验失败不能交接 design-phase。
8. 写入后重新读取文件，确认内容不是空文件、不是摘要占位符，并包含“功能项清单”“平台依赖和数据来源”“澄清记录”“交接给 design-phase 的上下文”。

## 需求分析文档模板

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

使用 Phase 2 的完整功能项模板输出每个功能项。

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

## design-phase-handoff.md

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

如果需求仍是草稿，交接文件必须明确 `requirement_status: 草稿`，并列出未解决关键问题。

## requirement-handoff.json

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

- `requirement_items` 必须覆盖 Markdown 中的所有功能项。
- `platform_dependency_tasks` 只写 design-phase 需要检索、确认或设计的平台上下文依赖。
- 通知、推送、发送、分派、审批、派单、触达等动作必须至少生成一条 `target_object_resolution`。最终版不能保留 `open`。
- `design_search_intent` 写成平台能力意图，不写外部执行动作。
- 最终版 `requirement_status=final`，草稿为 `draft`。

## Validator

期望校验命令：

```text
python .claude/skills/requirement-analysis/scripts/validate_requirement.py --handoff <交接目录>/requirement-handoff.json --output <交接目录>/requirement-validation.json --project-root <项目根目录>
```

如果当前安装中没有 validator 脚本，不能假装已运行；应在 `requirement-validation.json` 或最终汇报中明确说明缺少校验脚本，并将阶段标记为不可交接或 `BLOCKED`，除非 orchestrator 提供了等价 validator。

校验失败时：

- 涉及待确认、新事实、open questions、目标对象来源、产品/版本缺失时，回到澄清阶段。
- 章节缺失、验收标准数量不足、字段漏写等不需要新事实的问题，可以基于已知事实补充后重跑。

## 完成检查

- [ ] 平台名称 / `product_id` 已确认。
- [ ] 平台版本 / `product_version` 已确认。
- [ ] 原始需求文本或摘要已保留。
- [ ] 功能项已拆解并带 Given/When/Then 验收标准。
- [ ] P0/P1 功能项满足细化深度标准。
- [ ] 每个功能项都包含业务规则、数据规则、权限规则、状态流转、异常和边界。
- [ ] 每个功能项都做了平台依赖和数据来源分析。
- [ ] 所有关键 `[待确认]` 已解决，最终文档中没有残留。
- [ ] 文档写入当前项目目录下的 `requirements/<项目名称或平台版本标识>/需求分析.md`。
- [ ] `design-phase-handoff.md` 已生成。
- [ ] `requirement-handoff.json` 已生成。
- [ ] `requirement-validation.json.success=true`。
- [ ] 最终回复给出文档绝对路径。

## 常见错误

- 不要把文档写到 `%USERPROFILE%\.claude\project`。
- 不要把“没有明确写数据来源”当成“不依赖平台”。
- 不要把功能项写得过粗，例如只写“配置管理”“记录管理”“对接适配”。
- 不要把未确认的建议功能写成已确认范围。
- 不要在最终版文档中保留 `[待确认]`。
- 不要跳过澄清阶段直接生成最终文档。
- 不要在需求分析阶段设计 API、DDL 或 UI 细节。

---
name: requirement-analysis
description: >
  当 RequirementAgent 需要把用户项目描述、ticket URL、需求文档或人工补充内容整理成需求分析产物时使用。
  本 Skill 只负责需求分析方法论：范围识别、功能拆解、平台依赖、数据来源、验收标准、open_questions 和
  `artifacts/01_requirement.json` 输出；不负责流程调度、方案设计、原型、编码或测试。
---

# 需求分析 Skill

本 Skill 说明“需求分析怎么做”。谁来调用、是否暂停、Human Gate 如何确认、下一阶段何时开始，由 `/project-run` 和 RequirementAgent 决定。

## 阶段边界

应该做：
- 提取项目名称、业务目标、用户角色、功能需求、非功能需求、约束、验收标准和风险。
- 识别不明确的信息，形成 `open_questions`，交给 RequirementAgent 返回 Human Gate。
- 输出 `artifacts/01_requirement.json`，必要时补充人类可读说明。
- 只分析“要做什么”和“为什么做”，不提前决定“怎么实现”。

禁止做：
- 不写代码。
- 不做技术方案、数据库设计、接口设计或 UI 原型。
- 不选择 baseline API。
- 不修改后续阶段产物。
- 不写流程控制文件；状态、暂停、恢复和下一 Agent 调度属于 Orchestrator。

## 输入

RequirementAgent 可以提供以下任意输入：
- 用户项目描述。
- ticket URL。
- 需求文档路径或文档正文。
- Human Gate 确认后的补充意见。

如果输入来自 URL 或需要登录的页面，按 `references/input-fetching.md` 抓取。无法自动抓取时，不要猜内容，把需要人工处理的动作交给 RequirementAgent。

## 分析流程

### 1. 提取基础信息

提取并保留证据来源：
- `project_name`
- `business_goal`
- `source_type`
- `source_ref`
- `product_id`
- `product_version`
- 原始需求摘要
- 参与角色和外部系统
- 明确不做范围

`product_id` 和 `product_version` 如果缺失，不能输出最终版，只能输出带 `open_questions` 的草稿。

### 2. 拆解功能需求

把需求拆成稳定编号的功能项，例如 `F-01`、`F-02`。
每个功能项至少包含：
- 标题和摘要。
- 触发条件。
- 输入和输出。
- 业务规则。
- 数据规则。
- 权限规则。
- 状态流转。
- 异常和边界。
- Given/When/Then 验收标准。

拆解深度和证据级别规则见 `references/analysis-rules.md`。

### 3. 分析平台依赖和数据来源

每个功能项都要判断是否依赖平台已有对象、事件、规则、权限、状态、配置或主数据。

对于通知、推送、发送、分派、审批、订阅、触达等动作，必须分析目标对象：
- 作用到谁或什么对象。
- 目标来源是什么。
- 如何过滤目标。
- 联系方式或标识从哪里获得。

数据来源不明确时，不要标成“不依赖平台”，而是写入 `open_questions`。

### 4. 形成 Human Gate 问题

当缺少关键事实时：
- 输出草稿 `artifacts/01_requirement.json`。
- 设置 `status=draft`。
- 在 `open_questions` 中写稳定 `id`、问题、已知事实、可选项、推荐项和影响范围。
- 停止声明最终完成，让 RequirementAgent 把问题交给 Human Gate。

Human Gate 决策回传后，要更新对应功能项、澄清记录和证据级别。

### 5. 输出 artifact

必须输出：

```text
artifacts/01_requirement.json
```

推荐结构：

```json
{
  "schema_version": "1.0",
  "status": "final|draft",
  "project_name": "",
  "business_goal": "",
  "source": {
    "source_type": "ticket|manual|document|mixed",
    "source_ref": "",
    "summary": ""
  },
  "product": {
    "product_id": "",
    "product_version": "",
    "aliases": []
  },
  "user_roles": [],
  "functional_requirements": [],
  "non_functional_requirements": [],
  "constraints": [],
  "acceptance_criteria": [],
  "platform_dependency_tasks": [],
  "open_questions": [],
  "risks": []
}
```

JSON 必须用 serializer 写入，不能手工拼接字符串。写完后立即 `json.load` 重新读取。

## 校验

优先运行：

```text
python scripts/validate_requirement.py --input artifacts/01_requirement.json
```

如果使用旧兼容 validator，也可以通过阶段内脚本校验：

```text
python .claude/skills/requirement-analysis/scripts/validate_requirement.py --handoff <path> --output <path> --project-root <project_root>
```

## 完成标准

只有满足以下条件，RequirementAgent 才能把本阶段标为 `final`：
- 项目名称、业务目标、产品标识和版本已确认。
- 功能需求已拆解并具备验收标准。
- 每个功能项都有平台依赖和数据来源分析。
- 无关键 `open_questions`。
- `artifacts/01_requirement.json` 已写入并可被 JSON 解析。

否则必须输出 `draft` 并进入 Human Gate。

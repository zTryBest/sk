# Agent 执行协议

当 RequirementAgent 或 Agent Team 成员执行需求分析阶段时，使用本协议。

## Agent 职责

- 先读取 `.claude/skills/requirement-analysis/SKILL.md`。
- 只按需读取 reference 文件，避免把无关上下文塞进当前阶段。
- MCP、Browser、WebFetch 和本地脚本都只是工具，不承担流程调度。
- 所有结论都要标注证据状态：明确、澄清、推断或待确认。
- 只产出需求分析阶段 artifact。

## Main Agent 接口

Main Agent 应提供：
- ticket URL、文档路径、文档内容、用户描述或项目目标。
- 项目根目录和 artifact 输出目录。
- 已知产品标识和版本。
- Human Gate 已确认的补充意见。

RequirementAgent 应返回：
- `artifacts/01_requirement.json` 路径。
- `status`：`final` 或 `draft`。
- `open_questions`：最终版为空。
- 交给 DesignAgent 的风险和上下文摘要。

## Human Gate 行为

阶段 Agent 不直接询问用户，也不写流程控制文件。

如果缺少关键事实：
- 写入草稿 artifact。
- 设置 `status=draft`。
- 在 `open_questions` 中写稳定 `id`、问题、已知事实、可选项、推荐项和影响范围。
- 停止声明最终完成，把问题清单返回 Main Agent。

Human Gate 决策回传后，复用同一个问题 `id`，并更新相关功能项、澄清记录和证据级别。

## 可选辅助 Agent

在 Agent Team 模式下，可以由 Main Agent 安排只读辅助 Agent 完成：
- 来源材料抓取和摘要。
- 平台依赖覆盖检查。
- 需求拆解质量审查。

最终综合、文件写入和校验仍由 RequirementAgent 负责。

## 文件规则

- JSON 必须用 serializer 写入。
- 不在 artifact 目录留下 `_gen_*.py` 等临时 helper。
- 不写流程控制文件；调度、重试、Human Gate 持久化和下一 Agent 派发属于 Orchestrator/Main Agent。

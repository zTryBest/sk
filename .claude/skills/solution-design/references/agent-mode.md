# Agent 执行协议

当 DesignAgent 或 Agent Team 成员执行方案设计阶段时，使用本协议。

## Agent 职责

- 先读取 `.claude/skills/solution-design/SKILL.md`。
- 只按需读取 reference 文件，尤其是 MCP 规则和输出契约。
- MCP 服务是 baseline API 和平台能力证据工具，不承担流程调度。
- DesignAgent 负责最终方案综合、JSON 写入、validator 执行和阶段摘要。
- 只产出方案设计阶段 artifact。

## Main Agent 接口

Main Agent 应提供：
- `artifacts/01_requirement.json`。
- Human Gate 已确认的设计决策。
- 数据库类型、运行环境、部署形态、组件覆盖配置或 MCP 可用性说明。

DesignAgent 应返回：
- `artifacts/02_solution.json` 路径。
- `status`：`final` 或 `draft`。
- `open_decisions`：最终版为空。
- MCP 证据缺口。
- 给编码阶段的实现风险。

## Human Gate 行为

阶段 Agent 不直接询问用户，也不写流程控制文件。

如果缺少关键设计决策：
- 写入草稿 artifact。
- 设置 `status=draft`。
- 在 `open_decisions` 中写稳定 `id`、决策问题、已知事实、可选项、推荐项、影响范围和相关 MCP 证据。
- 停止声明最终完成，把决策清单返回 Main Agent。

Human Gate 决策回传后，复用同一个问题 `id`，并更新架构决策、实现方式分类、MCP 选择、风险和方案 JSON。

## 可选辅助 Agent

在 Agent Team 模式下，可以由 Main Agent 安排只读辅助 Agent 完成：
- MCP 证据研究。
- 架构方案审查。
- 版本兼容和风险审查。

最终综合、文件写入和校验仍由 DesignAgent 负责。

## 文件规则

- JSON 必须用 serializer 写入。
- API 示例、请求/响应样例和用户原话不能破坏 JSON。
- 不在 artifact 目录留下 `_gen_*.py` 等临时 helper。
- 不写流程控制文件；调度、重试、Human Gate 持久化和下一 Agent 派发属于 Orchestrator/Main Agent。

# AI Dev Agent Demo

本项目采用以下分工：

```text
Command = 从哪启动整条流程
Agent = 谁来做
Skill = 怎么做
MCP = 查什么资料/调用什么工具
Artifact = 每一步留下什么结果
Script = 校验、测试、构建这些确定性动作
```

## 入口

在 Claude Code 中使用：

```text
/project-run
```

入口命令位于：

```text
.claude/commands/project-run.md
```

## 流程

```text
RequirementAgent -> artifacts/01_requirement.json -> Human Gate
DesignAgent -> artifacts/02_solution.json -> Human Gate
PrototypeAgent -> artifacts/03_prototype.html -> Human Gate
PlannerAgent -> artifacts/04_plan.json -> Human Gate
BackendAgent -> workspace/backend + artifacts/05_backend_report.md
FrontendAgent -> workspace/frontend + artifacts/06_frontend_report.md
TestAgent -> artifacts/07_test_report.md
ReviewAgent -> artifacts/08_final_report.md
```

## 目录

```text
.claude/commands/      项目入口命令
.claude/agents/        Agent Team 角色定义
.claude/skills/        各阶段 Skill 方法论
mcp/                   MCP 服务说明和封装位置
scripts/               校验、测试、报告脚本
artifacts/             阶段产物
workspace/             编码工作区
```

## 关键约束

- 每个阶段必须读取上一个阶段产物。
- 每个阶段必须写入 `artifacts/`。
- 不允许跳过 Human Gate。
- 编码阶段不得修改需求、方案、原型和计划 artifact。
- Skill 除关键词和专业词汇外，以中文为主。

# Issue-Log 协议

## 概述

issue-log 是跨阶段问题上报机制。任何 Agent 在执行过程中发现上游产物问题时，不直接修改上游 artifact，而是通过 issue 上报。

## 核心原则

1. **不改上游** — Agent 只能修改自己阶段的产物，上游问题必须走 issue。
2. **Orchestrator 仲裁** — issue 由 Orchestrator 汇总、分类，通过 Human Gate 决策处理方式。
3. **追溯性** — 每个 issue 记录发现者、影响范围、建议和最终决策。

## Issue 严重级别

| 级别 | 含义 | Orchestrator 动作 |
|------|------|------------------|
| `blocking` | 阻塞当前阶段继续进行 | 立即暂停，进入 Human Gate |
| `warning` | 不阻塞但需关注 | 在下次 Human Gate 时展示 |
| `info` | 记录备查 | 仅记录，交付审查时汇总 |

## issue-log.json Schema

```json
{
  "schema_version": "1.0",
  "issues": [
    {
      "id": "ISS-{NNN}",
      "reporter_stage": "",
      "reporter_agent": "",
      "timestamp": "<ISO8601>",
      "severity": "blocking|warning|info",
      "category": "",
      "title": "",
      "description": "",
      "affected_artifacts": [],
      "affected_requirements": [],
      "suggested_action": "",
      "resolution": null,
      "resolved_at": null,
      "resolved_by_decision": null
    }
  ]
}
```

## Issue 分类

| category | 含义 | 典型来源 |
|----------|------|---------|
| `requirement_gap` | 需求遗漏或不完整 | 编码阶段发现功能定义缺失 |
| `design_conflict` | 方案设计与需求或实际矛盾 | 编码阶段发现接口设计不可行 |
| `dependency_missing` | 缺少外部依赖或配置 | 编码阶段发现需要的服务未定义 |
| `contract_violation` | 接口契约与实现不一致 | 前端消费后端 API 时发现不匹配 |
| `risk` | 潜在风险或技术债务 | 任何阶段发现的安全、性能风险 |
| `test_failure` | 测试不通过 | 测试阶段 |

## Agent 上报方式

Agent 在其 output report 中包含 issues 段落：

```markdown
## Issues Found

| id | severity | category | title | affected |
|----|----------|----------|-------|----------|
| ISS-xxx | blocking | design_conflict | ... | artifacts/02_solution.json |
```

或者在 JSON artifact 中包含 `issues_found` 字段：

```json
{
  "issues_found": [
    {
      "severity": "warning",
      "category": "requirement_gap",
      "title": "F-03 缺少异常回退路径定义",
      "description": "...",
      "affected_artifacts": ["artifacts/01_requirement.json"],
      "affected_requirements": ["F-03"],
      "suggested_action": "回到需求阶段补充状态机定义"
    }
  ]
}
```

Orchestrator 负责：
1. 从 Agent 返回中提取 issues。
2. 分配 `ISS-{NNN}` 编号。
3. 写入 `.ai-dev/issue-log.json`。
4. 根据 severity 决定是否立即触发 Human Gate。

## Issue 解决

issue 只能通过 Human Gate 决策解决：

```json
{
  "resolution": "用户描述的处理方式",
  "resolved_at": "<ISO8601>",
  "resolved_by_decision": "DEC-xxx"
}
```

解决方式包括：
- **回退修复**：回退到受影响的阶段，重新执行。
- **接受风险**：标记为 accepted risk，继续推进。
- **变通处理**：在当前阶段实施变通方案（需记录）。
- **延后处理**：标记为 deferred，在交付审查时再议。

## 初始化

当 `.ai-dev/issue-log.json` 不存在时，创建：

```json
{
  "schema_version": "1.0",
  "issues": []
}
```

## ID 生成

- 格式：`ISS-{三位数字}`
- 从 001 开始递增。
- 读取现有 issue-log 最后一个 id，+1。

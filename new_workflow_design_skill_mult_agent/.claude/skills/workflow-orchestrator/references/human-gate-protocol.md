# Human Gate 协议

## 概述

Human Gate 是 Orchestrator 在每个阶段完成后与用户交互的机制。它确保：
- 用户始终对产物有最终决定权。
- 决策被完整记录，可追溯。
- Agent 不会在无人确认的情况下推进 pipeline。

## Gate 触发时机

1. Agent 返回 artifact 且 `status=final` → 展示摘要，请求 APPROVE/REVISE/REJECT。
2. Agent 返回 artifact 且 `status=draft`（有 open_questions/open_decisions） → 展示问题，收集答案后重新调度。
3. 编码阶段出现 `blocking` issue → 展示 issue，请求处理决策。
4. optional 阶段到达时 → 询问是否执行。

## Gate 流程

### Case 1: Final Artifact

```
Orchestrator 输出：
───────────────────────────────────
## 📋 {阶段名称} 完成

**产物**: {artifact 路径}
**摘要**: {Agent 返回的摘要，3-5 句话}

{如有 warning 级别 issue，在此展示}

请选择：
- APPROVE：确认通过，进入下一阶段
- REVISE：需要修改（请说明修改意见）
- REJECT：拒绝，需要重新考虑
───────────────────────────────────
```

### Case 2: Draft Artifact (需要澄清)

```
Orchestrator 输出：
───────────────────────────────────
## ❓ {阶段名称} 需要确认

Agent 完成了草稿，但有以下问题需要您确认：

{遍历 open_questions/open_decisions:}
### Q{n}: {question}
- 已知事实：{known_facts}
- 推荐选项：{recommended}
- 可选项：{options}
- 影响范围：{impact}

请逐一回答，或输入 "REJECT" 终止本阶段。
───────────────────────────────────
```

### Case 3: Blocking Issue

```
Orchestrator 输出：
───────────────────────────────────
## ⚠️ 阻塞问题

来源：{reporter_stage} / {reporter_agent}
标题：{title}
描述：{description}
影响：{affected_artifacts}
建议：{suggested_action}

请选择：
- 按建议处理（描述您的决定）
- 回退到 {affected_stage} 阶段修复
- 忽略并继续（标记为 accepted risk）
───────────────────────────────────
```

### Case 4: Optional Stage

```
Orchestrator 输出：
───────────────────────────────────
## 📐 可选阶段：{阶段名称}

本阶段是可选的。{阶段说明}

是否执行？
- YES：执行本阶段
- SKIP：跳过，直接进入下一阶段
───────────────────────────────────
```

## 用户响应解析

| 用户输入 | 动作 |
|----------|------|
| APPROVE / 通过 / 确认 / OK / 没问题 | gate_decision = APPROVE |
| REVISE + 修改意见 | gate_decision = REVISE，提取修改意见 |
| REJECT / 拒绝 / 不行 | gate_decision = REJECT |
| 直接回答问题（Case 2） | 收集答案，gate_decision = REVISE（带答案重新调度） |
| YES / 执行（Case 4） | 执行 optional 阶段 |
| SKIP / 跳过（Case 4） | gate_decision = SKIP |

## Decision-Log 写入

每次 Human Gate 完成后，追加到 `.ai-dev/decision-log.json`：

```json
{
  "schema_version": "1.0",
  "decisions": [
    {
      "id": "DEC-{NNN}",
      "stage": "",
      "timestamp": "<ISO8601>",
      "type": "APPROVE|REVISE|REJECT|SKIP|ANSWER",
      "artifact_version": 1,
      "summary": "",
      "user_feedback": "",
      "open_questions_resolved": [],
      "context": ""
    }
  ]
}
```

### id 生成规则

- 格式：`DEC-{三位数字}`
- 从 001 开始递增。
- 读取现有 decision-log 最后一个 id，+1。

## Decision-Log 初始化

当 `.ai-dev/decision-log.json` 不存在时，创建：

```json
{
  "schema_version": "1.0",
  "decisions": []
}
```

## Gate 后状态更新

| 决策 | state.json 更新 |
|------|----------------|
| APPROVE | stage.status = "approved", stage.gate_decision = "APPROVE", stage.gate_decision_id = "DEC-xxx", stage.completed_at = now |
| REVISE | stage.status = "revision_requested", stage.gate_decision = "REVISE", stage.gate_decision_id = "DEC-xxx" |
| REJECT | stage.status = "rejected", stage.gate_decision = "REJECT", stage.gate_decision_id = "DEC-xxx" |
| SKIP | stage.status = "skipped", stage.gate_decision = "SKIP", stage.gate_decision_id = "DEC-xxx", stage.completed_at = now |
| ANSWER (draft 问题回答) | stage.status = "revision_requested"（带答案重新调度 Agent） |

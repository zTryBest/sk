# Human Gate 协议

> **STOP — Agent 返回后，必须先看 `status` 字段，再决定走哪个 Case。**
> - `status: "draft"` + `open_questions[]` / `open_decisions[]` 非空 → **必须先按 Case 2 逐项 AskUserQuestion 收集答案**，全部收集完才能进 Case 1 的 APPROVE/REVISE/REJECT
> - `status: "final"` → 走 Case 1
> - blocking issue → 走 Case 3
> - optional 阶段 → 走 Case 4
>
> **禁止跳过 OQ/Decision 收集直接问 APPROVE/REVISE/REJECT。**
> **禁止用纯文本一次性列出所有 OQ 让用户回答 — 必须用 `AskUserQuestion` 工具。**

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

**强制规则：用 `AskUserQuestion` 工具收集决策，不要让用户输入 APPROVE/REVISE/REJECT 关键字。**

#### 1.1 展示前置上下文

先输出一段简短的摘要（不要让用户选择前看不到产物概要）：

```
## 📋 {阶段名称} 完成

**产物**：{artifact 路径}
**摘要**：{Agent 返回的摘要，3-5 句话}
{如有 warning 级别 issue，在此简短列出}
```

#### 1.2 调用 AskUserQuestion

```
AskUserQuestion(
  questions: [{
    question: "{阶段名称}的产物如何处理？",
    header: "Gate-{阶段缩写}",  // 例如 Gate-Req / Gate-Design / Gate-Proto
    multiSelect: false,
    options: [
      {label: "APPROVE 通过", description: "进入下一阶段"},
      {label: "REVISE 修改", description: "提出修改意见后重新调度本阶段 Agent"},
      {label: "REJECT 拒绝", description: "终止 pipeline 或回退到上一阶段"}
    ]
  }]
)
```

#### 1.3 后续动作

- 用户选 **APPROVE** → `gate_decision = APPROVE`

> **STOP — APPROVE 后的下一步不是推进 pipeline，而是执行 1.4 记忆沉淀。**
> 记忆沉淀是 APPROVE 的即时副作用，禁止推迟到"所有阶段都完成再总结"。**

- 用户选 **REVISE** → 紧接着用 AskUserQuestion 或直接接收用户文本说明修改意见，写入 decision-log 的 `user_feedback`
- 用户选 **REJECT** → 进入 Case 5 拒绝处理流程（询问回退到哪个阶段）
- 用户选 **Other** → 解析自由文本，匹配 APPROVE/REVISE/REJECT 之一

#### 1.4 记忆沉淀（仅 APPROVE 触发，强制执行）

按 `memory-protocol.md` 第 3 节执行。**这是 APPROVE 的硬性副作用，不能跳过。**

1. orchestrator 读本阶段 artifact + 本次 decision-log + 本阶段 warning issues
2. 生成两类候选条目：
   - 项目经验候选（0-3 条）：本项目特定的事实/决策/踩坑
   - Agent 通用经验候选（0-2 条）：可复用到其他项目的方法论改进
3. **如果候选总数 == 0**：至少生成 1 条"本阶段事实记录"作为项目经验候选（如"本阶段 product_id=XXX, version=YYY, 经确认无平台依赖"），确保每个阶段至少沉淀一条事实。**不允许空跳过。**
4. 候选总数 > 0 → 用 AskUserQuestion 让用户对每条选择「保留 / 修改 / 丢弃」，最多 4 条/批
5. 保留的条目按格式 `- [{YYYY-MM-DD} stage:{stage} DEC-{id}] {lesson}` 追加到对应文件
6. 文件不存在时按 memory-protocol.md 第 6 节初始化

### Case 2: Draft Artifact (需要澄清)

**强制规则：必须用 `AskUserQuestion` 工具收集答案，禁止用纯文本列出所有 OQ 让用户"逐一回答"。**

#### 2.1 工具映射

把 `open_questions[]` / `open_decisions[]` 映射成 AskUserQuestion 的 `questions[]`：

| OQ 字段 | AskUserQuestion 字段 | 处理 |
|---|---|---|
| `OQ.question` | `questions[].question` | 直接用。如果 `known_facts` 非空，在 question 末尾追加一行"已知事实：{known_facts}"。 |
| `OQ.id`（如 `OQ-URL-01`） | `questions[].header` | 截断到 12 字符，保持可识别性。如 `OQ-URL-01` 直接用，`OQ-PLATFORM-VERSION` 截成 `OQ-PLATFRM`。 |
| `OQ.options[]` | `questions[].options[].label` | 每个选项作为一个 option。 |
| `OQ.recommended` | 推荐选项排第一 + 后缀 "(推荐)" | 找出与 `recommended` 匹配的 option，移到 `options[0]`，label 后加 " (推荐)"。 |
| `OQ.impact` | `questions[].options[].description` | 把 impact 放到推荐选项的 description 里；其他选项的 description 自动用 OQ 中的备注或简短说明。 |
| — | `questions[].multiSelect` | 固定 `false`（OQ 是单选）。 |

#### 2.2 调用约束

- **每次最多 4 个 question**：AskUserQuestion 工具上限 4。OQ 超过 4 个时分批调用，按 OQ id 顺序处理，前一批答完再发下一批。
- **每个 question 2-4 个 option**：如果 OQ.options 多于 4 → 截断到前 4（推荐项必须保留）；少于 2 → 补一个"其他（请说明）"作为兜底。系统会自动加 "Other"，所以不需要手动加 Other 项。
- **不展示**：在调 AskUserQuestion 之前不输出任何"请回答以下问题"的文本前缀；阶段名和摘要可以放在调用之前一句话里。

#### 2.3 调用模板

```
首先输出一句话上下文（不要列 OQ）：
> {阶段名称}已生成草稿，有 N 项需要您确认。

然后调用：
AskUserQuestion(
  questions: [
    {
      question: "{OQ.question}\n\n已知事实：{OQ.known_facts}",
      header: "{OQ.id 截断到 12 字符}",
      multiSelect: false,
      options: [
        {label: "{recommended option} (推荐)", description: "{OQ.impact}"},
        {label: "{other option 2}", description: "..."},
        {label: "{other option 3}", description: "..."}
      ]
    },
    ...最多 4 个
  ]
)
```

#### 2.4 兜底输出

只有以下情况用纯文本：
- OQ 本身没有 `options[]`（自由文本回答场景）→ 此时一次只展示一个 OQ，用文本提问。
- 用户在 AskUserQuestion 中选了"Other"且需要自由文本说明 → 工具回传中的 `notes` 字段已包含，无需再次提问。

### Case 3: Blocking Issue

**强制规则：用 `AskUserQuestion` 工具收集处置决策，不要让用户输入纯文本。**

#### 3.1 展示前置上下文

```
## ⚠️ 阻塞问题

来源：{reporter_stage} / {reporter_agent}
标题：{title}
描述：{description}
影响：{affected_artifacts}
建议：{suggested_action}
```

#### 3.2 调用 AskUserQuestion

```
AskUserQuestion(
  questions: [{
    question: "如何处理此阻塞问题？",
    header: "Block-{issue.id}",  // 例如 Block-001，截断到 12 字符
    multiSelect: false,
    options: [
      {label: "按建议处理 (推荐)", description: "{suggested_action 简述}"},
      {label: "回退到 {affected_stage}", description: "回退到对应阶段修复，pipeline 状态回退"},
      {label: "忽略并继续", description: "标记为 accepted risk，写入 issue-log"}
    ]
  }]
)
```

#### 3.3 后续动作

- 选"按建议处理" → 再用 AskUserQuestion 或文本收集用户具体的决定描述
- 选"回退" → 设置 `current_stage` 为 `affected_stage`，状态 = `revision_requested`
- 选"忽略" → issue 标记 `resolution = "accepted_risk"`，pipeline 继续

### Case 4: Optional Stage

**强制规则：用 `AskUserQuestion` 工具，不要让用户输入 YES/SKIP。**

#### 4.1 展示前置上下文

```
## 📐 可选阶段：{阶段名称}

本阶段是可选的。{阶段说明}
```

#### 4.2 调用 AskUserQuestion

```
AskUserQuestion(
  questions: [{
    question: "是否执行 {阶段名称} 阶段？",
    header: "Opt-{阶段缩写}",  // 例如 Opt-Proto
    multiSelect: false,
    options: [
      {label: "YES 执行", description: "调度对应 Agent 完成此阶段"},
      {label: "SKIP 跳过", description: "标记 stage.status = skipped，直接进入下一阶段"}
    ]
  }]
)
```

#### 4.3 后续动作

- 选 YES → 调度对应 Agent
- 选 SKIP → `stage.status = "skipped"`，`gate_decision = "SKIP"`，推进

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

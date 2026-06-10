# 状态机规范

## state.json Schema

```json
{
  "schema_version": "1.0",
  "project_name": "",
  "project_description": "",
  "created_at": "",
  "updated_at": "",
  "current_stage": "",
  "stages": []
}
```

## Stage 定义

```json
{
  "id": "requirement-analysis",
  "order": 1,
  "status": "pending",
  "agent": "RequirementAgent",
  "skill": "requirement-analysis",
  "artifact": "artifacts/01_requirement.json",
  "optional": false,
  "attempts": 0,
  "max_attempts": 5,
  "started_at": null,
  "completed_at": null,
  "gate_decision": null,
  "gate_decision_id": null
}
```

## 完整 Pipeline Stages

| order | id | agent | skill | artifact | optional |
|-------|-----|-------|-------|----------|----------|
| 1 | requirement-analysis | RequirementAgent | requirement-analysis | artifacts/01_requirement.json | false |
| 2 | solution-design | DesignAgent | solution-design | artifacts/02_solution.json | false |
| 3 | prototype-design | PrototypeAgent | prototype-design | artifacts/03_prototype.html | true |
| 4 | task-planning | PlannerAgent | task-planning | artifacts/04_plan.json | false |
| 5 | coding | AgentTeam | null | null | false |
| 6 | delivery-review | ReviewAgent | delivery-review | artifacts/08_final_report.md | false |

## 状态枚举

| 状态 | 含义 |
|------|------|
| `pending` | 尚未开始 |
| `in_progress` | Agent 正在执行 |
| `awaiting_gate` | Agent 完成，等待 Human Gate |
| `approved` | Human Gate 通过 |
| `revision_requested` | 用户要求修改，等待重新调度 |
| `rejected` | 用户拒绝，pipeline 暂停 |
| `skipped` | optional 阶段被跳过 |

## 状态转换规则

```
pending ─────────────────────→ in_progress        (Orchestrator 调度 Agent)
in_progress ─────────────────→ awaiting_gate      (Agent 完成，artifact 产出)
awaiting_gate ───────────────→ approved           (Human Gate: APPROVE)
awaiting_gate ───────────────→ revision_requested (Human Gate: REVISE)
awaiting_gate ───────────────→ rejected           (Human Gate: REJECT)
revision_requested ──────────→ in_progress        (Orchestrator 重新调度 Agent)
pending (optional) ──────────→ skipped            (用户确认跳过)
rejected ────────────────────→ pending            (用户决定重来本阶段)
rejected ────────────────────→ 回退到更早阶段      (用户指定回退点)
```

## 推进规则（强约束）

当 `current_stage` 的 status 变为 `approved` 或 `skipped` 时：

```
1. 从 state.json.stages[] 找到当前 stage.order
2. 找 order = current_order + 1 的 stage
   - 不存在 → pipeline 完成
3. 检查该 stage.optional：
   - optional == true  → Case 4 AskUserQuestion（YES/SKIP）
   - optional == false → 更新 current_stage 为该 stage.id，status = "pending"
4. 继续主循环
```

**推进必须是 `order + 1`，不能跳 order。** 从 state.json.stages[] 读 order 字段，不能凭 orchestrator Pipeline 阶段定义的文字顺序推断。

### 常见错误（违反即流程错误）

| ❌ 错误行为 | ✓ 正确行为 |
|---|---|
| prototype-design (order 3) approved → current_stage 直接切 coding (order 5) | prototype-design (order 3) approved → 找 order 4 → task-planning pending |
| requirement-analysis approved → 跳过 solution-design 直接进 prototype-design | order 1 approved → order 2 (non-optional) → 必须 pending |
| optional 阶段用户选 YES → approved 后跳过下一个非 optional 阶段 | optional YES → 执行 → approved → order+1 → 正常推进 |

### 同步检查表（每次推进时执行）

```
推进前：
  current_order = ___
  next_order = current_order + 1 = ___
  next_stage_id = ___
  next_stage.optional = true/false

确认后在新 prompt 或状态日志中输出：
  "Stage X (order N) approved → 推进到 Stage Y (order N+1)"
```

如果输出里没有这行，视为推进未执行。

## 回退规则

当 Human Gate 选择 REJECT 时：
1. 当前 stage status 设为 `rejected`。
2. 询问用户：
   - 重来本阶段（当前 stage reset 为 `pending`）。
   - 回退到指定阶段（目标 stage 和后续所有 stage reset 为 `pending`，清除对应 artifact）。
   - 终止 pipeline。
3. 回退时不删除 decision-log 和 issue-log 中的历史记录。

## attempts 规则

- 每次调度 Agent（包括 REVISE 重新调度），attempts + 1。
- 达到 `max_attempts` 时提示用户：继续尝试 / 跳过（仅 optional）/ 终止。

## 初始化模板

当 `<project_root>/.ai-dev/state.json` 不存在时，创建：

**`project_root` = 当前 Claude Code 的工作目录（会话 CWD）。** 所有 `.ai-dev/`、`artifacts/`、`workspace/` 路径都基于此拼接。

```json
{
  "schema_version": "1.0",
  "project_name": "",
  "project_description": "",
  "project_root": "<当前 CWD 绝对路径，如 E:/AI/demo>",
  "created_at": "<ISO8601>",
  "updated_at": "<ISO8601>",
  "current_stage": "requirement-analysis",
  "stages": [
    {"id": "requirement-analysis", "order": 1, "status": "pending", "agent": "RequirementAgent", "skill": "requirement-analysis", "artifact": "artifacts/01_requirement.json", "optional": false, "attempts": 0, "max_attempts": 5, "started_at": null, "completed_at": null, "gate_decision": null, "gate_decision_id": null},
    {"id": "solution-design", "order": 2, "status": "pending", "agent": "DesignAgent", "skill": "solution-design", "artifact": "artifacts/02_solution.json", "optional": false, "attempts": 0, "max_attempts": 5, "started_at": null, "completed_at": null, "gate_decision": null, "gate_decision_id": null},
    {"id": "prototype-design", "order": 3, "status": "pending", "agent": "PrototypeAgent", "skill": "prototype-design", "artifact": "artifacts/03_prototype.html", "optional": true, "attempts": 0, "max_attempts": 5, "started_at": null, "completed_at": null, "gate_decision": null, "gate_decision_id": null},
    {"id": "task-planning", "order": 4, "status": "pending", "agent": "PlannerAgent", "skill": "task-planning", "artifact": "artifacts/04_plan.json", "optional": false, "attempts": 0, "max_attempts": 5, "started_at": null, "completed_at": null, "gate_decision": null, "gate_decision_id": null},
    {"id": "coding", "order": 5, "status": "pending", "agent": "AgentTeam", "skill": null, "artifact": null, "optional": false, "attempts": 0, "max_attempts": 10, "started_at": null, "completed_at": null, "gate_decision": null, "gate_decision_id": null},
    {"id": "delivery-review", "order": 6, "status": "pending", "agent": "ReviewAgent", "skill": "delivery-review", "artifact": "artifacts/08_final_report.md", "optional": false, "attempts": 0, "max_attempts": 3, "started_at": null, "completed_at": null, "gate_decision": null, "gate_decision_id": null}
  ]
}
```

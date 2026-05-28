---
name: full-workflow
description: >
  End-to-end workflow: requirement analysis → design phase. Runs both skills
  sequentially, passing the requirements document to the design phase
  automatically. This skill should be used when the user wants to go from
  raw requirement all the way to detailed design in one session.
---

# Full Workflow: 需求分析 → 方案设计

## Purpose

Chain `requirement-analysis` and `design-phase` into a single automated pipeline.
Output: requirements document + detailed design document.

## CRITICAL: Auto-Progression Rule

**Never make the user type "继续" or "继续吧" to advance the workflow.**

After EVERY phase, sub-phase, or batch of work, you MUST:
1. Present a brief summary of what was just done
2. Immediately call `AskUserQuestion` with the next action as choices
3. Default choice should always be "继续" or the natural next step
4. The user clicks — they never type to advance

This applies to:
- Between Step 1 and Step 2 (requirement → design transition)
- Between every Phase inside design-phase (architecture → components → frontend → API → database → document)
- Between Step 4 and Step 5 (design → pencil)
- Any time you finish a block of work and need user sign-off

**Anti-pattern (forbidden):**
```
"Phase 4 完成。继续 Phase 5？"  ← user has to TYPE "继续"
```

**Correct pattern (required):**
```
AskUserQuestion("Phase 4 完成，进入 Phase 5 后端接口设计？", ["继续", "先调整 Phase 4"])
```

## Workflow

### Step 1: Requirement Analysis

1. Load the `requirement-analysis` skill.
2. Follow its workflow: extract → decompose → ambiguity resolution → document.
3. After ALL ambiguities resolved and document saved, go to Step 2 immediately.
4. Do NOT end your turn — call `AskUserQuestion` to auto-transition.

### Step 2: Auto-Transition

Present summary, then immediately call `AskUserQuestion`:

```
AskUserQuestion(
  "需求分析完成——N 个功能项, N 个角色, N 个确认项已解决。是否继续方案设计？",
  ["继续方案设计", "先调整需求"]
)
```

DO NOT ask in plain text. MUST use `AskUserQuestion` with choices.

### Step 3: Design Phase

1. Load the `design-phase` skill.
2. Pass the requirements document path as input.
3. Follow its workflow, and **at every confirmation gate, use `AskUserQuestion` with choices**.
4. After ALL phases confirmed and document written → go to Step 4 immediately.

### Step 4: Final Summary

Present summary, then immediately call `AskUserQuestion`:

```
AskUserQuestion(
  "方案设计完成。是否使用 Pencil 生成前端静态页面？",
  ["生成前端页面 (Pencil)", "跳过，先做后端开发", "结束流程"]
)
```

### Step 5 (Optional): Pencil

If user picks Pencil:
1. Load the `pencil` skill.
2. Pass the design document path.
3. Output to `%USERPROFILE%\\.claude\\outputs\\frontend\\<platform>\\<feature-name>\\`.

## Pitfalls

- **NEVER ask user to type "继续"** — always use `AskUserQuestion` with choices
- **NEVER end a turn waiting for a text reply** — if you need confirmation, use `AskUserQuestion`
- **After every phase boundary, call `AskUserQuestion` immediately**
- **Default choice should be the natural next step**
- Architecture first — confirm before jumping to pages/APIs
- Frontend → Gateway only

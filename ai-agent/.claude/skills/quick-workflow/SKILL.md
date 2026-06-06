---
name: quick-workflow
description: >
  Auto-pilot workflow: requirement analysis → design phase, with ZERO
  confirmation gates. For simple, well-understood requirements where the
  user trusts the AI to make reasonable decisions.
---

# Quick Workflow: 需求分析 → 方案设计（全自动）

## Purpose

Same pipeline as `full-workflow` but with ALL confirmation gates removed.

**When to use:**
- `quick-workflow`: straightforward features, user says "直接做" or "auto"
- `full-workflow`: complex features, ambiguity, new domains, user wants control

## CRITICAL: Minimal Interaction Rule

You may ONLY ask the user TWO things at the start:
1. Platform + version
2. Project root directory (default: `%USERPROFILE%\\hermes-projects\\<name>\\`)

After that: ZERO questions. Run fully automatic.
Mark all AI guesses as `[AI假设]`.

## Workflow

### Step 0: Bare-Minimum Setup

Ask exactly TWO questions via `AskUserQuestion`, then never interrupt again.

### Step 1: Auto Requirement Analysis

1. Load the `requirement-analysis` skill.
2. Skip ambiguity resolution. Make best guesses.
3. Mark guesses as `[AI假设]`.
4. Output: `<project-root>/docs/requirements/<feature-name>-<date>.md`

### Step 2: Auto Design Phase

1. Load the `design-phase` skill.
2. Skip ALL confirmation gates.
3. Defaults: MySQL 8.0, Spring Boot + Vue 3, JWT Auth, Redis, RabbitMQ.
4. Output: `<project-root>/docs/design/<feature-name>-设计文档-<date>.md`

### Step 3: Final Summary + Pencil

Present summary, then ONE `AskUserQuestion`:
```
["生成前端页面", "结束"]
```

## Assumptions & Defaults

| Decision | Default |
|----------|---------|
| Database | MySQL 8.0 |
| Tech stack | Spring Boot + Vue 3 + Element Plus |
| Auth | JWT |
| Cache | Redis |

## Pitfalls

- ONLY 2 questions at start
- Never ask "继续？"
- Mark AI decisions as `[AI假设]`
- Not for complex features — suggest `full-workflow`

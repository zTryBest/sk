---
name: requirement-analysis
description: >
  Parse a requirement from a ticket URL or manual input, decompose it into
  discrete functional items with acceptance criteria. Platform version is
  mandatory. This skill is the human-confirmation-heavy entry point before
  design. This skill should be used when the user provides a requirement
  description, a ticket URL, or asks to analyze/break down requirements.
---

# Requirement Analysis

## Purpose

Decompose a natural-language requirement into structured, confirmable functional
items. This is the entry point of the development workflow and the most
human-interactive phase.

This skill does NOT:
- Design frontend pages or describe UI (→ design-phase skill)
- Identify backend API modules (→ design-phase skill)
- Generate code or static pages

This skill DOES:
- Extract and understand the requirement from a URL or manual input
- Break it into discrete functional items with Given/When/Then acceptance criteria
- Identify actors, constraints, and scope
- Surface ambiguities for human confirmation
- Output a requirements document

## Input

### Mode A: Ticket URL (preferred)

For internal ticket systems (Jira, TAPD, 禅道, 飞书, 自研系统):

1. Use web_fetch or Playwright MCP to retrieve page content.
2. Parse to extract:
   - **Platform + version** — MANDATORY. Stop and ask if not found.
   - Requirement title and full description
   - Attachments (note existence for images)
3. If behind SSO, use Playwright MCP with persistent browser profile for login.

### Mode B: Manual Input

- Platform + version is MANDATORY. Stop and ask if missing.
- Also collect: source/ticket ID, related modules, user roles.

## Workflow

### Phase 1: Extract & Parse

1. Extract requirement text from the source.
2. Identify platform + version (gate — do not proceed without).
3. Preserve raw original text for traceability.

### Phase 2: Understand & Decompose

#### 2.1 Core Problem Statement
One sentence: what problem, for whom.

#### 2.2 Actors / Roles
Table with: role, responsibility, involved in this requirement.

#### 2.3 Functional Breakdown
For each functional item, produce:

```
### F-<NN>: <功能名称>

- 描述: what this feature does in plain language
- 触发条件: what causes activation
- 输入: data or user-action that triggers it
- 输出: what the system produces
- 前置条件: prerequisites
- 后置条件: post-conditions
- 验收标准:
  1. Given <precondition>, when <action>, then <expected result>
  2. ...
- 优先级: P0 / P1 / P2
- 涉及角色: which actors
```

#### 2.4 Constraints & Scope
- Platform version constraints
- Data/performance/integration constraints
- Out of scope (explicit boundary)

### Phase 3: Ambiguity Resolution

1. List every ambiguous point as `[待确认]`.
2. For each, provide a reasoned best guess.
3. Use AskUserQuestion to present in batches (max 4 at a time).
4. Record all resolved answers. Do not proceed until all resolved.

### Phase 4: Generate Requirements Document

Write to `~/.claude/outputs/requirements/<platform>/<feature-name>.md`.

## Pitfalls

- Never skip platform version. No platform = no analysis.
- Do NOT design UI or APIs here — that is the design-phase skill's job.
- Batch confirmations — 3-4 at a time, not one by one.
- Preserve original requirement text in the document.
- Break down, don't summarize — "build user management" → F-01 through F-08.

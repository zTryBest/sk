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

## Configuration

Before starting, load the three global internal system URLs:

```
%USERPROFILE%\.claude\config\internal-urls.yaml
```

> WSL 用户：`/mnt/c/Users/<username>/.claude/config/internal-urls.yaml`

These three addresses are **fixed and shared by all platforms**:

```yaml
sso_login: "https://..."           # SSO 统一认证登录地址
product_composition: "https://..."  # 产品构成查询地址
component_api: "https://..."        # 组件接口查询地址
```

- `sso_login` — 所有内部系统的认证入口。访问需登录的页面时自动跳转到此地址
- `product_composition` — 查询平台微服务清单（设计阶段使用）
- `component_api` — 查询微服务 API 契约（设计阶段使用）

**Ticket URL 不是配置文件中的固定地址。** 需求 ticket URL 由用户在每次需求分析时主动提供（Mode A）。如果用户没有提供 ticket URL，说明走手动输入模式（Mode B）。

## Input

当用户提供了 ticket URL，说明走需求单拉取模式。**必须使用级联策略**，不要预先判断 URL 是"内部"还是"公开"：

### Mode A: Ticket URL — 级联抓取策略

**核心原则：先试简单方式，失败自动升级。不要跳过第一步直接上 Playwright。**

#### Step 1: 轻量抓取（先试）

始终先尝试最轻量的方式获取页面内容：

1. **web_fetch**（首选）— 尝试直接抓取页面内容
2. **crawl4ai**（备选）— 如果可用，提取 Markdown
3. **判断结果**：
   - ✅ 成功 → 跳到 Step 3 提取信息
   - ❌ 失败（SSO 重定向、登录页、403、超时、空内容）→ **自动进入 Step 2，不要问用户**

#### Step 2: Playwright MCP（自动降级）

**触发条件**：Step 1 无法获取到有效内容。

大多数内部系统都有 SSO，轻量抓取失败是预期的。不需要问用户"要不要用 Playwright"，直接执行。

使用 Playwright MCP（需预先配置 `claude mcp add playwright`）：
1. `browser_navigate` 打开用户提供的 ticket URL
2. 未登录时自动跳转到 `sso_login` 认证
3. `browser_snapshot` 或 `browser_evaluate` 提取页面内容

#### Step 3: 提取信息

统一提取：
- **Platform + version** — MANDATORY. Stop and ask if not found.
- Requirement title and full description
- Attachments (note existence for images)

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

## What's Next

After requirements are confirmed:

```
需求文档 → Pencil Round 1 (低保真确认稿) → 业务方确认 → 方案设计
```

- **Pencil Round 1** — generate low-fidelity mockups from functional items for business
  confirmation before investing in detailed design. Use the `pencil` skill.

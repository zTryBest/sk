---
name: requirement-analysis
description: >
  Parse a requirement from a ticket URL or manual input, decompose it into
  discrete functional items with user stories and acceptance criteria.
  Platform version is mandatory. This skill is the human-confirmation-heavy
  entry point — output feeds the design phase.
triggers:
  - User provides a requirement ticket URL
  - User provides a requirement description
  - User asks to "analyze requirements" or "break down requirements"
  - User mentions "需求分析" or "需求拆解"
---

# Requirement Analysis / 需求分析

## Purpose

Take a requirement (from a ticket URL or manual input) and decompose it into
structured, confirmable functional items. This is the **entry point** of the
workflow and the **most human-interactive** phase.

**This skill does NOT:**
- Design frontend pages or describe UI (→ design-phase skill)
- Identify backend API modules (→ design-phase skill)
- Generate code or static pages (→ pencil skill / dev skill)

**This skill DOES:**
- Extract and understand the requirement
- Break it into discrete functional items
- Identify actors, constraints, and scope
- Surface ambiguities for human confirmation
- Output a requirements document that feeds the design phase

## Input

### Mode A: Ticket URL — Internal SSO System (Playwright MCP)

For internal ticket systems that require SSO login (e.g. internal Jira, TAPD,
禅道, 飞书, 自研系统):

**Infrastructure (pre-configured once):**
- Playwright MCP server at `~/.hermes/config.yaml` → `mcp_servers.playwright`
- Browser profile persisted at `~/.hermes/browser-profile/`
- `--save-session` enabled

**First-time SSO setup:**
The Playwright MCP runs headed by default. On first use:
1. Navigate to the ticket system's login page or a known ticket URL.
2. The browser window appears (WSL needs WSLg or X server for GUI).
3. User completes SSO login manually.
4. Session cookies are persisted to `--user-data-dir`.
5. Subsequent uses reuse the saved session automatically.

**Crawling flow:**
1. Use `mcp_playwright_browser_navigate` to open the ticket URL.
   - Tool name may vary; check available MCP tools with `mcp_playwright_*` prefix.
2. If SSO redirect happens → browser follows it → session cookies handle auth.
3. If session expired: prompt user to re-login (set `--headless` to false temporarily).
4. Once on the ticket page, use `mcp_playwright_browser_snapshot` to capture
   the accessibility tree of the page content.
5. Extract from the snapshot:
   - **Platform + version** — e.g. field labeled "所属平台/版本". Search the text
     for patterns like "P平台", "版本号", version numbers. **MANDATORY — if not
     found, stop and ask the user.**
   - **Requirement title** — page heading or subject line
   - **Requirement description** — the main body content
   - **Attachments** — note filenames; images can be captured with
     `mcp_playwright_browser_take_screenshot`
6. If the accessibility snapshot is insufficient, fall back to extracting the
   full page HTML with `mcp_playwright_browser_evaluate` and parsing with AI.

### Mode B: Ticket URL — Public / API-accessible (crawl4ai)

For publicly accessible pages or systems with API token auth (Confluence,
public Jira, docs sites):

1. If the page is public, call crawl4ai directly:
   ```python
   from crawl4ai import AsyncWebCrawler
   result = await crawler.arun(url="https://ticket-url")
   markdown_content = result.markdown
   ```

2. If auth is needed (API token), use curl with headers:
   ```bash
   curl -s -H "Authorization: Bearer $TOKEN" "https://api.example.com/issue/KEY-123"
   ```

3. Parse the extracted content to find platform version and requirement text.

4. Same extraction rules as Mode A step 5.

### Mode C: Manual Input

The user types or pastes the requirement directly.

**Required:**
- Platform + version (e.g. "P平台 2.4.0") — **MUST be present**. If missing, stop and ask.
- Requirement description (raw text)

**Recommended (ask if missing):**
- Requirement source / ticket ID (for traceability)
- Related modules or existing features this touches
- User types / roles affected

## Crawling Troubleshooting

### Playwright MCP not available
If MCP tools (`mcp_playwright_*`) are not available:
- Ensure `pip install mcp` succeeded
- Ensure `mcp_servers.playwright` is in `~/.hermes/config.yaml`
- Restart Hermes Agent after config changes
- Fall back to Mode B (crawl4ai) or Mode C (manual input)

### SSO session expired
- Run Playwright headed: temporarily remove `--headless` from MCP args
- Navigate to the ticket URL, user re-authenticates
- Session saved, restore `--headless` if desired

### WSL display issues (no GUI for headed browser)
- WSLg should be enabled by default on recent WSL2
- Alternative: use `--headless` mode + manually export cookies from host browser
- Alternative: run a separate setup script on Windows host to populate `user-data-dir`

## Workflow

### Phase 1: Extract & Parse

1. Extract requirement text from the source (URL via MCP/crawl4ai, or manual).
2. Identify:
   - **Platform + version** — mandatory gate. Do not proceed without it.
   - **Feature name** — derive from title or summarize.
   - **Raw description** — preserve original text for traceability.
3. If the requirement references other documents/systems, note them as context.

### Phase 2: Understand & Decompose

Analyze the requirement and produce:

#### 2.1 Core Problem Statement
One sentence: "解决什么问题，为谁解决"

#### 2.2 Actors / Roles
| 角色 | 职责 | 本次需求涉及 |

#### 2.3 Functional Breakdown
Break the requirement into discrete functional items. Each item:

```
### F-<NN>: <功能名称>

- **描述**: what this feature does, in plain language
- **触发条件**: what causes this feature to activate
- **输入**: what data/user-action triggers it
- **输出**: what the system produces/returns
- **前置条件**: what must be true before this works
- **后置条件**: what becomes true after it executes
- **验收标准**:
  1. Given <precondition>, when <action>, then <expected result>
  2. ...
- **优先级**: P0 / P1 / P2
- **涉及角色**: which actors from 2.2
```

#### 2.4 Constraints & Scope
- Platform version constraints
- Data/performance constraints
- Integration constraints (other systems this must work with)
- Out of scope (explicitly what this does NOT cover)

### Phase 3: Ambiguity Resolution (Human Confirmation Loop)

This is the **most critical phase**. The AI MUST:
1. List every ambiguous or unclear point as a `[待确认]` item.
2. For each ambiguity, provide a **reasoned best guess** and ask the user to confirm or correct.
3. Use `clarify` tool to present ambiguities in batches (no more than 4 at a time).

Example:
> **[待确认-1] 角色权限**: 需求提到"管理员可以审核"，但未明确"管理员"是否包含"超级管理员"和"普通管理员"。建议：仅超级管理员可审核。请确认。
>
> [ ] A. 仅超级管理员  [ ] B. 所有管理员  [ ] C. 其他: ___

**Do not proceed beyond this phase until all `[待确认]` items are resolved.** Each resolved item is recorded with the user's answer.

### Phase 4: Generate Requirements Document

Write the document to `~/.hermes/requirements/<platform>/<feature-name>.md` (adjust path as user specifies):

```markdown
# <Feature Name> 需求文档

> 来源: <ticket URL or "手动输入">
> 目标平台: <platform> <version>
> 文档版本: v1.0
> 最后更新: <date>

## 1. 概述

### 1.1 核心问题
(one-sentence: 解决什么问题，为谁解决)

### 1.2 原始需求
<blockquote>
(preserved original requirement text)
</blockquote>

## 2. 用户与角色

| 角色 | 职责 | 本次需求涉及 |

## 3. 功能拆解

### 3.1 功能清单总览

| 编号 | 功能名称 | 优先级 | 涉及角色 | 简述 |

### 3.2 功能详情

(Each functional item from Phase 2.3, with full acceptance criteria)

## 4. 约束与范围

### 4.1 平台约束
- 目标平台: <platform> <version>
- ...

### 4.2 范围边界
- 包含: ...
- 不包含: ...

## 5. 确认记录

| 编号 | 问题 | AI建议 | 人工确认结果 |
|------|------|--------|-------------|
| 待确认-1 | ... | ... | ... |

## 6. 附录
- 原始需求链接: ...
- 相关文档: ...
```

## Output Checklist

Before considering this phase complete:

- [ ] Platform + version captured
- [ ] Original requirement preserved
- [ ] All functional items have acceptance criteria (Given/When/Then)
- [ ] All `[待确认]` items resolved and recorded
- [ ] Document written to file
- [ ] Summary presented: N functional items, N roles, N confirmations resolved

## Pitfalls

- **Never skip platform version** — every skill downstream needs it. No platform = no analysis.
- **Do not design UI here** — functional items describe WHAT the system does, not HOW the page looks. Page design is the design-phase skill's job.
- **Do not identify APIs here** — API module identification is the design-phase skill's job.
- **Batch confirmations** — don't ask one question at a time. Group 3-4 related ambiguities into one `clarify` call.
- **Preserve original text** — always include the raw requirement in the document. Future readers need traceability.
- **Break down, don't summarize** — a vague requirement of "build user management" should become F-01 through F-08, each testable.
- **MCP tools may have different names** — use `mcp_playwright_*` prefix, but verify actual tool names at runtime. Common names: `browser_navigate`, `browser_snapshot`, `browser_take_screenshot`, `browser_evaluate`.
- **Accessibility snapshots are lossy** — if critical content is missing from the snapshot, fall back to `browser_evaluate` with `document.body.innerText` or extract full HTML.

## Handoff

The requirements document produced here is consumed by:
- **design-phase skill** — takes functional items and produces frontend page specs + backend API module specs
- **plan skill** — can use functional items for project planning

## Portability (Claude Code, Cursor, etc.)

This skill uses Hermes-specific YAML frontmatter (`name`, `description`, `triggers`)
and the Hermes skill loading mechanism (`skill_view`/`skills_list`). To use in other
AI coding tools:

- **Claude Code**: Copy the Markdown body (below the `---` frontmatter line) into
  `CLAUDE.md` or `.claude/skills/requirement-analysis.md`. The triggers and automatic
  loading won't work — you'll need to reference the skill explicitly in your prompt.
- **Cursor**: Same approach — include in `.cursorrules` or reference manually.
- **GitHub Copilot**: Add as a custom instruction file.

The **workflow** (Phase 1→2→3→4) and **output templates** are tool-agnostic and
work in any AI coding assistant.

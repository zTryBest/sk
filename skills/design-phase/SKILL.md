---
name: design-phase
description: >
  Take a requirements document and produce a detailed design: microservice
  topology, component/API matching, frontend page specs, gateway REST +
  Feign interfaces, database schema, and internal protocols. Each layer
  requires human confirmation. Knowledge base accumulates baseline (not
  project-specific) interfaces per platform. This skill should be used after
  requirement analysis is complete, when the user says "方案设计" or asks to
  design the system.
---

# Design Phase

## Purpose

Transform a requirements document into actionable design artifacts:

1. Architecture design — microservice topology, service internals, network zones
2. Component matching — identify which microservices are involved (new/modify/reuse)
3. Frontend page design — static initial states, interaction flows, gateway API deps
4. Backend API design — gateway REST APIs + Feign inter-service interfaces
5. Database design — DDL with indexes, partitions, archive strategy
6. Internal protocol design — MQ events, Feign contracts with fallback
7. Detailed design document — consolidated output

## Key Architecture Constraints

- Frontend → Gateway (CAS SSO) → Backend services. Never direct microservice calls.
- Inter-service: BIC+RestTemplate (internal token) or Consul+Feign. Never direct REST.
- Component = Microservice (not frontend UI component).
- Third-party systems: private protocol → Adapter pattern.

## Knowledge Base Policy

Only baseline platform capabilities go into `~/.claude/knowledge/<platform>/`.
Project-specific (定制) interfaces stay in the design document only.

**Goes into KB:** baseline microservice inventory, baseline Feign/MQ/REST interfaces.
**Does NOT go into KB:** new custom microservice interfaces, project-specific REST APIs.

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

- `product_composition` — 在 Phase 3 中用于查询平台微服务清单（"产品构成"模块）
- `component_api` — 在 Phase 3 中用于查询各微服务的 API 契约
- 如果 URL 为空 → 跳过在线查询，使用已有 KB + 人工补充

## Workflow

### Phase 1: Load Context

1. Read requirements doc → extract platform, version, functional items, roles.
2. Load existing KB: `~/.claude/knowledge/<platform>/microservices.md`, `interfaces.md`.
3. Confirm architecture constraints (gateway type, registry protocol).

### Phase 2: Architecture Design

#### 2.1 System Architecture
Draw ASCII microservice topology: Gateway → Services (existing + new, each marked)
→ MQ/Registry → External. For each integration: direction, data, protocol, failure mode.

#### 2.2 Software Architecture
Draw layered internal architecture per new microservice: API → Business → Adapter
(private protocol) → Data → Infrastructure. Note key patterns: Adapter, Feign+Fallback,
Event-driven.

#### 2.3 Network Architecture
Three zones:
- Zone 1: Browser → Gateway (HTTPS + CAS)
- Zone 2: Service ↔ Service (Feign/Registry, internal)
- Zone 3: Service → External (private protocol)

Document protocol, auth, encryption, timeout per path.

#### 2.4 Confirmation
Use AskUserQuestion to confirm all three architecture views.

### Phase 3: Microservice Component Matching

#### 3.1 Query Knowledge Sources

Follow the discovery workflow in `references/component-api-discovery.md`.

**在线查询（URL 已配置时）：**

Component Discovery (see reference for detailed MCP steps):
1. Navigate to `product_composition` URL → search for the platform → click result card.
2. Locate the **"产品构成"** module → extract all microservices.

API Discovery (see reference for detailed MCP steps):
1. Navigate to `component_api` URL → search for each component by name.
2. Hover → click "查看详情" → select version (latest ≤ target).

**离线模式（URL 未配置时）：**
Fall back to `~/.claude/knowledge/<platform>/` KB + manual input.

If crawled docs are unclear (missing examples, ambiguous types):
1. Ask: "是否有准确的请求/响应示例？" → use as authoritative source.
2. Ask: "是否有测试环境可直接调用接口？" → use curl to call and capture real response.
3. Neither → mark as [待确认], proceed with best-effort design.

Key interactions: search → click product card → locate "产品构成" module;
search component → hover to reveal "查看详情" button → click → select version.

#### 3.2 Matching Tables

Microservice matching:
```
| Requirement | Microservices Involved | Type | Notes |
```

Interface matching:
```
| Interface | Caller→Provider | Method | Type | Notes |
```

#### 3.3 Confirmation
Use AskUserQuestion. User can correct any mismatch.

#### 3.4 Accumulate to KB
Only baseline interfaces → `~/.claude/knowledge/<platform>/interfaces.md`.

### Phase 4: Frontend Page Design

Key constraint: pages call gateway APIs only, never microservices directly.

For each page:
```
### Page: <name>
- Route: /path
- Type: page | modal | tab | drawer

#### Static Initial State
- Layout: header / filter / content / pagination
- Component inventory (every UI element with initial visibility/enabled/default)
- Empty/loading/error states

#### Interaction Flow
1. Load → API call → render
2. User action → validation → API call → feedback
3. Error handling per case

#### API Dependencies (all via gateway)
```

Confirm all pages with user.

### Phase 5: Backend API Design

#### 5.1 Gateway REST APIs
Each endpoint: method, path, routes-to microservice, auth, request/response, errors, logic.

#### 5.2 Feign Inter-service Interfaces
Each interface: caller→provider, @FeignClient config, signature, fallback, timeout, retry.

Present two inventory tables. Confirm with user.

### Phase 6: Database Design

**MUST ask user first:** "What database type?" (MySQL/PostgreSQL/Oracle/other).

Use database-specific DDL syntax.
Mark each table as NEW or EXTEND (existing table + columns).
Design partitions for tables > 100K rows/month with archive strategy.

Confirm with user.

### Phase 7: Internal Protocol Design

MQ event contracts (payload, ACK, idempotency, dead-letter).
Feign interface contracts (full fallback + timeout + circuit-breaker detail).

### Phase 8: Generate Design Document

Output to: `~/.claude/outputs/design/<platform>/<feature-name>-设计文档.md`

## Pitfalls

- Architecture first — confirm before jumping to pages/APIs.
- Frontend → Gateway only. No direct microservice calls from pages.
- Service → Service via BIC+RestTemplate or Consul+Feign. No direct REST.
- Ask database type before writing DDL.
- KB only for baseline interfaces, not project-specific ones.
- Every Feign interface must define a Fallback.
- **Never guess or fabricate API information.** If an API cannot be found or is uncertain, stop and ask the user. Do not invent interfaces, parameters, or response formats.

## What's Next

After design is complete:

```
方案设计 → Pencil Round 2 (高保真设计稿)
      ↓
    开发 (后端编码)
```

- **Pencil Round 2** — generate high-fidelity .pen designs + PNG exports from Phase 4
  frontend page specs (static initial state, component inventory, interaction flow,
  API dependencies). Use the `pencil` skill, Round 2 mode.

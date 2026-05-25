# Session Insights: Key Corrections from PVIC SMS Project

> Captured: 2026-05-25. Critical mid-session corrections that transformed the
> design-phase approach. Future sessions should not need to rediscover these.

## Correction 1: "组件" = Microservices, NOT Frontend UI

The initial design-phase approach treated "组件" as frontend UI components
(FormPanel, DataTable, ModalForm). The correct interpretation: "组件" means
backend microservices.

**Impact:**
- Phase 3 "Component Matching" matches microservices (e.g. 告警服务, 用户服务), not UI widgets
- "API matching" = inter-service Feign interfaces, not frontend-facing REST
- Architecture diagrams show microservice topology, not UI component trees

## Correction 2: Frontend NEVER Calls Microservices Directly

Frontend → Gateway (CAS SSO) → Backend services. The frontend does not
know about backend microservice addresses. All frontend API calls go
through the company's self-built gateway.

**Impact:**
- Frontend page design: "API Dependencies" section lists gateway paths only
- Network architecture: explicit gateway layer
- Phase 5 split into: Gateway REST APIs (frontend-facing) vs Feign interfaces (service-to-service)

## Correction 3: Inter-Service Calls Use Feign/Registry, NOT Direct REST

Backend services communicate via Feign (declarative HTTP client) or
the company's registry protocol. Not direct REST calls between services.

**Impact:**
- Phase 5.2: Feign interface design template with @FeignClient config
- Every Feign interface must define: Fallback, timeout, retry strategy
- Circuit-breaker consideration (Sentinel/Hystrix via registry)

## Correction 4: Database Type MUST Be Asked Before DDL

Never assume MySQL. Different databases have completely different DDL syntax
(AUTO_INCREMENT vs SERIAL, TINYINT vs SMALLINT, JSON vs JSONB, ON UPDATE vs
triggers).

**Impact:**
- Phase 6 starts with: "Ask user: what database type?"
- DDL templates show database-specific syntax
- PostgreSQL-specific features: JSONB, conditional unique indexes,
  RANGE partitioning, updated_at triggers

## Correction 5: Knowledge Base = Baseline Only

Only platform baseline interfaces belong in the knowledge base. Project-specific
custom interfaces stay in the design document only.

**Examples:**
- GOES into KB: UserServiceClient.getPhoneNumbers (baseline user service capability)
- Does NOT go into KB: SmsServiceClient.getSmsBinding (project-specific new service)

## Correction 6: Scaffold Generation Belongs in Development, Not Design

The design phase focuses on architecture and contracts. Scaffold download/
extraction happens during the development/coding phase.

**Impact:**
- Removed scaffold download from design-phase skill
- Design document specifies architecture constraints without executing the download

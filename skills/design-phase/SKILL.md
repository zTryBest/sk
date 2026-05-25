---
name: design-phase
description: >
  Takes a requirements document and produces a detailed design: system/software/
  network architecture, microservice component matching (with human confirmation),
  frontend page specs, gateway REST API + inter-service Feign/registry interfaces,
  database schema, and internal protocols. Each layer requires human confirmation.
  Knowledge base accumulates per project. Output feeds the development phase.
triggers:
  - User says "方案设计" or "design phase" or "详细设计"
  - A requirements document has been completed and user wants to proceed
  - User asks to design APIs, database, or frontend pages
---

# Design Phase / 方案设计

## Purpose

Take the structured requirements document (from `requirement-analysis` skill)
and transform it into actionable design artifacts:

1. **Architecture design** — system architecture (微服务拓扑), software architecture
   (服务内部分层 + Feign/注册中心通信), network architecture (网关路由 + 内外部通信)
2. **微服务组件匹配** — 查询平台微服务知识库，AI 判断涉及哪些微服务、哪些需要新增/
   修改，人工确认，确认结果积累到知识库
3. **前端页面设计** — 静态初始状态、交互流程、UI 元素清单
4. **后端接口设计** — 网关对外 REST API + 微服务间 Feign/注册中心接口
5. **数据库设计** — 表结构、字段、关系、索引
6. **内部协议设计** — MQ 事件、Feign 接口契约
7. **详细设计文档** — 以上全部汇总，含"复用/扩展/新增"标记

**This is the most architecture-heavy phase. Every design decision must be confirmed
by the user before being finalized.**

## Key Architecture Constraints

本平台有特定的架构约束，设计时必须遵守：

1. **前端不直连后端微服务** — 前端 → 公司自研网关 (CAS SSO) → 后端服务
2. **后端服务间两种调用方式**：
   - **BIC + RestTemplate** — 通过 BIC 注册中心寻址，RestTemplate 发起 HTTP 调用，内部 Token 机制鉴权
   - **Consul + Feign** — 通过 Consul 服务发现，Feign 声明式调用
3. **组件 = 微服务** — 本平台语境下"组件"指后端微服务，非前端 UI 组件
4. **第三方系统通过私有协议对接** — 适配器模式封装

## Knowledge Base Philosophy

Knowledge bases only store **platform baseline capabilities** — reusable across all projects.
Project-specific (定制) artifacts stay in the design document only.

**What goes into knowledge base:**
- 平台基线微服务清单和职责
- 基线微服务对外暴露的 Feign 接口 / MQ 事件 / REST API
- 数据库设计规范

**What does NOT go into knowledge base:**
- 本次新建的定制微服务的内部接口（如 SmsServiceClient.getSmsBinding）
- 本次项目特有的 REST API（如 /api/v1/sms/*）
- 项目特有的数据表结构

Rationale: 基线接口（如 UserServiceClient.getPhoneNumbers）其他项目也会用到，
定制接口只对当前项目有意义。

Knowledge bases are organized by platform at `docs/knowledge/<platform>/`:
- `microservices.md` — 平台基线微服务清单
- `interfaces.md` — 基线微服务对外接口契约
- `database.md` — 数据库规范

Each project's confirmed **baseline** matches are appended to these files.

## Workflow

### Phase 1: Load Context

1. Read the requirements document. Extract platform, version, functional items, roles.
2. Load existing knowledge bases if available.
3. Confirm architecture constraints with user (网关类型、注册中心协议、Feign 版本等).

### Phase 2: Architecture Design

#### 2.1 System Architecture (微服务拓扑)

Show the microservice topology — which services exist, which are new, and how they communicate.

The diagram must distinguish three communication paths:
- **前端 → 网关**: HTTPS + CAS SSO
- **网关 → 微服务**: 内部路由转发
- **微服务 ↔ 微服务**: Feign / 注册中心协议
- **微服务 → 外部**: 私有协议 / HTTPS

Template:
```
                      ┌─────────────────────────┐
                      │   公司自研 API 网关        │
                      │   + CAS SSO 认证          │
                      └──────┬──────────────────┘
                             │ (内部路由)
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ 告警服务      │  │ 用户服务      │  │ 短信服务(NEW) │
  │ (existing)   │  │ (existing)   │  │              │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                 │
         └────────┬────────┘                 │
                  │                          │
          ┌───────┴───────┐                  │
          │ 注册中心/MQ    │←─────────────────┘
          │ (existing)    │  Feign/事件
          └───────────────┘
                                          │ 私有协议
                                          ▼
                                 ┌──────────────────┐
                                 │ 第三方短信平台     │
                                 │ (私有协议)        │
                                 └──────────────────┘
```

For each service-to-service integration, document:
- 调用方 → 提供方
- 通信方式: BIC+RestTemplate / Consul+Feign / MQ事件
- 数据和方向
- 故障降级策略

#### 2.2 Software Architecture (服务内部分层)

Each microservice's internal layered architecture:

```
┌──────────────────────────────────────────────┐
│            短信服务 (SMS Service)              │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  API 层 (对外暴露)                       │  │
│  │  - REST Controller (供网关调用)          │  │
│  │  - Feign Interface (供其他服务调用)       │  │
│  │  - MQ Consumer (事件消费)               │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │  业务逻辑层 (Service)                    │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │  适配器层 (私有协议封装)                   │  │
│  │  SmsProviderAdapter → 各平台Adapter     │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │  数据访问层 (Repository/Mapper)          │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

Key design patterns:
- **适配器模式** — 封装私有协议差异
- **Feign 接口 + 降级** — 服务间调用，需定义 Fallback
- **事件驱动** — 告警触发通过 MQ 解耦

#### 2.3 Network Architecture (网络通信)

Three communication zones:

**Zone 1: 前端 → 后端（经网关）**
```
浏览器 ──HTTPS/CAS──→ 公司网关 ──内部路由──→ 短信服务 REST API
```
- 前端只和网关通信，不知道后端微服务地址
- 网关负责 CAS 认证、路由、限流

**Zone 2: 服务间（Feign/注册中心）**
```
短信服务 ──Feign/注册中心──→ 用户服务 (查手机号)
告警服务 ──Feign/注册中心──→ 短信服务 (查绑定配置)
告警服务 ──MQ事件─────────→ 短信服务 (告警触发)
```
- 通过注册中心发现服务地址，Feign 声明式调用
- 需要定义 Fallback 降级逻辑

**Zone 3: 外部通信（私有协议）**
```
短信服务 ──私有协议──→ 第三方短信平台
```
- 适配器封装协议差异
- 连接池 + 心跳 + 重连

#### 2.4 Architecture Confirmation

Use `clarify` to confirm all three architecture views.

### Phase 3: 微服务组件匹配

**This is the critical gate. Do not skip.**

#### 3.1 概念说明

本平台语境下：
- **组件 = 微服务** (e.g. 告警服务、用户服务、短信服务)
- **API = 微服务间接口** (Feign 接口 / 注册中心 RPC 接口 / MQ 事件)
- 前端的"页面"是 Phase 4 的内容，不在此阶段

#### 3.2 查询知识来源

Follow the discovery workflow documented in `references/component-api-discovery.md`.

Before starting, ask the user for the internal URLs:
- 组件信息内网地址 (for discovering platform microservices)
- 接口信息内网地址 (for discovering inter-service APIs)

**If URLs are provided:**

Component Discovery (see reference for detailed MCP steps):
1. Navigate to the components URL → search for the platform → click result card.
2. Enter the product detail page → locate the **"产品构成"** module.
3. This module contains ALL microservices that make up the platform.
4. Extract component names, descriptions, and statuses.

API Discovery (see reference for detailed MCP steps):
1. Navigate to the API docs URL → search for each component by name.
2. **Hover** over the component tag to reveal the **"查看详情"** button.
3. Click "查看详情" → select version (latest ≤ target platform version).
4. Extract all API interfaces: method, path, request/response.

**If URLs are not provided:**
Fall back to loading existing knowledge base from `~/.hermes/knowledge/<platform>/`,
supplemented by user manual input.

**If internal docs are unclear or incomplete:**
When the crawled API documentation lacks sufficient detail (missing request/response
examples, unclear parameter types, ambiguous field descriptions):

1. Ask the user: "接口文档说明不够清晰，是否有准确的请求/响应示例？"
   If yes → use the user-provided examples as the authoritative source.

2. If no examples available, ask: "是否有测试环境可以直接调用接口获取响应？"
   If yes → use `curl` or `terminal` with `*** to call the API endpoint directly and capture the real response. Use the response as the API specification.

3. If neither is available → mark the unclear APIs as `[待确认]` in the design document
   and proceed with best-effort design based on available information.

#### 3.3 AI Matching Proposal

```
## 微服务组件匹配

| 需求功能 | 涉及微服务 | 类型 | 说明 |
|----------|-----------|------|------|
| F-01 短信配置 | 短信服务 (NEW) | 新增 | 新服务 |
| F-02 模板管理 | 短信服务 (NEW) | 新增 | — |
| F-03 告警绑定 | 告警服务 + 短信服务 | 修改+新增 | 告警服务增加绑定接口 |
| F-04 短信发送 | 告警服务 + 短信服务 + 用户服务 | 修改+新增+复用 | MQ事件+Feign查手机号 |
| F-05 生命周期 | 短信服务 (NEW) | 新增 | 内部逻辑 |
| F-06 发送记录 | 短信服务 (NEW) | 新增 | — |

## 微服务间接口匹配

| 接口 | 调用方→提供方 | 通信方式 | 类型 | 功能 |
|------|-------------|----------|------|------|
| alert.triggered | 告警服务→短信服务 | MQ | 新增 | 告警事件通知 |
| getUserPhones | 短信服务→用户服务 | Feign | 复用/新增 | 批量查手机号 |
| getSmsBinding | 告警服务→短信服务 | Feign | 新增 | 查询短信绑定配置 |
```

#### 3.4 Human Confirmation (MANDATORY)

Use `clarify` to present and confirm.

#### 3.5 Accumulate to Knowledge Base

After confirmation, append **only baseline components/interfaces** to the knowledge base.
Do NOT add project-specific (定制) interfaces.

**Add to knowledge base:**
- 新发现的平台基线微服务能力（如发现用户服务有 getPhoneNumbers 接口）
- 架构约束（数据库类型、通信协议等）

**Do NOT add:**
- 本次新建的定制微服务及其接口
- 本次项目特有的 REST API

### Phase 4: Frontend Page Design

For each functional item that has a UI, design the page.

**Key constraint: 前端页面只调用网关，不直接调用微服务。**
因此页面设计中的"依赖 API"均为网关路径。

#### 4.1 Page Identification

Map functional items to pages. Mark each as NEW or EXTEND.

#### 4.2 Page Design Template

```
### Page: <Page Name>
- Route: /<path>
- Page Type: 独立页面 | 弹窗 | Tab页 | 抽屉

#### Static Initial State (页面首次加载时的状态)
- Layout: [布局描述]
- Component Inventory (页面上所有UI元素):
  | UI元素 | 类型 | 初始状态 | 说明 |
  |--------|------|----------|------|
  | 平台类型 | 下拉框 | 默认"请选择" | ... |
  | AccessKey | 输入框 | 空 | 密码类型 |
  | 测试连接 | 按钮 | 可点击 | ... |
- Default/Empty States: [空数据/Loading/错误]

#### Interaction Flow
1. 页面加载 → 调网关 API → 回填
2. 用户操作 → 校验 → 调网关 API → 反馈
3. 异常处理

#### API Dependencies (均通过网关)
- GET /api/v1/sms/config
- POST /api/v1/sms/config/test
- PUT /api/v1/sms/config
```

#### 4.3 Human Confirmation

### Phase 5: 后端接口设计

接口分为两类，需要分别设计：

#### 5.1 网关对外 REST API (前端调用)

前端通过网关调用，网关路由到对应微服务。

```
### <METHOD> /api/v1/<path>

- 网关路由: 网关 → 短信服务
- 功能: ...
- 权限: <CAS角色>

- Request: { ... }
- Response: { "code": 0, "data": { ... } }
- Error: 400/401/403/500

- 业务逻辑: ...
- 关联功能: F-XX
```

#### 5.2 微服务间接口 (BIC+RestTemplate / Consul+Feign)

服务间通过两种方式调用：

**方式一: Consul + Feign（声明式调用）**
```java
@FeignClient(name = "user-service", path = "/internal/user",
             fallback = UserServiceClientFallback.class)
public interface UserServiceClient {
    @PostMapping("/phones")
    Result<Map<String, String>> getPhoneNumbers(@RequestBody List<String> userIds);
}
```

**方式二: BIC + RestTemplate（寻址调用）**
```java
// BIC 寻址获取服务地址
String userServiceUrl = bicRegistry.resolve("user-service");
// RestTemplate + 内部 Token 发起调用
HttpHeaders headers = new HttpHeaders();
headers.set("X-Internal-Token", internalToken);
ResponseEntity<Result> resp = restTemplate.exchange(
    userServiceUrl + "/internal/user/phones", HttpMethod.POST,
    new HttpEntity<>(userIds, headers), Result.class);
```

对于每个服务间接口，需要指定使用哪种调用方式，并定义：
- Fallback 降级逻辑（超时/不可用时返回什么）
- 超时配置
- 重试策略
             fallback = UserServiceClientFallback.class)
public interface UserServiceClient {

    // 批量查询用户手机号
    @PostMapping("/phones")
    Result<Map<String, String>> getPhoneNumbers(@RequestBody List<String> userIds);
}
```

对于每个 Feign 接口，需要定义：
- Fallback 降级逻辑（超时/不可用时返回什么）
- 超时配置
- 重试策略

#### 5.3 API Inventory

分别列两份清单：
- 网关 REST API 清单
- 微服务间 Feign 接口清单

### Phase 6: Database Design

**Before designing tables, MUST ask the user:**
> 平台使用的数据库类型是什么？(MySQL / PostgreSQL / Oracle / 其他)

Different databases have different syntax (AUTO_INCREMENT vs SERIAL, TINYINT vs SMALLINT,
JSON vs JSONB, COMMENT syntax, ON UPDATE triggers, partitioning strategy). Do not assume.

Design each table with:
- Database-specific DDL syntax
- Table ownership (which microservice's database)
- 复用/扩展/新增标记
- Indexes for query patterns
- Partitioning strategy for large tables (预估 > 10万/月 要分区)
- Archive/cleanup strategy for fast-growing tables

### Phase 7: Internal Protocol Design

#### 7.1 MQ Event Contracts

#### 7.2 Feign Interface Contracts (Fallback + 超时 + 重试)

### Phase 8: Generate Design Document

Output: `~/.hermes/design/<platform>/<feature-name>-设计文档.md`

## Output Checklist

- [ ] Architecture designed and confirmed (微服务拓扑 + 服务内分层 + 三区网络)
- [ ] 微服务组件匹配 confirmed → accumulated to knowledge base
- [ ] Frontend pages: static initial state + interaction flow + 网关 API 依赖
- [ ] 网关 REST APIs: endpoints, request/response, error codes
- [ ] 微服务间 Feign 接口: interface 定义 + Fallback + 超时
- [ ] Database: CREATE TABLE per microservice
- [ ] All confirmation gates passed
- [ ] Design document written

## References

- `references/session-insights.md` — 首次实战（PVIC 短信项目）中用户纠正的 6 个关键设计偏差。新项目开始前务必阅读，避免重蹈覆辙。

## Pitfalls

- **前端只走网关** — 页面设计中 API 依赖必须全部是网关路径
- **服务间走 Feign/注册中心** — 不设计直接的 REST 跨服务调用
- **组件 = 微服务** — Phase 3 匹配的是微服务，不是前端 UI 组件
- **Feign 必须定义 Fallback** — 每个 Feign 接口都要有降级逻辑
- **适配器封装私有协议** — 第三方对接的协议差异在适配器层消化
- **知识库累积** — 每次确认后追加到知识库，下次设计直接复用
- **禁止猜测接口** — 找不到或不确定的接口，必须询问用户。禁止编造接口、参数或响应格式。一个错误的接口契约会让下游所有开发工作作废。

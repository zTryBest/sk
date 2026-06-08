---
name: backend-coding
description: >
  当 BackendAgent 需要根据 `artifacts/04_plan.json` 和 `artifacts/02_solution.json` 完成后端编码时使用。
  本 Skill 负责脚手架源码获取、Java Web 后端实现、编译测试和 `artifacts/05_backend_report.md` 输出；
  不负责需求、方案、前端、测试总控或流程调度。
---

# 后端编码 Skill

本 Skill 说明“后端编码怎么做”。BackendAgent 负责调用本 Skill，Orchestrator 负责阶段顺序和 Human Gate。

## 阶段边界

应该做：
- 读取 `artifacts/04_plan.json`。
- 读取 `artifacts/02_solution.json` 中的后端接口、baseline API、数据模型和外部集成设计。
- 通过 HTTP 脚手架服务生成 Java Web 源码，解压到 `workspace/backend/`。
- 在脚手架源码上完成后端编码。
- 运行可用的编译和测试命令。
- 输出 `artifacts/05_backend_report.md`。

禁止做：
- 不修改 `artifacts/01_requirement.json`。
- 不修改 `artifacts/02_solution.json`。
- 不新增需求或变更方案结论。
- 不写前端代码。
- 不跳过已有脚手架结构重写项目。
- 不调度其他 Agent。

## 输入

必须读取：

```text
artifacts/04_plan.json
artifacts/02_solution.json
```

可以读取：

```text
artifacts/01_requirement.json
```

仅用于理解业务上下文，不能修改需求和方案。

## 脚手架服务协议

当前脚手架服务通过 HTTP 调用，尚未封装为 MCP。优先使用固定脚本：

```text
python scripts/scaffold_client.py --url http://<ip>:8888 --component-id <组件标识> --version <组件版本> --service-id <服务标识> --output-dir workspace/backend
```

`--url` 可以是服务基址 `http://<ip>:8888`，也可以是完整端点 `http://<ip>:8888/v1/frame/frame`。

固定协议：
- 请求路径：`http://<ip>:8888/v1/frame/frame`
- 请求方式：`POST`
- 请求头：`Content-Type: application/json; charset=utf-8`
- 响应内容：zip 文件流

默认请求体示例：

```json
{
  "configInfo": [
    {"label": "database", "value": "postgresql", "has": true},
    {"label": "cache", "value": "jedis", "has": true},
    {"label": "mq", "value": "kafka", "has": true},
    {"label": "reference", "value": "bic,bic;bic,xauthc;bic,xauthz", "has": true},
    {"label": "javaVersion", "value": "11", "has": true},
    {"label": "basicFeatures", "value": "cas", "has": true},
    {"label": "controller", "value": "", "has": false}
  ],
  "version": "2.0-RELEASE",
  "packageName": "com.aries.jc.sc",
  "componentId": "patpps",
  "serviceId": ["patpps"],
  "port": 17000,
  "errorCode": "0x160a",
  "dependenciesVersion": "3.4.3",
  "email": "z@cn",
  "author": "z"
}
```

`componentId`、`version`、`serviceId` 必须来自 `04_plan.json`、`02_solution.json`、环境变量或 Human Gate 决策。缺少时不要使用示例值猜测，返回 Human Gate 问题。

正确获取 zip 后，脚本会安全解压到 `workspace/backend/`，并生成 `scaffold-manifest.json`。其中 `source_dir` 是真实后端源码目录。

## 编码流程

1. 读取计划和方案。
2. 获取或定位后端脚手架源码。
3. 识别 Maven/Gradle、包名、Controller、Service、Repository、DTO、Entity、Config 和 Test 目录。
4. 按 `04_plan.json` 中后端任务逐项实现。
5. 对 baseline API 调用按 `02_solution.json.selected_baseline_apis` 的契约实现，不猜接口。
6. 实现错误码、参数校验、权限、日志、审计、重试、fallback 和测试点。
7. 运行可用命令，例如 `mvn test`、`./mvnw test`、`gradle test` 或 `./gradlew test`。
8. 自动修复编译或测试失败，最多 3 轮。
9. 输出后端报告。

## 输出

必须输出：

```text
artifacts/05_backend_report.md
```

报告包含：
- 源码目录。
- 脚手架请求摘要。
- 完成的后端任务。
- 修改文件清单。
- Gateway API 实现情况。
- baseline API 调用实现情况。
- 数据库或配置变更。
- 编译和测试命令及结果。
- 未完成项和风险。

不要把完整源代码粘进报告。

## 完成标准

只有满足以下条件，BackendAgent 才能声明完成：
- 已读取 `04_plan.json` 和 `02_solution.json`。
- 后端源码位于 `workspace/backend/`。
- 已完成计划中的后端任务，或明确记录无法完成的原因。
- 已运行可用编译/测试命令。
- `artifacts/05_backend_report.md` 已写入。

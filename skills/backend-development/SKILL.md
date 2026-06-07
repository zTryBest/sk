---
name: backend-development
description: >
  在方案设计完成后执行后端编码阶段。用于根据 design-handoff.json 和 Java Web 脚手架源代码完成后端实现、编译、测试和交接；
  支持通过 HTTP 脚手架服务按定制组件标识和版本生成源码。workflow-orchestrator 以 worker_mode 调度时必须使用本 skill。
---

# Backend Development

本 skill 负责后端编码阶段：读取方案设计产物，生成或定位 Java Web 脚手架，在脚手架源码上完成后端实现，并输出可验证的机器交接文件。

## 输入

优先读取：

- `workflow-state.json`
- `decisions.jsonl`
- `worker-checkpoint.json`
- `external-result.json`
- 上一阶段 `design-handoff.json`
- 方案设计文档 `design-doc.md`

脚手架服务配置来源按优先级读取：

1. `workflow-state.json.backend_scaffold` 或 `workflow-input.json.backend_scaffold`
2. 环境变量 `SCAFFOLD_SERVICE_URL`、`SCAFFOLD_COMPONENT_ID`、`SCAFFOLD_COMPONENT_VERSION`
3. `design-handoff.json.product.component_overrides.backend_scaffold`
4. `design-handoff.json.product.product_id` 和 `product_version`

如果缺少脚手架服务 URL、组件标识或组件版本，写 `pending-questions.json` 和 `worker-result.json(status=NEED_USER_INPUT)`，不要猜。

## 默认执行流程

1. 读取 `references/worker-mode.md` 和 `references/output-contracts.md`。
2. 读取并校验 `design-handoff.json`，确认 `source.design_status=final` 且没有待确认设计项。
3. 生成或定位 Java Web 脚手架源码。
4. 扫描项目结构，识别 Maven/Gradle、包名、Controller/Service/Repository/DTO/entity/config/test 目录。
5. 从 `design-handoff.json` 提取基线 API 复用、定制实现、外部集成、错误处理和测试点。
6. 在脚手架源码上实现后端代码。不要重写脚手架无关结构，不做大范围格式化。
7. 运行可用的编译和测试命令，例如 Maven/Gradle wrapper、`mvn test`、`gradle test`。
8. 自动修复编译/测试失败，最多 3 轮。
9. 写 `backend-code-result.json` 和 `backend-validation.json`，再写 `worker-result.json(status=STAGE_COMPLETED)`。

## SubAgent 使用

编码阶段可以使用 worker 内 subAgent，但必须由当前 worker 统一决策和落盘。

- `backend-code-map`：只读，扫描脚手架目录、依赖、包结构和测试命令。
- `backend-implementation-reviewer`：只读，审查实现是否覆盖设计、是否有明显编译/契约风险。
- `backend-test-reviewer`：只读，分析测试失败、建议修复方向。

不要让多个 subAgent 同时修改同一个文件。真正写文件由当前 worker 或单一明确的实现子任务完成；worker 最终负责汇总、运行测试、写 handoff 和 result。

## HTTP 脚手架服务

当前脚手架服务尚未封装进 MCP，先通过 HTTP 调用。worker 必须优先使用本 skill 的固定脚本：

```text
python backend-development/scripts/scaffold_client.py --url http://<ip>:8888 --component-id <组件标识> --version <组件版本> --service-id <服务标识> --output-dir <工作目录/scaffold>
```

`--url` 可以是服务基址 `http://<ip>:8888`，也可以是完整端点 `http://<ip>:8888/v1/frame/frame`；脚本会规范化到完整端点。响应必须是 `.zip` 文件流，脚本会安全解压到 `--output-dir`，并写入 `scaffold-manifest.json`，其中 `source_dir` 是后续编码的 Java 源码目录。

固定请求协议：

- 请求路径：`http://<ip>:8888/v1/frame/frame`
- 请求方式：`POST`
- 请求头：`Content-Type: application/json; charset=utf-8`
- 响应内容：zip 文件流

默认请求体：

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

`componentId`、`version`、`serviceId` 必须来自 `workflow-state.json.backend_scaffold`、`workflow-input.json.backend_scaffold`、环境变量或设计交接，缺少时不要使用示例值猜测。`packageName`、`port`、`errorCode`、`dependenciesVersion`、`configInfo` 等参数可以按配置覆盖示例默认值。需要完全自定义时，使用 `--request-json <path>` 传入精确 JSON。

如果缺少服务 IP/URL，写 `worker-checkpoint.json`、`pending-questions.json` 和 `worker-result.json(status=NEED_USER_INPUT)`。如果 HTTP 服务不可用、返回内容不是 zip、下载需要登录或外部系统动作，写 `external-action.json`、`worker-checkpoint.json`、`pending-questions.json` 和 `worker-result.json(status=NEED_USER_INPUT)`，等待恢复后从 checkpoint 继续，不要重复已完成的编码步骤。

## 文件写入

- JSON 文件必须用 serializer 写入，并立即 `json.load` 校验。
- 不要在产物目录留下 `_gen_result.py`、`_gen_handoff.py`、`_gen_*.py` 等临时 Python helper。
- 不默认生成 worker prompt/log/metrics 调试文件。
- 不要把完整代码清单写入 `backend-code-result.json`；只记录路径、摘要、测试结果和风险。

## 完成条件

- `backend-code-result.json` 已写入。
- `backend-validation.json.success=true`。
- 已在脚手架源码中完成后端实现。
- 已运行可用的编译/测试命令，或明确记录无法运行的原因。
- `worker-result.json.status=STAGE_COMPLETED`。

## 何时读取 references

- 后端 worker 协议和暂停恢复：读 `references/worker-mode.md`。
- 输出 JSON schema、完成检查和 validator：读 `references/output-contracts.md`。

# Worker Mode

当 prompt、`workflow-state.json` 或用户明确指令包含 `worker_mode: true` 时使用本协议。

## 启动

- 第一动作读取 `workflow-state.json`、`decisions.jsonl`、`worker-checkpoint.json`、`external-result.json`、`design-handoff.json`。
- 如果存在 `worker-checkpoint.json`，且 `decisions.jsonl` 或 `external-result.json` 已满足其 `required_inputs`，必须从 `resume_from` 继续，不要重复 `completed_steps`。
- 不直接向用户提问，不调用 `AskQuestion`。

## 脚手架生成

- 使用 `scripts/scaffold_client.py` 调用 HTTP 脚手架服务，不要临时生成 `_gen_handoff.py`、`_gen_result.py` 或其他一次性 Python 脚本。
- 请求端点固定为 `POST http://<ip>:8888/v1/frame/frame`，请求体使用 `configInfo`、`version`、`packageName`、`componentId`、`serviceId`、`port`、`errorCode`、`dependenciesVersion`、`email`、`author` 结构。
- 响应必须是 zip 文件流；正确响应后解压到工作目录，并以 `scaffold-manifest.json.source_dir` 作为后续 Java 源码目录。
- 脚手架 zip 下载和解压完成后，在 checkpoint 的 `completed_steps` 中记录 scaffold 已完成；恢复时如果 manifest 和 `source_dir` 已存在，不要再次调用脚手架服务。

## 暂停和恢复

- 缺少脚手架服务 URL、组件标识、组件版本、源码输出目录或不可自动判断的服务契约时，先写 `worker-checkpoint.json`，再写 `pending-questions.json`，再写 `worker-result.json(status=NEED_USER_INPUT)`。
- 脚手架 HTTP 服务不可用、响应不是 zip、下载需要登录、人机验证或外部系统操作时，写 `external-action.json`、`worker-checkpoint.json`、`pending-questions.json` 和 `worker-result.json(status=NEED_USER_INPUT)`。
- 用户或主流程完成动作后，新的 worker 必须读取 `decisions.jsonl` / `external-result.json` 并从 checkpoint 继续。

## 编码约束

- 只在脚手架源码目录内修改后端代码。不要修改需求/设计产物，不要改 workflow 状态文件，除非写阶段交接文件。
- 不做无关重构，不大范围格式化，不删除脚手架原有业务无关文件。
- 多个 subAgent 可以读代码，但不要并行写同一文件；父 worker 负责最终落盘。
- 编译/测试失败最多自动修复 3 轮；超过后写 `backend-validation.json(success=false)` 和 `worker-result.json(status=VALIDATION_FAILED)`。
- `backend-code-result.json`、`backend-validation.json`、`pending-questions.json` 和 `worker-result.json` 必须用 JSON serializer 写入，写完立即 `json.load` 校验。
- 不要在产物目录留下 `_gen_result.py`、`_gen_handoff.py`、`_gen_*.py` 等临时 Python helper。

## 完成

- 阶段完成时运行 `scripts/validate_backend.py`，输出 `backend-validation.json`。
- validator 成功后写 `worker-result.json(status=STAGE_COMPLETED)`，包含 `artifact_dir`、`handoff=backend-code-result.json`、`validation=backend-validation.json` 和简短 `summary`。
- 是否进入后续测试/发布阶段由 orchestrator 处理，不由本 skill 自己推进。

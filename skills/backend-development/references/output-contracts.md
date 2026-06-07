# Output Contracts

## 输出文件

后端编码阶段输出保存到当前 workflow 的 `artifact_dir` 或设计交接目录：

```text
backend-code-result.json
backend-validation.json
```

源码目录由脚手架服务生成或由配置指定，通常不在 `requirements/` 下。

## backend-code-result.json

```json
{
  "schema_version": "1.0",
  "source": {
    "design_handoff": "",
    "design_doc": "",
    "generated_at": "",
    "backend_status": "completed|partial|blocked"
  },
  "scaffold": {
    "service_url": "http://<ip>:8888/v1/frame/frame",
    "endpoint": "http://<ip>:8888/v1/frame/frame",
    "component_id": "",
    "component_version": "",
    "manifest": "",
    "request": {
      "configInfo": [],
      "version": "",
      "packageName": "",
      "componentId": "",
      "serviceId": [],
      "port": 0,
      "errorCode": "",
      "dependenciesVersion": "",
      "email": "",
      "author": ""
    },
    "response_summary": {
      "type": "zip_stream",
      "bytes": 0,
      "extracted_files_count": 0
    },
    "source_dir": "",
    "build_tool": "maven|gradle|unknown"
  },
  "implementation_summary": [
    {
      "from_design_item": "",
      "module": "",
      "files_changed": [],
      "summary": "",
      "status": "implemented|partial|skipped",
      "reason": ""
    }
  ],
  "baseline_api_adapters": [
    {
      "from_api": "",
      "method": "",
      "api_path": "",
      "files_changed": [],
      "summary": ""
    }
  ],
  "custom_code": [
    {
      "from_classification": "",
      "module": "",
      "files_changed": [],
      "summary": ""
    }
  ],
  "external_integrations": [
    {
      "from_classification": "",
      "system": "",
      "files_changed": [],
      "summary": ""
    }
  ],
  "build_and_test": {
    "commands_run": [
      {
        "command": "",
        "cwd": "",
        "exit_code": 0,
        "summary": ""
      }
    ],
    "compile_success": false,
    "tests_success": false,
    "failure_summary": ""
  },
  "changed_files": [],
  "open_issues": [],
  "next_steps": []
}
```

## Validator

期望校验命令：

```text
python <backend-development-skill-dir>/scripts/validate_backend.py --handoff <artifact_dir>/backend-code-result.json --output <artifact_dir>/backend-validation.json --project-root <项目根目录>
```

校验成功条件：

- `schema_version` 存在。
- `source.backend_status=completed`。
- `scaffold.source_dir` 存在。
- 如填写 `scaffold.manifest`，该文件必须存在；manifest 中的 `source_dir` 是脚手架解压后的 Java 源码目录。
- `changed_files` 至少包含一个文件，且文件存在。
- `build_and_test.commands_run` 至少包含一个命令。
- `build_and_test.compile_success=true`。
- 如果存在 `open_issues`，validation 仍可成功但会产生 warnings；如果 `backend_status=partial|blocked` 则 validation 失败。

## 完成检查

- [ ] 已读取 `design-handoff.json`。
- [ ] 已通过 `scripts/scaffold_client.py` 获取 zip 响应、解压源码并生成 `scaffold-manifest.json`，或已从 checkpoint 恢复到既有源码目录。
- [ ] 已识别构建工具和测试命令。
- [ ] 已按设计实现后端代码。
- [ ] 已运行编译/测试或记录无法运行原因。
- [ ] 已写 `backend-code-result.json`。
- [ ] 已运行 validator 并生成 `backend-validation.json`。
- [ ] `backend-validation.json.success=true`。

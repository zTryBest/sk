# Backend Scaffold MCP Server

封装公司 SpringBoot 脚手架生成服务, 让 Claude Code 里的 Orchestrator + BackendAgent 通过 MCP 工具直接调用, 无需在 prompt 里拼 URL/解 zip/翻译 configInfo schema。

## 架构

```
┌──────────────────────┐         ┌──────────────────────┐
│ Claude Code (开发机A) │         │ Claude Code (开发机B) │
└──────────┬───────────┘         └──────────┬───────────┘
           │ MCP HTTP                       │ MCP HTTP
           ▼                                ▼
       ┌────────────────────────────────────────────┐
       │ scaffold_mcp.py (局域网共享主机:8001)      │
       │                                            │
       │  - get_form_schema                         │
       │  - validate_params                         │
       │  - generate_backend (内部翻译 LabelDTO)    │
       └────────────────────┬───────────────────────┘
                            │ HTTP
                            ▼
       ┌────────────────────────────────────────────┐
       │ SpringBoot 脚手架服务 (127.0.0.1:8888)     │
       │  GET  /v1/frame/info  → 完整表单 schema    │
       │  POST /v1/frame/frame → 接收 FrameRequest  │
       └────────────────────────────────────────────┘
```

## 部署 (主机侧)

```bash
cd tools/scaffold-mcp
pip install -r requirements.txt

export SCAFFOLD_BACKEND_URL=http://127.0.0.1:8888   # SpringBoot 地址
export MCP_HTTP_PORT=8001                            # MCP server 监听端口
export MCP_HTTP_HOST=0.0.0.0                         # 允许局域网访问

python scaffold_mcp.py
```

后台常驻 (Linux/Mac):
```bash
nohup python scaffold_mcp.py > scaffold_mcp.log 2>&1 &
```

Windows 后台:
```powershell
Start-Process python -ArgumentList "scaffold_mcp.py" -WindowStyle Hidden
```

## 团队成员注册 (每台开发机)

```bash
# <主机IP> 替换为部署机器的局域网 IP
claude mcp add --scope user --transport http scaffold http://<主机IP>:8001/mcp

# 验证
claude mcp list
# 期望看到: scaffold: http://<主机IP>:8001/mcp (HTTP) - ✓ Connected
```

重启 Claude Code 后, `mcp__scaffold__*` 工具即可使用。

## 暴露的工具

| 工具 | 谁调用 | 说明 |
|---|---|---|
| `mcp__scaffold__get_form_schema()` | Orchestrator | 实时拉取 SpringBoot 完整表单 schema (baseInfos + configInfo) |
| `mcp__scaffold__validate_params(packageName, componentId)` | BackendAgent | 提前校验命名格式 |
| `mcp__scaffold__generate_backend(...)` | BackendAgent | 生成脚手架, 内部翻译 configInfo 成 LabelDTO, 解压到 output_path |

## SpringBoot 端契约

### GET /v1/frame/info

返回完整表单 schema, 供 MCP 客户端动态生成用户输入界面:

```json
{
  "code": "0",
  "data": {
    "baseInfos": [
      {
        "label": "组件版本号",
        "value": "version",
        "defaultValue": "2.0-SNAPSHOT",
        "options": [],
        "type": "input",
        "order": 0
      },
      ...
    ],
    "configInfo": [
      {
        "label": "数据库",
        "value": "database",
        "defaultValue": null,
        "options": [
          {"label": "MySQL", "value": "mysql", "children": null},
          {"label": "PostgreSql", "value": "postgresql", "children": null}
        ],
        "type": "radio",
        "order": 0
      },
      ...
    ]
  }
}
```

支持的 type:
- `input` / `number` / `custominput`: baseInfos 中的文本类输入
- `radio`: 单选
- `checkbox`: 多选
- `cascader-multi`: 二级级联多选

### POST /v1/frame/frame

接收 `FrameRequestDTO`, 返回 zip 二进制流。

`configInfo` 字段是 `List<LabelDTO>`, `LabelDTO = {label, has, value}`。MCP server 内部按以下规则翻译:

| schema.type | 翻译规则 | 示例 |
|---|---|---|
| `radio` | 一个 LabelDTO, value = 选中项 | `{label:"database", has:true, value:"mysql"}` |
| `checkbox` | 一个 LabelDTO, value = 逗号拼 | `{label:"mq", has:true, value:"kafka,rabbitMq"}` |
| `cascader-multi` | 一个 LabelDTO, value = "p1,c1;p1,c2" | `{label:"reference", has:true, value:"consul,bic;consul,xauthc"}` |

## 项目级默认配置

LLM 不擅长凭空生成 `port` / `errorCode` / `version` 这类业务字段, 也不能用 `git config` 取 `author/email` (公司没有 git 环境)。建议在每个项目的 `.ai-dev/scaffold-defaults.yaml` 预设:

```yaml
backend:
  # baseInfos (与 SpringBoot DTO 字段名一致, camelCase)
  version: "2.0-SNAPSHOT"
  packageName: "com.aries.jc.sc"
  componentId: "patpps"
  serviceId: ["patpps"]
  port: "17000"
  errorCode: "0x160a"
  dependenciesVersion: "3.4.3"
  email: "niezhenjie@hikvision.com.cn"
  author: "niezhenjie"

  # configInfo (key 用 schema.value 字段名)
  config:
    database: "mysql"
    cache: "redisson"
    mq: ["kafka"]
    reference: [["consul", "bic"]]
    javaVersion: "11"
    basicFeatures: ["cloudstore"]
    controller: []
```

Orchestrator 在编码阶段开头按以下流程填充:
1. 调 `get_form_schema()` 拉取 SpringBoot 实时 schema
2. 对每个未在 yaml 中的字段, 用 `AskUserQuestion` 让用户选择 (radio/checkbox 平铺成选项)
3. 用户答案写回 yaml
4. BackendAgent 后续读 yaml 即可, 不再询问

## 调试

主机侧测试 MCP server 是否正常:
```bash
curl http://127.0.0.1:8001/mcp -X POST -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

期望返回 `get_form_schema` / `validate_params` / `generate_backend` 三个工具。

直接调 SpringBoot info:
```bash
curl http://127.0.0.1:8888/v1/frame/info
```

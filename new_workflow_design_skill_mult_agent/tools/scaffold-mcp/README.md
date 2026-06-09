# Backend Scaffold MCP Server

封装公司 SpringBoot 脚手架生成服务，让 Claude Code 里的 BackendAgent 通过 MCP 工具直接调用，无需在 prompt 里拼 URL/解 zip。

## 架构

```
┌──────────────────────┐         ┌──────────────────────┐
│ Claude Code (开发机A) │         │ Claude Code (开发机B) │
└──────────┬───────────┘         └──────────┬───────────┘
           │ MCP HTTP                       │ MCP HTTP
           ▼                                ▼
       ┌────────────────────────────────────────────┐
       │ scaffold_mcp.py (你的局域网主机:8001)      │
       └────────────────────┬───────────────────────┘
                            │ HTTP
                            ▼
       ┌────────────────────────────────────────────┐
       │ SpringBoot 脚手架服务 (127.0.0.1:8888)     │
       │  POST /v1/frame/frame                      │
       │  GET  /api/options    ← 待 Java 同学添加   │
       └────────────────────────────────────────────┘
```

## 部署 (主机侧)

```bash
cd tools/scaffold-mcp
pip install -r requirements.txt

# 配置 SpringBoot 地址 (默认 http://127.0.0.1:8888)
export SCAFFOLD_BACKEND_URL=http://127.0.0.1:8888
export MCP_HTTP_PORT=8001
export MCP_HTTP_HOST=0.0.0.0   # 允许局域网访问

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

重启 Claude Code 后，`mcp__scaffold__*` 工具即可使用。

## 暴露的工具

| 工具 | 说明 |
|---|---|
| `mcp__scaffold__list_middleware_options()` | 实时从 SpringBoot 拉取可选中间件清单 |
| `mcp__scaffold__validate_params(package_name, component_id)` | 提前校验命名格式 |
| `mcp__scaffold__generate_backend(...)` | 生成脚手架并解压到 output_path，返回结构化元信息 |

## SpringBoot 端约定

### 已有: POST /v1/frame/frame

请求体 `FrameRequestDTO` (用户提供的契约)，返回 zip 文件流。

### 待加: GET /api/options

为了让 LLM 知道 `serviceId` 和 `configInfo` 的合法值，需要 SpringBoot 加一个只读接口:

```http
GET /api/options
→ 200 OK
{
  "service_ids": ["patpps", "patpp2"],
  "middlewares": [
    {"label": "Redis", "value": "redis"},
    {"label": "RocketMQ", "value": "rocketmq"},
    {"label": "Elasticsearch", "value": "es"}
  ]
}
```

未实现时，`list_middleware_options()` 会返回 `NOT_IMPLEMENTED`，agent 仍可调用 `generate_backend` 但选项需硬编码（不推荐）。

## 项目级默认配置

LLM 不擅长凭空生成 `port` / `error_code` / `dependencies_version` 这类业务字段。建议在每个项目的 `.ai-dev/scaffold-defaults.yaml` 预设:

```yaml
backend:
  port: "17000"
  error_code: "0x160a"
  dependencies_version: "3.2.5.RELEASE"
  version: "2.0-SNAPSHOT"
  service_ids: ["patpps"]
```

BackendAgent 调度前由 Orchestrator 读 yaml 注入到 prompt；缺字段时用 AskUserQuestion 询问并写回 yaml。

## 调试

主机侧测试 MCP server 是否正常:
```bash
curl http://127.0.0.1:8001/mcp -X POST -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

期望返回 `list_middleware_options` / `validate_params` / `generate_backend` 三个工具。

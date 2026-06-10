# 后端脚手架获取

## 触发条件

`workspace/backend/` 不存在或为空时, 必须先执行本流程获取脚手架。已有代码时跳过本文件, 直接增量开发。

## 强制路径: mcp__scaffold__* 工具

**禁止用 Bash curl / wget / Invoke-WebRequest 直接拉取 zip。** 公司脚手架走专用 MCP server, 原因:
- SpringBoot 接口字段繁多 (baseInfos 9 项 + configInfo 7 类), LLM 拼 payload 易错
- configInfo 翻译规则(radio/checkbox/cascader-multi 翻译成 LabelDTO)已在 MCP server 内部封装
- zip 流不该进 LLM 上下文

## 三个工具

| 工具 | 用途 | 谁调用 |
|---|---|---|
| `mcp__scaffold__get_form_schema()` | 拉取完整表单 schema (baseInfos + configInfo) | Orchestrator (编码阶段开头, 用于动态生成 AskUserQuestion) |
| `mcp__scaffold__validate_params(packageName, componentId)` | 提前校验命名格式 | BackendAgent |
| `mcp__scaffold__generate_backend(...)` | 生成脚手架并解压到 output_path | BackendAgent |

**BackendAgent 不调用 `get_form_schema`** — Orchestrator 在调度前已用它收集配置, BackendAgent 启动时 yaml 应已就绪。

## yaml 配置 (`.ai-dev/scaffold-defaults.yaml`)

字段名与 info schema 的 value 字段保持一致, 全部 camelCase:

```yaml
backend:
  # baseInfos (info.value 字段名)
  version: "2.0-SNAPSHOT"
  packageName: "com.aries.jc.sc"
  componentId: "patpps"
  serviceId: ["patpps"]               # custominput 类型, 数组
  port: "17000"
  errorCode: "0x160a"
  dependenciesVersion: "3.4.3"
  email: "niezhenjie@hikvision.com.cn"
  author: "niezhenjie"

  # configInfo (info.value 字段名 → 用户的选择)
  config:
    database: "mysql"                          # radio 单选 → string
    cache: "redisson"                          # radio 单选 → string
    mq: ["kafka"]                              # checkbox 多选 → list[str]
    reference: [["consul", "bic"]]             # cascader-multi → list[[parent, child]]
    javaVersion: "11"                          # radio 单选 → string
    basicFeatures: ["cloudstore"]              # checkbox 多选 → list[str]
    controller: []                             # 未选 → 空 list
```

**所有字段由 Orchestrator 在编码阶段开头一次性收集后写入。** BackendAgent 启动时 yaml 就绪。

**禁止 LLM 凭空猜测任何字段** (含 port / errorCode / version / author / email)。**禁止用 git config 取 author/email** (公司没有 git 环境)。

## 调用流程 (BackendAgent 端, 3 步)

### Step 1: 读取 yaml

读 `.ai-dev/scaffold-defaults.yaml`, 提取 `backend.*` 全部字段。

文件不存在或字段缺失 → 在 issues 里记录 `scaffold_defaults_missing: [缺失字段列表]`, REVISE 上报由 Orchestrator 补齐。

### Step 2: 校验命名

调 `mcp__scaffold__validate_params(packageName=yaml.backend.packageName, componentId=yaml.backend.componentId)`:

- `valid: true` → 继续 Step 3
- `valid: false` → 把 errors 写入 issues (category: requirement_gap), 由 Orchestrator REVISE 让用户修正 yaml

### Step 3: 生成脚手架

调 `mcp__scaffold__generate_backend(...)`:

```
mcp__scaffold__generate_backend(
  version             = yaml.backend.version,
  packageName         = yaml.backend.packageName,
  componentId         = yaml.backend.componentId,
  serviceId           = yaml.backend.serviceId,
  port                = yaml.backend.port,
  errorCode           = yaml.backend.errorCode,
  dependenciesVersion = yaml.backend.dependenciesVersion,
  email               = yaml.backend.email,
  author              = yaml.backend.author,
  config              = yaml.backend.config,    # 整个 dict 传过去, MCP server 内部翻译 LabelDTO
  output_path         = "workspace/backend",
  overwrite           = false
)
```

## 处理返回

- `status: "ok"` → 用返回的 `next_steps` 继续后续阶段。在 05_backend_report.md 顶部记录: 脚手架来源 (MCP scaffold) / files_created / main_class / framework_version
- `status: "error"`:

| error_code | 处理 |
|---|---|
| `INVALID_PARAMS` | yaml 字段格式错, issues 上报让 Orchestrator REVISE |
| `TARGET_NOT_EMPTY` | workspace/backend 已有内容。**不要传 overwrite=true 自动覆盖**, issues 上报问用户 |
| `BACKEND_VALIDATION` | SpringBoot 服务端 4xx 校验失败, 把 message 整段贴到 issues |
| `DOWNLOAD_FAILED` | 网络/服务端 5xx, blocking issues |
| `ZIP_CORRUPTED` | 服务端返回 zip 损坏, blocking issues |

## 红线 (违反任一视为任务失败)

1. **禁止 Bash 拉取**: 不允许 `curl` / `wget` / `Invoke-WebRequest` / `python urllib` 直接下脚手架
2. **禁止凭空猜任何字段**: 全部必须来自 yaml, 缺失就 REVISE 不要猜 (公司没有 git 环境, 禁止 `git config` 取 author/email)
3. **禁止跳过 validate_params**: 调 `generate_backend` 前必须先 `validate_params`
4. **禁止自动 overwrite**: `TARGET_NOT_EMPTY` 时必须 issues 上报让用户决定, **不能**自己传 `overwrite=true`
5. **禁止假调用**: `generate_backend` 返回 ok 后必须用 Read/Glob 校验目标路径真有文件落地
6. **禁止 BackendAgent 自己调 get_form_schema**: 那是 Orchestrator 的工作, agent 启动时 yaml 应已就绪

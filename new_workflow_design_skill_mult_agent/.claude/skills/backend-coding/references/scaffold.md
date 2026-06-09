# 后端脚手架获取

## 触发条件

`workspace/backend/` 不存在或为空时，必须先执行本流程获取脚手架。已有代码时跳过本文件，直接增量开发。

## 强制路径：mcp__scaffold__* 工具

**禁止用 Bash curl / wget / Invoke-WebRequest 直接拉取 zip。** 公司脚手架走专用 MCP server，原因：
- SpringBoot 接口字段繁多，LLM 拼 query string 易错
- zip 流不该进 LLM 上下文
- 中间件清单实时从服务端拉，避免 reference 过期

## 三个工具

| 工具 | 用途 |
|---|---|
| `mcp__scaffold__list_middleware_options()` | 实时拉取可选中间件和服务段清单 |
| `mcp__scaffold__validate_params(package_name, component_id)` | 提前校验命名格式 |
| `mcp__scaffold__generate_backend(...)` | 生成脚手架并解压到 output_path |

## 调用流程

### Step 1: 读取项目级默认配置

读 `.ai-dev/scaffold-defaults.yaml`：

```yaml
backend:
  # 业务字段
  port: "17000"
  error_code: "0x160a"
  dependencies_version: "3.2.5.RELEASE"
  version: "2.0-SNAPSHOT"
  service_ids: ["patpps"]
  component_id: "patpps"
  package_name: "com.company.demo"
  middlewares:
    - {label: "Redis", has: true, value: ""}
  # 用户身份
  author: "张三"
  email: "zhangsan@company.com"
```

所有字段（含 author / email）都由 Orchestrator 在编码阶段开头用 AskUserQuestion 统一收集后写入。**BackendAgent 启动时 yaml 应已就绪**。

文件不存在或字段缺失 → 在 issues 里记录 `scaffold_defaults_missing: [缺失字段列表]`，REVISE 上报由 Orchestrator 补齐。

**禁止用 LLM 凭空猜测任何字段**（含 port / error_code / version / author / email）。

### Step 2: 拉取可选清单

调 `mcp__scaffold__list_middleware_options()`：

- 返回 `{options: [...]}` 或 `{service_ids: [...], middlewares: [...]}`（取决于 SpringBoot 实现）→ 用返回值确定 `service_ids` 和 `middlewares` 候选
- 返回 `{status: "error", error_code: "NOT_IMPLEMENTED"}` → SpringBoot 未实现 /api/options，使用 yaml 中预设的 service_ids / middlewares
- 返回 `OPTIONS_FETCH_FAILED` → 网络错误，issues 上报 blocking，不要继续

### Step 3: 校验命名

调 `mcp__scaffold__validate_params(package_name, component_id)`：

- `valid: true` → 继续 Step 4
- `valid: false` → 把 errors 写入 issues（category: requirement_gap），由 Orchestrator REVISE 让用户修正 yaml

### Step 4: 生成脚手架

调 `mcp__scaffold__generate_backend(...)`，参数全部来自 Step 1 的 yaml：

```
mcp__scaffold__generate_backend(
  component_id      = yaml.backend.component_id,
  package_name      = yaml.backend.package_name,
  service_ids       = yaml.backend.service_ids,
  port              = yaml.backend.port,
  error_code        = yaml.backend.error_code,
  author            = yaml.backend.author,
  email             = yaml.backend.email,
  middlewares       = yaml.backend.middlewares,
  version           = yaml.backend.version,
  dependencies_version = yaml.backend.dependencies_version,
  output_path       = "workspace/backend",
  overwrite         = false
)
```

### Step 5: 处理返回

- `status: "ok"` → 用返回的 `next_steps` 继续后续阶段。在 05_backend_report.md 顶部记录：脚手架来源（MCP scaffold）、files_created、main_class、framework_version
- `status: "error"`：
  | error_code | 处理 |
  |---|---|
  | `INVALID_PARAMS` | yaml 字段格式错，issues 上报让 Orchestrator REVISE |
  | `TARGET_NOT_EMPTY` | workspace/backend 已有内容。**不要传 overwrite=true 自动覆盖**，issues 上报问用户 |
  | `BACKEND_VALIDATION` | SpringBoot 服务端 4xx 校验失败，把 message 整段贴到 issues |
  | `DOWNLOAD_FAILED` | 网络/服务端 5xx，blocking issues |
  | `ZIP_CORRUPTED` | 服务端返回 zip 损坏，blocking issues |
  | `NOT_IMPLEMENTED` / `OPTIONS_FETCH_FAILED` | 只可能在 Step 2 出现，已在那里处理 |

## 红线（违反任一视为任务失败）

1. **禁止 Bash 拉取**：不允许 `curl` / `wget` / `Invoke-WebRequest` / `python -c "urllib..."` 直接下脚手架
2. **禁止凭空猜参数**：`port` / `error_code` / `dependencies_version` / `version` / `service_ids` / `author` / `email` 全部必须来自 yaml，缺失就 REVISE 不要猜（公司没有 git 环境，禁止 `git config` 取 author/email）
3. **禁止自动 overwrite**：`TARGET_NOT_EMPTY` 时必须问用户，不能擅自传 `overwrite=true` 删除用户已有工作
4. **禁止跳过 validate_params**：必须先校验命名，避免 Step 4 才被服务端拒
5. **禁止假调用**：`generate_backend` 返回 ok 后必须真有文件落到 output_path；如果对返回值有疑问，用 Read/Glob 校验

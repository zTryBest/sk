# Input Fetching

> **STOP — 读到这里说明输入是 URL。下面的决策树是强约束，不是建议。**
> 在抓取过程中，禁止 fallback 到任何本文件未列出的方案（例如直接要用户粘贴文本）。
> 抓取相关的 open_question 必须用 **OQ-URL-XX** 编号；其他编号格式视为违反约束。

## 触发条件

当输入包含 URL（http/https 开头）时，必须执行本文件的抓取流程。不要跳过直接要求用户粘贴内容。

## 抓取决策树

严格按以下顺序执行，逐步降级：

```
Step 1: WebFetch 轻量抓取
  ↓ 成功 → 提取内容，结束
  ↓ 失败（403/SSO跳转/空内容/超时）→ Step 2

Step 2: Playwright MCP 抓取（默认持久化 profile）
  ↓ 页面正常（cookie 已有效）→ 提取内容，结束
  ↓ 跳转到登录页 → Step 3

Step 3: 检查 SSO 自动登录配置
  ↓ ~/.claude/config/internal-urls.yaml 凭证完整 → Step 3a 自动填表
  ↓ 凭证缺失 → Step 3b 引导用户手动登录

Step 3a: 自动 SSO 填表登录
  ↓ 成功 → 重抓 ticket URL，结束
  ↓ 失败（验证码/MFA/密码错）→ Step 3b

Step 3b: 输出 draft + open_question 引导用户在 Playwright 浏览器中手动登录
  ↓ 用户登录后 REVISE 重新调度 → Step 2 重试

Step 4: 全部失败 → 输出 draft 请求人工粘贴内容
```

**核心理念**：Playwright MCP 默认就是持久化 profile（按 workspace 自动隔离），用户只要在它打开的浏览器窗口里手工登录过一次，cookie 就会保留下来。后续所有抓取都免登。SSO 自动填表只是兜底，**不是首选**。

## Step 1: WebFetch 轻量抓取

直接调用 WebFetch 工具：
```
WebFetch(url: "<ticket_url>", prompt: "提取页面中的需求标题、正文、附件信息、平台名称和版本")
```

判断失败标志：
- 返回内容包含 "login"、"sign in"、"SSO"、"unauthorized"、"403"
- 返回内容为空或明显不是需求内容
- 被重定向到非目标域名

## Step 2: Playwright MCP 抓取（持久化 profile）

使用 Playwright MCP 打开页面：

```
mcp__playwright__browser_navigate(url: "<ticket_url>")
mcp__playwright__browser_snapshot()
```

**Playwright MCP 默认会用持久化 profile**（路径取决于 OS）：
- Windows: `%USERPROFILE%\AppData\Local\ms-playwright\mcp-{channel}-{workspace-hash}`
- macOS: `~/Library/Caches/ms-playwright/mcp-{channel}-{workspace-hash}`
- Linux: `~/.cache/ms-playwright/mcp-{channel}-{workspace-hash}`

之前在同一 workspace 登录过的 cookie / localStorage 都会自动复用。

判断页面状态：
- 页面内容正常（包含需求标题、正文等业务字段）→ 直接提取，结束
- 页面是登录页（出现用户名/密码输入框、SSO 重定向 URL、"请登录"等文本）→ 进入 Step 3

## Step 3: 处理登录页

### 3.1 读取 SSO 配置（必须执行，禁止跳过）

**强制动作：用 Read 工具读取 `~/.claude/config/internal-urls.yaml`。Read 工具会自动解析 `~`，Windows 上也用这个路径。不要用 Bash cat，不要凭空假设凭证缺失。**

Read 必须真的发生。返回结果按以下分支处理：

| Read 结果 | 走哪条 | 必须留的证据 |
|---|---|---|
| 文件不存在（ENOENT / no such file） | Step 3b | issues 中记录 `yaml_path_attempted: "~/.claude/config/internal-urls.yaml"` + `yaml_status: "not_found"` |
| 文件存在但 `sso_username` / `sso_password` / `sso_selectors.*` 任一为空 | Step 3b | issues 中记录 `yaml_status: "incomplete"` + 列出哪些字段为空 |
| 全部字段非空 | **Step 3a 自动填表（不允许跳到 3b）** | 在 fetch_status 里写 `sso_auto_login_attempted: true` |

**违反约束的表现（任一即任务失败）：**
- 输出 "SSO 拦截无法抓取" 但 issues 里没有 yaml 读取结果
- yaml 字段齐全却走 Step 3b 引导手动登录
- 用 Bash `cat` / `grep` 替代 Read 工具读取 yaml

字段：
```yaml
sso_login: "https://..."           # 必需
playwright_profile_dir: "..."      # 仅说明，实际 profile 由 MCP 启动参数决定
sso_username: ""                   # 可选 — 走自动填表才需要
sso_password: ""                   # 可选 — 走自动填表才需要
sso_selectors:                     # 可选 — 走自动填表才需要
  username_input: "#username"
  password_input: "#password"
  submit_button: "#submit"
```

### 3.2 路径分叉

| 条件 | 走哪条 |
|------|--------|
| `sso_username` + `sso_password` + `sso_selectors` 都有值 | Step 3a 自动填表 |
| 缺任一字段 | Step 3b 引导手动登录 |

## Step 3a: SSO 自动填表登录

```
1. mcp__playwright__browser_navigate(url: sso_login)
2. mcp__playwright__browser_snapshot()
3. mcp__playwright__browser_fill_form(fields: [
     {target: sso_selectors.username_input, name: "username", type: "textbox", value: sso_username},
     {target: sso_selectors.password_input, name: "password", type: "textbox", value: sso_password}
   ])
4. mcp__playwright__browser_click(target: sso_selectors.submit_button)
5. mcp__playwright__browser_wait_for(time: 3)
6. mcp__playwright__browser_snapshot()  -- 确认登录成功
7. mcp__playwright__browser_navigate(url: "<ticket_url>")
8. mcp__playwright__browser_snapshot()  -- 提取内容
```

登录失败处理（验证码/MFA/密码错/超时）→ Step 3b。

## Step 3b: 引导用户手动登录（推荐路径）

**不要**关闭 Playwright 浏览器，**不要**再尝试自动填表。直接：

1. 在 `open_questions` 中输出引导：

```json
{
  "id": "OQ-URL-01",
  "question": "需要在 Playwright 浏览器窗口中手动登录一次",
  "known_facts": "URL: <ticket_url>，当前被重定向到登录页。Playwright MCP 已打开浏览器窗口；持久化 profile 会缓存登录态。",
  "options": [
    "在 Playwright 已打开的浏览器中完成 SSO 登录，登录成功后回复'已登录'，我会 REVISE 重新抓取",
    "在 ~/.claude/config/internal-urls.yaml 中填入 SSO 用户名/密码/selector，下次走自动填表",
    "直接把 ticket 正文粘贴到对话中"
  ],
  "recommended": "在 Playwright 浏览器中手动登录（一次性，之后免登）",
  "impact": "未完成前需求分析只能基于现有信息输出 draft"
}
```

2. 输出 `status: "draft"`，把抓取结果留空或仅保留 URL。
3. 返回 Orchestrator，等待 Human Gate REVISE。

### REVISE 重抓

收到"已登录"反馈后，Agent 重新执行 Step 2 即可。持久化 profile 已带 cookie，无需再走 Step 3。

## Step 4: 全部失败的兜底

仅在以下情况进入：
- Step 3b 用户拒绝任何登录方案
- 多次 REVISE 仍无法抓取

```json
{
  "id": "OQ-URL-99",
  "question": "无法自动访问 ticket URL，需要人工粘贴",
  "known_facts": "URL: <url>，已尝试 WebFetch / Playwright / SSO 自动填表 / 手动登录引导，均失败",
  "options": [
    "用户手动粘贴 ticket 正文",
    "提供新的可访问 URL"
  ],
  "recommended": "用户手动粘贴 ticket 正文",
  "impact": "需求分析只能基于用户手动输入"
}
```

## 内容提取

抓取成功后，从页面中提取：
- 需求标题
- 需求正文/描述
- 附件列表（名称和链接）
- 平台名称 / `product_id`
- 平台版本 / `product_version`
- 优先级
- 关联人员/角色
- 标签/分类

如果平台名称或版本在页面中未找到，不要猜，标记为 `open_questions`。

## 禁止行为

- 禁止在 WebFetch 失败后直接放弃或要求用户粘贴。
- 禁止跳过 Step 2 直接进 Step 3。
- 禁止把 SSO 密码贴到对话中要求用户提供。
- 禁止在 Step 3b 等待用户期间用 sleep / 轮询 — agent 必须返回 draft 由 Orchestrator REVISE。

# Input Fetching

## 触发条件

当输入包含 URL（http/https 开头）时，必须执行本文件的抓取流程。不要跳过直接要求用户粘贴内容。

## 抓取决策树

严格按以下顺序执行，逐步降级：

```
Step 1: WebFetch 轻量抓取
  ↓ 成功 → 提取内容，结束
  ↓ 失败（403/SSO跳转/空内容/超时）→ Step 2

Step 2: Playwright MCP 抓取（带已有 session）
  ↓ 成功 → 提取内容，结束
  ↓ 需要登录 → Step 3

Step 3: 读取 SSO 配置并自动登录
  ↓ 配置完整且登录成功 → 抓取内容，结束
  ↓ 配置缺失或登录失败 → Step 4

Step 4: 输出 draft，请求人工协助
```

## Step 1: WebFetch 轻量抓取

直接调用 WebFetch 工具：
```
WebFetch(url: "<ticket_url>", prompt: "提取页面中的需求标题、正文、附件信息、平台名称和版本")
```

判断失败标志：
- 返回内容包含 "login"、"sign in"、"SSO"、"unauthorized"、"403"
- 返回内容为空或明显不是需求内容
- 被重定向到非目标域名

## Step 2: Playwright MCP 抓取

使用 Playwright MCP 打开页面：

```
mcp__playwright__browser_navigate(url: "<ticket_url>")
mcp__playwright__browser_snapshot()
```

检查页面快照：
- 如果页面内容正常（包含需求信息）→ 提取内容，结束
- 如果页面是登录页面（包含用户名/密码输入框）→ 进入 Step 3

## Step 3: SSO 自动登录

### 3.1 读取配置

配置文件路径（按平台选择）：

Windows:
```
%USERPROFILE%\.claude\config\internal-urls.yaml
```

WSL/Linux:
```
~/.claude/config/internal-urls.yaml
```

配置字段：
```yaml
sso_login: "https://..."
playwright_profile_dir: "~/.claude/browser-profile"
sso_username: ""
sso_password: ""
sso_selectors:
  username_input: "#username"
  password_input: "#password"
  submit_button: "#submit"
```

### 3.2 判断是否可自动登录

| 条件 | 动作 |
|------|------|
| `sso_username` + `sso_password` + `sso_selectors` 都有值 | 执行自动登录 |
| 缺少任一字段 | 进入 Step 4 |

### 3.3 执行自动登录

```
1. mcp__playwright__browser_navigate(url: sso_login)
2. mcp__playwright__browser_snapshot()  -- 确认在登录页
3. mcp__playwright__browser_fill_form(fields: [
     {target: sso_selectors.username_input, name: "username", type: "textbox", value: sso_username},
     {target: sso_selectors.password_input, name: "password", type: "textbox", value: sso_password}
   ])
4. mcp__playwright__browser_click(target: sso_selectors.submit_button)
5. mcp__playwright__browser_wait_for(time: 3)  -- 等待登录完成
6. mcp__playwright__browser_snapshot()  -- 检查是否登录成功
7. 登录成功后，重新导航到 ticket URL：
   mcp__playwright__browser_navigate(url: "<ticket_url>")
8. mcp__playwright__browser_snapshot()  -- 提取内容
```

判断登录成功：页面不再是登录页，或已跳转回目标页面。
判断登录失败：页面仍在登录页，或出现错误提示。

### 3.4 登录失败处理

- 如果出现验证码/MFA → 进入 Step 4
- 如果账号密码错误 → 进入 Step 4
- 如果页面超时 → 重试一次，仍失败则进入 Step 4

## Step 4: 输出 draft，请求人工协助

无法自动抓取时：
- 不要猜测页面内容。
- 不要要求用户把密码贴到对话中。
- 在 `open_questions` 中写明需要人工协助：

```json
{
  "id": "OQ-URL-01",
  "question": "无法自动访问 ticket URL，需要人工提供内容",
  "known_facts": "URL: <url>，抓取失败原因：<reason>",
  "options": [
    "用户在浏览器中登录后，我用 Playwright 重新抓取",
    "用户手动粘贴 ticket 内容到对话中"
  ],
  "recommended": "用户在浏览器中登录后重新抓取",
  "impact": "无法获取原始需求文本，需求分析只能基于用户手动输入"
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

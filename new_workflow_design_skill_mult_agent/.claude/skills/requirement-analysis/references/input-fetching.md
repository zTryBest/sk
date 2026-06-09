# Input Fetching

## 配置

开始前按需加载全局内部系统地址：

```text
%USERPROFILE%\.claude\config\internal-urls.yaml
```

WSL 用户路径：

```text
/mnt/c/Users/<username>/.claude/config/internal-urls.yaml
```

配置字段：

```yaml
sso_login: "https://..."
playwright_profile_dir: "~/.claude/browser-profile"
sso_username: ""
sso_password: ""
sso_selectors:
```

- `sso_login`：内部系统认证入口。访问需登录页面时可能自动跳转到此地址。
- `playwright_profile_dir`：Playwright MCP 持久化 SSO 会话的浏览器 profile 目录。
- `sso_username` / `sso_password`：可选。留空时让用户在浏览器中手动登录，密码不经过模型。
- `sso_selectors`：仅自动登录模式需要。

Ticket URL 不是固定配置，由用户每次需求分析时提供。未提供 ticket URL 时走手动输入模式。

## Mode A：Ticket URL

当用户提供 ticket URL 时，按级联策略抓取，不要一开始要求用户手动粘贴。

1. 先尝试轻量抓取，例如 WebFetch 或可用页面提取工具。
2. 如果轻量抓取失败、跳转 SSO、403、超时或内容为空，自动切换到 Playwright MCP 或浏览器抓取。
3. 如果需要 SSO 登录：
   - 已配置账号密码时按配置自动登录。
   - Agent 模式下也必须先读取 `internal-urls.yaml`；如果 `sso_username`、`sso_password`、`sso_selectors` 和 Playwright/MCP 能力可用，可以在本阶段内完成登录和抓取。
   - 未配置密码时，告知 Main Agent 需要 Human Gate 在浏览器中完成登录，不要让用户把密码贴到对话中。
   - 只有在缺少密码、缺少选择器、MCP/浏览器不可用、登录失败或需要人机验证时，才停止抓取并把需要的外部动作返回给 Main Agent。
4. 抓取完成后提取需求标题、正文、附件线索、平台名称、平台版本和原始文本。

## Mode B：手动输入或文档粘贴

当用户直接粘贴需求文档、文本或附件内容时，从文本中提取：

- 平台名称 / `product_id`
- 平台版本 / `product_version`
- 需求背景
- 角色 / 参与者
- 功能项和验收标准
- 约束、依赖、边界
- 澄清记录

如果平台名称或版本缺失，先阻塞确认。

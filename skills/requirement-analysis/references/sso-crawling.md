# SSO-Protected Internal System Access

## Problem

All company-internal systems are behind SSO authentication. Simple HTTP fetch
cannot access them. This includes:

- **需求 ticket 系统** — ticket URL 由用户每次提供（不在配置文件中）
- **产品构成查询系统** — `product_composition` URL（配置文件中的全局地址）
- **组件接口查询系统** — `component_api` URL（配置文件中的全局地址）

Any access to these systems requires SSO authentication first.

## Solution: Playwright MCP

Use `@playwright/mcp` as an MCP server with persistent browser profile so SSO
login happens once and session is reused.

### Prerequisites

1. Node.js + npx — already available
2. Playwright — already installed (v1.60)

### Config

```bash
claude mcp add playwright -- npx -y @playwright/mcp \
  --user-data-dir ~/.claude/browser-profile \
  --save-session \
  --output-dir ~/.claude/browser-output
```

Key options:
- `--user-data-dir <path>` — persists browser cookies, localStorage, etc.
  This makes SSO work: after first login, session survives restarts.
- `--save-session` — saves MCP session state alongside browser profile.
- No `--headless` — runs headed by default so the SSO login page is visible.

### First-Time SSO Login

1. Add the MCP server config
2. Navigate to any internal URL (ticket, product_composition, or component_api) via Playwright MCP
3. The browser auto-redirects to the SSO login page (`sso_login` from config)
4. A visible browser window opens
5. **Complete SSO login manually** (credentials, MFA if needed)
6. Browser session is saved to `--user-data-dir`
7. Future uses: navigating to ANY internal URL reuses saved session, SSO is transparent

### Crawling Flow (General Pattern)

Once SSO session is established, the same pattern works for any internal system:

```
# Ticket crawling (URL provided by user each time)
Playwright: browser_navigate(url="<USER-PROVIDED-TICKET-URL>")
  → SSO auto-redirect if needed, cookies reused

# Product composition (global URL from config)
Playwright: browser_navigate(url="<product_composition>")
  → Search platform name → click result → view "产品构成"

# Component API (global URL from config)
Playwright: browser_navigate(url="<component_api>")
  → Search component name → hover tag → click "查看详情"
```

### Fallback: Standalone Playwright Script

If MCP is not available, use a standalone Node.js script:

```javascript
// crawl-ticket.js
const { chromium } = require('playwright');
const url = process.argv[2];

(async () => {
  const browser = await chromium.launchPersistentContext(
    '~/.claude/browser-profile',
    { headless: false }
  );
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: 'networkidle' });
  const content = await page.innerText('body');
  console.log(content);
  await browser.close();
})();
```

### Cascading Strategy: web_fetch → Playwright

If the page is publicly accessible, `web_fetch` will return clean content directly.
If it fails (SSO redirect, 403, etc.), Playwright MCP is the automatic fallback.

**Do not skip web_fetch.** Always try the lightweight approach first.
Playwright is the escalation path, not the default.

### Pitfalls

- **SSO session expiry**: If crawling fails with redirects to login, re-open
  headed browser and re-login.
- **WSL display**: In WSL, headed browser requires WSLg or X server. If not
  available, perform first-time SSO login on a machine with display, then
  copy `--user-data-dir` to the WSL environment.
- **MFA**: If SSO requires MFA on every login (not just first time), Playwright
  MCP cannot automate this. The user must be available to complete MFA.

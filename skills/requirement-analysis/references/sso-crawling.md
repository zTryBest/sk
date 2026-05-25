# SSO-Protected Requirement Ticket Crawling

## Problem

Company-internal requirement systems (Jira, TAPD, 禅道, 飞书, custom) are behind
SSO authentication. Simple `curl` / HTTP fetch cannot access them.

## Solution: Playwright MCP

Use `@playwright/mcp` as an MCP server with persistent browser profile so SSO
login happens once and session is reused.

### Prerequisites

1. **Node.js + npx** — already available
2. **Playwright** — already installed (v1.60)
3. **mcp Python package** — `pip install mcp` (required by Hermes native MCP client)

### Config

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  playwright:
    command: "npx"
    args:
      - "-y"
      - "@playwright/mcp"
      - "--user-data-dir"
      - "~/.hermes/browser-profile"
      - "--save-session"
      - "--output-dir"
      - "~/.hermes/browser-output"
    timeout: 120
    connect_timeout: 60
```

Key options:
- `--user-data-dir <path>` — persists browser cookies, localStorage, etc.
  This is what makes SSO work: after first login, session survives restarts.
- `--save-session` — saves MCP session state alongside browser profile.
- No `--headless` — runs headed by default so user can see and interact with
  the SSO login page the first time.

### First-Time SSO Login

1. Restart Hermes after adding the config
2. Ask the agent to navigate to the internal ticket URL
3. A visible browser window opens, redirects to SSO
4. **User manually logs in** (enter credentials, MFA if needed)
5. Browser session is saved to `--user-data-dir`
6. Future uses: browser reuses saved session, SSO is transparent

### Crawling Flow

Once SSO session is established, the flow for requirement analysis:

```
mcp_playwright_browser_navigate(url="<TICKET_URL>")
  → SSO auto-redirect, cookies reused, no login needed
  → Page loads

mcp_playwright_browser_snapshot()
  → Returns page content as accessibility tree
  → Parse to extract: platform version, requirement title, description, comments
```

### Fallback: Standalone Playwright Script

If MCP is not available (mcp package not installed), use a standalone Node.js
script called via `terminal`:

```javascript
// ~/.hermes/scripts/crawl-ticket.js
const { chromium } = require('playwright');
const url = process.argv[2];

(async () => {
  const browser = await chromium.launchPersistentContext(
    '~/.hermes/browser-profile',
    { headless: false }
  );
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: 'networkidle' });
  const content = await page.content();
  console.log(content);
  await browser.close();
})();
```

Usage: `node ~/.hermes/scripts/crawl-ticket.js "https://ticket-url"`

### Alternative: crawl4ai

`crawl4ai` is a Python library that excels at extracting clean Markdown from
web pages. However, it does NOT handle SSO login. It could be useful as a
post-processing step after Playwright MCP has navigated and authenticated.

Decision: start with Playwright MCP. Add crawl4ai later if page parsing quality
becomes a bottleneck.

### Pitfalls

- **SSO session expiry**: Some SSO providers expire sessions after hours/days.
  If crawling fails with redirects to login, re-open headed browser and re-login.
- **WSL display**: In WSL, headed browser requires WSLg or X server. If not
  available, first-time SSO login must be done on a machine with display, then
  copy `--user-data-dir` to the WSL environment.
- **MFA**: If SSO requires MFA on every login (not just first time), Playwright
  MCP cannot automate this. User must be available to complete MFA.

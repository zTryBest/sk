# SSO-Protected Requirement Ticket Crawling

## Problem

Company-internal requirement systems (Jira, TAPD, 禅道, 飞书, custom) are behind
SSO authentication. Simple HTTP fetch cannot access them.

## Solution: Playwright MCP

Use `@playwright/mcp` as an MCP server with persistent browser profile so SSO
login happens once and session is reused.

### Prerequisites

1. Node.js + npx — already available
2. Playwright — already installed (v1.60)

### Config

```bash
claude mcp add playwright -- npx -y @playwright/mcp \
  --user-data-dir /home/edc/.hermes/browser-profile \
  --save-session \
  --output-dir /home/edc/.hermes/browser-output
```

Key options:
- `--user-data-dir <path>` — persists browser cookies, localStorage, etc.
  This makes SSO work: after first login, session survives restarts.
- `--save-session` — saves MCP session state alongside browser profile.
- No `--headless` — runs headed by default so the SSO login page is visible.

### First-Time SSO Login

1. Add the MCP server config
2. Navigate to the internal ticket URL via Playwright MCP tools
3. A visible browser window opens, redirects to SSO
4. **Complete SSO login manually** (credentials, MFA if needed)
5. Browser session is saved to `--user-data-dir`
6. Future uses: browser reuses saved session, SSO is transparent

### Crawling Flow

Once SSO session is established:

```
Playwright: browser_navigate(url="https://ticket-system.example.com/issue/PROJ-1234")
  → SSO auto-redirect, cookies reused, no login needed
  → Page loads

Playwright: browser_snapshot()
  → Returns page content as accessibility tree
  → Parse to extract: platform version, requirement title, description, comments
```

### Fallback: Standalone Playwright Script

If MCP is not available, use a standalone Node.js script:

```javascript
// crawl-ticket.js
const { chromium } = require('playwright');
const url = process.argv[2];

(async () => {
  const browser = await chromium.launchPersistentContext(
    '/home/edc/.hermes/browser-profile',
    { headless: false }
  );
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: 'networkidle' });
  const content = await page.innerText('body');
  console.log(content);
  await browser.close();
})();
```

### Alternative: crawl4ai

`crawl4ai` excels at extracting clean Markdown from web pages but does NOT
handle SSO login. Use it as a post-processing step after Playwright MCP has
navigated and authenticated, or for public pages.

### Pitfalls

- **SSO session expiry**: If crawling fails with redirects to login, re-open
  headed browser and re-login.
- **WSL display**: In WSL, headed browser requires WSLg or X server. If not
  available, perform first-time SSO login on a machine with display, then
  copy `--user-data-dir` to the WSL environment.
- **MFA**: If SSO requires MFA on every login (not just first time), Playwright
  MCP cannot automate this. The user must be available to complete MFA.

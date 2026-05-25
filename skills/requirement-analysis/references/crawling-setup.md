# Crawling Infrastructure Setup

> Last verified: 2026-05-25, Python 3.14, WSL (Ubuntu)

## Architecture

Three-mode crawling for requirement tickets:

```
Mode A: Playwright MCP  →  SSO-protected internal systems
Mode B: crawl4ai        →  Public / API-accessible pages
Mode C: Manual input    →  Fallback
```

## Playwright MCP Configuration

Added to `~/.hermes/config.yaml`:

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

Key details:
- **`--user-data-dir`** persists browser cookies/localStorage — SSO session survives restarts
- **`--save-session`** saves Playwright session data to output dir
- **No `--headless`** — runs headed by default so user can see SSO login page
- **MCP package**: `@playwright/mcp` (NOT the deprecated `@anthropic/mcp-server-playwright`)
- **Prerequisite**: `pip install mcp` (Python MCP client for Hermes to connect to MCP servers)

## SSO Login Flow

1. First use: Playwright MCP launches headed browser, user completes SSO
2. Session stored in `--user-data-dir`
3. Subsequent uses: browser reuses saved session, SSO transparent
4. If session expires: prompt user to re-login

WSL GUI requirements:
- WSLg should be enabled by default on WSL2
- Alternative: export cookies from Windows host browser to `user-data-dir`

## crawl4ai Installation (Python 3.14)

**Problem**: crawl4ai 0.8.6 pins `lxml~=5.3`, but lxml 5.x has no pre-built wheel for Python 3.14 (cp314). Building from source fails without Cython.

**Solution**: Install lxml 6.1.1 separately (has cp314 wheel), then install crawl4ai with `--no-deps`, then install remaining dependencies individually.

```bash
# Prerequisites
sudo apt-get install -y libxml2-dev libxslt-dev python3-dev

# Install lxml 6.1.1 (cp314 pre-built wheel available)
python3 -m pip install --break-system-packages lxml

# Install crawl4ai without its pinned lxml
python3 -m pip install --break-system-packages --no-deps crawl4ai

# Install remaining dependencies (discovered iteratively)
python3 -m pip install --break-system-packages \
    aiosqlite aiofiles playwright pyppeteer fake-useragent \
    cssselect lxml_html_clean snowballstemmer xxhash \
    beautifulsoup4 aiohttp psutil pillow pycryptodome \
    rank-bm25 nltk patchright tf-playwright-stealth \
    litellm shapely lark alphashape pyOpenSSL PyYAML \
    rich click chardet brotli humanize httpx
```

**Known version conflicts** (warnings, not errors):
- `lxml` 6.1.1 installed, crawl4ai expects ~5.3
- `snowballstemmer` 3.1.0 installed, crawl4ai expects ~2.2
- `litellm` 1.83.7 installed, crawl4ai expects unclecode-litellm 1.81.13

These are soft constraints — crawl4ai works despite the warnings.

## MCP Tool Names

After restarting Hermes, Playwright MCP registers tools with `mcp_playwright_*` prefix.
Common tool names (verify at runtime):
- `mcp_playwright_browser_navigate` — navigate to URL
- `mcp_playwright_browser_snapshot` — accessibility tree of current page
- `mcp_playwright_browser_take_screenshot` — screenshot
- `mcp_playwright_browser_evaluate` — execute JS in page (e.g., `document.body.innerText`)
- `mcp_playwright_browser_click` — click element

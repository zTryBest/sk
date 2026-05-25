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

Add to Claude Code MCP config (`.claude/mcp.json` or `claude mcp add`):

```bash
claude mcp add playwright -- npx -y @playwright/mcp \
  --user-data-dir ~/.claude/browser-profile \
  --save-session \
  --output-dir ~/.claude/browser-output
```

Key details:
- `--user-data-dir` persists browser cookies/localStorage — SSO session survives restarts
- `--save-session` saves Playwright session data to output dir
- No `--headless` — runs headed by default so user can see SSO login page
- MCP package: `@playwright/mcp` (NOT the deprecated `@anthropic/mcp-server-playwright`)

## SSO Login Flow

1. First use: Playwright MCP launches headed browser, user completes SSO
2. Session stored in `--user-data-dir`
3. Subsequent uses: browser reuses saved session, SSO transparent
4. If session expires: prompt user to re-login

WSL GUI requirements:
- WSLg enabled by default on WSL2
- Alternative: export cookies from Windows host browser to `user-data-dir`

## crawl4ai Installation (Python 3.14)

crawl4ai 0.8.6 pins `lxml~=5.3`, but lxml 5.x has no pre-built wheel for Python 3.14 (cp314).

```bash
# Prerequisites
sudo apt-get install -y libxml2-dev libxslt-dev python3-dev

# Install lxml 6.1.1 (cp314 pre-built wheel available)
python3 -m pip install --break-system-packages lxml

# Install crawl4ai without its pinned lxml
python3 -m pip install --break-system-packages --no-deps crawl4ai

# Install remaining dependencies
python3 -m pip install --break-system-packages \
    aiosqlite aiofiles playwright pyppeteer fake-useragent \
    cssselect lxml_html_clean snowballstemmer xxhash \
    beautifulsoup4 aiohttp psutil pillow pycryptodome \
    rank-bm25 nltk patchright tf-playwright-stealth \
    litellm shapely lark alphashape pyOpenSSL PyYAML \
    rich click chardet brotli humanize httpx
```

Known version conflicts (warnings, not errors):
- `lxml` 6.1.1 vs crawl4ai expects ~5.3
- `snowballstemmer` 3.1.0 vs crawl4ai expects ~2.2

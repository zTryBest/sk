# Environment Variables & Cross-Platform Paths

## Platform-Agnostic Path Convention

All paths use `~/.hermes/` as the base directory. This expands correctly on:
- **Linux**: `~` → `/home/<user>/`
- **macOS**: `~` → `/Users/<user>/`
- **Windows (WSL)**: `~` → `/home/<user>/`
- **Windows (native)**: `~` → `C:\Users\<user>\`

Example:
```
~/.hermes/knowledge/     → Knowledge base (shared across projects)
~/.hermes/.env           → Environment variables (credentials, tokens)
~/.hermes/browser-profile/ → Playwright persistent browser state
```

## Credential Management

Credentials are stored in `~/.hermes/.env` and loaded by the agent at startup.

```bash
# Required for internal platform access
PVIC_API_TOKEN=your-token-here

# Required for scaffold API access
SCAFFOLD_API_KEY=your-key-here
```

In skills, reference environment variables like `$PVIC_API_TOKEN`.
When using curl, pass via `-H "Authorization: Bearer $PVIC_API_TOKEN"`.

## SSO / Browser Session

Playwright MCP stores the browser session in `~/.hermes/browser-profile/`.
This is cross-platform — Playwright's persistent context API handles OS differences.

First-time SSO login: the browser opens (headed mode), user logs in once,
session persists. On session expiry, re-login is needed.

## WSL-Specific Notes

- WSLg provides GUI for headed browser — usually enabled by default
- If WSLg is not available, perform first-time SSO login on Windows host,
  then copy the profile: `cp -r /mnt/c/Users/<user>/AppData/Local/... ~/.hermes/browser-profile/`

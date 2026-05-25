# Platform Component & API Discovery

> Internal tool URLs — exact addresses provided by user per platform.
> All interactions via Playwright MCP with saved SSO session.

## Component Discovery

URL: `<COMPONENTS_URL>` (user-provided)

Steps:
1. Navigate to the internal components URL via Playwright MCP.
2. In the search bar, enter the platform name (e.g. "PVIC").
3. Search results appear as cards — each card is one product.
4. Click the card matching the target platform to enter the product detail page.
5. On the detail page, locate the **"产品构成" (Product Composition)** module.
6. This module lists ALL components (microservices) that make up the platform.
7. Extract: component name, description, status, version info.
8. Present the component list to the user for confirmation.

## API (Interface) Discovery

URL: `<APIS_URL>` (user-provided)

Steps:
1. Navigate to the internal API docs URL via Playwright MCP.
2. In the search bar, enter the component name (e.g. "用户服务").
3. Search results include **component tags** — clickable labels.
4. **Hover** the mouse over a component tag to reveal a **"查看详情" (View Details)** button.
   - This button only appears on hover. Use `browser_hover` before `browser_click`.
5. Click "查看详情" to open the component's API detail page.
6. On the detail page, locate the **version selector** (dropdown).
7. **Version selection rule:** pick the latest version that is <= the target platform version.
   - Example: target = PVIC 2.4.0, available versions = [2.3.0, 2.4.0, 2.5.0, 3.0.0]
   - Select: 2.4.0 (latest ≤ 2.4.0)
8. Extract all API interfaces: method, path, request/response, description.
9. Present the API list to the user for confirmation.

## MCP Interaction Pattern

```
# Component discovery flow
browser_navigate("<COMPONENTS_URL>")
browser_type(selector="search-input", text="PVIC")
browser_click(selector="search-button")
browser_snapshot()                          # Get result cards
browser_click(selector=".card[data-name='PVIC']")
browser_snapshot()                          # Get product detail
# Locate "产品构成" section → extract component list

# API discovery flow
browser_navigate("<APIS_URL>")
browser_type(selector="search-input", text="用户服务")
browser_click(selector="search-button")
browser_snapshot()                          # Get component tags
browser_hover(selector=".tag[data-name='用户服务']")  # Hover to reveal detail button
browser_click(selector=".detail-button")    # Click "查看详情"
browser_snapshot()                          # Get API list
browser_select_option(selector="version-dropdown", value="2.4.0")
browser_snapshot()                          # Get version-specific APIs
```

## Confirmation Gate

After extracting component and API information:
1. Present to user in a structured table.
2. User confirms or corrects.
3. **Confirmed items are added to the knowledge base immediately.**

Knowledge base accumulation:
- Components → `~/.claude/knowledge/<platform>/microservices.md`
- APIs → `~/.claude/knowledge/<platform>/interfaces.md`

This ensures the next requirement analysis can query the KB directly
without repeating the Playwright crawl.

## Golden Rule: Never Guess

If an API cannot be found in the internal docs, or the documentation is
insufficient to determine the exact interface contract, **stop and ask the user**.
Never invent interfaces, parameters, or response formats. An incorrect API
contract wastes all downstream development work. Mark unclear items as
`[待确认]` and proceed only after user clarification.

Internal API documentation may lack sufficient detail. When this happens:

### Step 1: Ask for Examples
> "接口文档说明不够清晰（如缺少请求/响应示例、参数类型不明确），
>  是否有准确的请求/响应示例可以提供？"

If the user provides examples → use them as the authoritative API specification.

### Step 2: Ask for Test Environment
> "是否有测试环境可以直接调用该接口获取实际响应？"

If yes:
```bash
curl -s -H "Authorization: Bearer *** \
  "<TEST_API_URL>" \
  -d '["u001","u002"]' | python3 -m json.tool
```
Capture the real response and use it as the API contract.

### Step 3: Mark as Unclear
If neither is available → mark the unclear APIs as `[待确认]` in the design
document and proceed with best-effort design.

- **Hover required for "查看详情"** — the button is hidden until hover.
  Use `browser_hover` first, then `browser_click` on the revealed button.
- **Version selection** — always pick latest ≤ target version, not latest overall.
  A newer major version may have breaking API changes.
- **SSO session** — both URLs likely share the same SSO domain.
  The saved `auth.json` should work for both.
- **Page load timing** — after clicking into detail pages, wait for the
  "产品构成" or API list to render before taking a snapshot.

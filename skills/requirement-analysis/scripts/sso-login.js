#!/usr/bin/env node
/**
 * One-time SSO login script.
 * Opens a headed browser so the user can log in once,
 * then saves the authentication state for all future MCP sessions.
 *
 * Usage:
 *   node ~/.claude/skills/requirement-analysis/scripts/sso-login.js <SSO_LOGIN_URL>
 *
 * The saved state is loaded by Playwright MCP via --storage-state.
 */

const { chromium } = require("playwright");
const path = require("path");
const os = require("os");
const fs = require("fs");

const loginUrl = process.argv[2];
if (!loginUrl) {
  console.error("Usage: node sso-login.js <SSO_LOGIN_URL>");
  console.error("Example: node sso-login.js <SSO_LOGIN_URL>");
  process.exit(1);
}

const hermesHome = process.env.HERMES_HOME || path.join(os.homedir(), ".hermes");
const profileDir = path.join(hermesHome, "browser-profile");
const storageStateFile = path.join(profileDir, "auth.json");

fs.mkdirSync(profileDir, { recursive: true });

(async () => {
  console.log("=");
  console.log("  SSO Login Setup");
  console.log("=");
  console.log(`  Profile dir:  ${profileDir}`);
  console.log(`  Storage state: ${storageStateFile}`);
  console.log(`  Login URL:    ${loginUrl}`);
  console.log();

  const browser = await chromium.launchPersistentContext(profileDir, {
    headless: false,
    viewport: { width: 1280, height: 800 },
  });

  const page = await browser.newPage();
  await page.goto(loginUrl, { waitUntil: "domcontentloaded" });

  console.log("  Browser opened. Please complete SSO login in the browser window.");
  console.log("  Do NOT close the browser — this script will detect when login is done.");
  console.log();

  // Wait for navigation away from the SSO login page,
  // indicating successful authentication.
  try {
    await page.waitForURL((url) => !url.href.includes("login"), {
      timeout: 300_000, // 5 minutes
    });
  } catch {
    console.log("  Timeout waiting for login redirect.");
    console.log("  If you completed login, the session may still be usable.");
  }

  // Save storage state
  await browser.storageState({ path: storageStateFile });
  console.log(`  Auth state saved to ${storageStateFile}`);

  await browser.close();
  console.log("  Done. Restart Hermes / Claude Code to use the saved session.");
})().catch((err) => {
  console.error("  Error:", err.message);
  process.exit(1);
});

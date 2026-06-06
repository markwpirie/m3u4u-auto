import os
import re
import sys
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv
import capsolver

load_dotenv()

EMAIL = "markwpirie@aol.com"
PASSWORD = os.getenv("M3U4U_PASSWORD")
CAPSOLVER_API_KEY = os.getenv("CAPSOLVER_API_KEY")
WAIT_SECONDS = 60


def log(msg: str) -> None:
    print(f"[m3u4u] {msg}", flush=True)


def solve_turnstile(page) -> "str | None":
    """Detect and solve Cloudflare Turnstile via Capsolver. Returns token or None if no widget found."""
    # Let Angular and Cloudflare scripts finish loading
    log("  Waiting for page to settle...")
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except PlaywrightTimeoutError:
        pass  # proceed even if not fully idle

    site_key = None

    # Strategy 1: standard .cf-turnstile div
    try:
        page.wait_for_selector(".cf-turnstile", timeout=8_000)
        site_key = page.locator(".cf-turnstile").first.get_attribute("data-sitekey")
    except PlaywrightTimeoutError:
        pass

    # Strategy 2: any element carrying data-sitekey
    if not site_key:
        el = page.locator("[data-sitekey]").first
        if el.count() > 0:
            site_key = el.get_attribute("data-sitekey")

    # Strategy 3: pull site key from the Cloudflare iframe src
    if not site_key:
        iframe = page.locator("iframe[src*='challenges.cloudflare.com']").first
        if iframe.count() > 0:
            src = iframe.get_attribute("src") or ""
            m = re.search(r'[?&](?:sitekey|k)=([^&]+)', src)
            if not m:
                m = re.search(r'challenges\.cloudflare\.com/[^/]+/([0-9A-Za-z_-]{20,})', src)
            if m:
                site_key = m.group(1)

    # Strategy 4: regex sweep of full page HTML
    if not site_key:
        html = page.content()
        for pattern in [
            r'data-sitekey=["\']([^"\']+)["\']',
            r'"sitekey"\s*:\s*"([^"]+)"',
            r'"siteKey"\s*:\s*"([^"]+)"',
        ]:
            m = re.search(pattern, html)
            if m:
                site_key = m.group(1)
                break

    if not site_key:
        log("  Turnstile not detected — saving debug_page.html for inspection")
        with open("debug_page.html", "w", encoding="utf-8") as fh:
            fh.write(page.content())
        log("  Skipping CAPTCHA solve")
        return None

    log(f"  Turnstile site key: {site_key}")
    log("  Sending to Capsolver (typically 5–15s)...")

    capsolver.api_key = CAPSOLVER_API_KEY
    solution = capsolver.solve({
        "type": "AntiTurnstileTaskProxyless",
        "websiteURL": page.url,
        "websiteKey": site_key,
    })
    token = solution["token"]
    log("  Turnstile solved ✓")
    return token


def inject_turnstile_token(page, token: str) -> None:
    """Inject a solved Turnstile token into the page and fire any success callbacks."""
    page.evaluate(
        """(token) => {
            // Find or create the hidden response input Cloudflare expects
            let input = document.querySelector('input[name="cf-turnstile-response"]');
            if (!input) {
                input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'cf-turnstile-response';
                const widget = document.querySelector('.cf-turnstile') || document.body;
                widget.appendChild(input);
            }
            input.value = token;
            // Fire success callbacks declared on the widget
            document.querySelectorAll('[data-callback]').forEach(widget => {
                const cb = widget.getAttribute('data-callback');
                if (cb && typeof window[cb] === 'function') window[cb](token);
            });
        }""",
        token,
    )
    log("  Token injected into page")


def close_confirmation_dialog(page) -> None:
    """Wait for an Angular Material confirmation dialog and click Yes."""
    log("  Waiting for confirmation dialog...")
    try:
        dialog = page.locator("mat-dialog-container")
        dialog.wait_for(timeout=10_000)
        yes_btn = dialog.get_by_role("button", name="Yes")
        yes_btn.wait_for(timeout=10_000)
        yes_btn.click()
        log("  → Clicked 'Yes'")
        dialog.wait_for(state="hidden", timeout=10_000)
        log("  → Dialog closed")
        time.sleep(1)
    except PlaywrightTimeoutError as exc:
        raise RuntimeError("Confirmation dialog did not appear or 'Yes' button not found") from exc


def get_playlist_row(page, playlist_name: str):
    """Return the first row locator that contains the playlist name."""
    row = page.locator(
        f"mat-row:has-text('{playlist_name}'), "
        f"tr:has-text('{playlist_name}')"
    ).first
    try:
        row.wait_for(timeout=15_000)
    except PlaywrightTimeoutError:
        raise RuntimeError(f"Could not find a row containing '{playlist_name}'")
    return row


def find_row_button_by_icon(page, row, *icon_names):
    """Return the first button in the row that contains a mat-icon matching one of the names."""
    for name in icon_names:
        btn = row.locator("button").filter(
            has=page.locator("mat-icon").filter(has_text=name)
        )
        if btn.count() > 0:
            return btn.first
    return None


def click_sync_button(page, playlist_name: str) -> None:
    log(f"  Finding sync button for '{playlist_name}'...")
    row = get_playlist_row(page, playlist_name)
    btn = find_row_button_by_icon(page, row, "sync", "refresh", "sync_alt")
    if btn is None:
        log("  → Icon not matched; falling back to first button in row")
        btn = row.locator("button").first
    btn.scroll_into_view_if_needed()
    btn.click()
    log(f"  → Sync button clicked for '{playlist_name}'")


def click_push_button(page, playlist_name: str) -> None:
    log(f"  Finding Dropbox push button for '{playlist_name}'...")
    row = get_playlist_row(page, playlist_name)
    btn = find_row_button_by_icon(page, row, "cloud_upload", "publish", "backup", "upload")
    if btn is None:
        log("  → Icon not matched; falling back to second button in row")
        btn = row.locator("button").nth(1)
    btn.scroll_into_view_if_needed()
    btn.click()
    log(f"  → Push button clicked for '{playlist_name}'")


def main() -> None:
    missing = [k for k, v in {"M3U4U_PASSWORD": PASSWORD, "CAPSOLVER_API_KEY": CAPSOLVER_API_KEY}.items() if not v]
    if missing:
        for key in missing:
            log(f"ERROR: {key} is not set in .env")
        sys.exit(1)

    with sync_playwright() as p:
        log("Launching Chromium (non-headless for Cloudflare)...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        try:
            # ── Login ─────────────────────────────────────────────────────────────
            log("Navigating to https://m3u4u.com/login ...")
            page.goto("https://m3u4u.com/login", wait_until="domcontentloaded")

            log("Waiting for login form...")
            page.wait_for_selector("input[type='email']", timeout=30_000)

            # Solve Turnstile first — it needs networkidle to fully render
            token = solve_turnstile(page)

            log(f"Filling email: {EMAIL}")
            page.fill("input[type='email']", EMAIL)

            log("Filling password...")
            page.fill("input[type='password']", PASSWORD)

            if token:
                inject_turnstile_token(page, token)
                time.sleep(1)

            log("Clicking login button...")
            page.locator("button[type='submit']").click()

            log("Waiting for playlists page to render...")
            page.wait_for_selector("mat-row, tr.mat-row", timeout=60_000)
            time.sleep(2)
            log("Playlists page ready.")

            # ── Step 1: Sync Silver-Surf - Copy ───────────────────────────────────
            log("─── Step 1/4: Sync 'Silver-Surf - Copy' ───")
            click_sync_button(page, "Silver-Surf - Copy")
            close_confirmation_dialog(page)
            log(f"Waiting {WAIT_SECONDS}s ...")
            time.sleep(WAIT_SECONDS)

            # ── Step 2: Sync MARK Small List ──────────────────────────────────────
            log("─── Step 2/4: Sync 'MARK Small List' ───")
            click_sync_button(page, "MARK Small List")
            close_confirmation_dialog(page)
            log(f"Waiting {WAIT_SECONDS}s ...")
            time.sleep(WAIT_SECONDS)

            # ── Step 3: Push Silver-Surf - Copy to Dropbox ────────────────────────
            log("─── Step 3/4: Push 'Silver-Surf - Copy' to Dropbox ───")
            click_push_button(page, "Silver-Surf - Copy")
            close_confirmation_dialog(page)
            log(f"Waiting {WAIT_SECONDS}s ...")
            time.sleep(WAIT_SECONDS)

            # ── Step 4: Push MARK Small List to Dropbox ───────────────────────────
            log("─── Step 4/4: Push 'MARK Small List' to Dropbox ───")
            click_push_button(page, "MARK Small List")
            close_confirmation_dialog(page)

            log("All 4 operations completed successfully.")

        except Exception as exc:
            log(f"FATAL ERROR: {exc}")
            try:
                page.screenshot(path="error_screenshot.png")
                log("Screenshot saved → error_screenshot.png")
            except Exception:
                pass
            sys.exit(1)

        finally:
            browser.close()
            log("Browser closed.")


if __name__ == "__main__":
    main()

import os
import sys
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv

load_dotenv()

EMAIL = "markwpirie@aol.com"
PASSWORD = os.getenv("M3U4U_PASSWORD")
WAIT_SECONDS = 60


def log(msg: str) -> None:
    print(f"[m3u4u] {msg}", flush=True)


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
        time.sleep(1)  # let the UI settle after dialog close
    except PlaywrightTimeoutError as exc:
        raise RuntimeError("Confirmation dialog did not appear or 'Yes' button not found") from exc


def get_playlist_row(page, playlist_name: str):
    """Return the first row locator that contains the exact playlist name."""
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
    """Find the first button in the row that has a mat-icon matching one of the names."""
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
        log("  → Sync icon not matched by name; falling back to first button in row")
        btn = row.locator("button").first

    btn.scroll_into_view_if_needed()
    btn.click()
    log(f"  → Sync button clicked for '{playlist_name}'")


def click_push_button(page, playlist_name: str) -> None:
    log(f"  Finding Dropbox push button for '{playlist_name}'...")
    row = get_playlist_row(page, playlist_name)

    btn = find_row_button_by_icon(page, row, "cloud_upload", "publish", "backup", "upload")
    if btn is None:
        log("  → Push icon not matched by name; falling back to second button in row")
        btn = row.locator("button").nth(1)

    btn.scroll_into_view_if_needed()
    btn.click()
    log(f"  → Push button clicked for '{playlist_name}'")


def main() -> None:
    if not PASSWORD:
        log("ERROR: M3U4U_PASSWORD environment variable is not set.")
        log("Copy .env.example to .env and fill in your password.")
        sys.exit(1)

    with sync_playwright() as p:
        log("Launching Chromium (non-headless so Cloudflare Turnstile can pass)...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        try:
            # ── Login ─────────────────────────────────────────────────────────────
            log("Navigating to https://m3u4u.com/login ...")
            page.goto("https://m3u4u.com/login", wait_until="domcontentloaded")

            log("Waiting for login form...")
            page.wait_for_selector("input[type='email']", timeout=30_000)

            log(f"Filling email: {EMAIL}")
            page.fill("input[type='email']", EMAIL)

            log("Filling password...")
            page.fill("input[type='password']", PASSWORD)

            log("Clicking login button...")
            page.locator("button[type='submit']").click()

            log("Waiting for playlists page to render...")
            # Wait for at least one playlist row — covers both mat-table and plain table
            page.wait_for_selector("mat-row, tr.mat-row", timeout=60_000)
            time.sleep(2)  # allow Angular to finish rendering all rows
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
                screenshot_path = "error_screenshot.png"
                page.screenshot(path=screenshot_path)
                log(f"Screenshot saved → {screenshot_path}")
            except Exception:
                pass
            sys.exit(1)

        finally:
            browser.close()
            log("Browser closed.")


if __name__ == "__main__":
    main()

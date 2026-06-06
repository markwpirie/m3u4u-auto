# m3u4u Auto Sync

Automates syncing and Dropbox-pushing two m3u4u playlists using Python + Playwright.

**What it does, in order:**
1. Logs into m3u4u.com (Cloudflare Turnstile solved automatically via Capsolver)
2. Syncs **Silver-Surf - Copy** → waits 15s → pushes to Dropbox
3. Waits 45s
4. Syncs **MARK Small List** → waits 15s → pushes to Dropbox

Total runtime: ~2.5 minutes.

---

## Prerequisites

- Python 3.9+
- A [Capsolver](https://capsolver.com) account and API key (used to auto-solve the Cloudflare CAPTCHA)
- A Dropbox connection already configured in your m3u4u account

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/markwpirie/m3u4u-auto.git
cd m3u4u-auto

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Playwright's Chromium browser
playwright install chromium
```

---

## Configuration

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials:

```
M3U4U_PASSWORD=your_m3u4u_password
CAPSOLVER_API_KEY=your_capsolver_api_key
```

The `.env` file is git-ignored and will never be committed.

---

## Running

### One-click (recommended)

Double-click **m3u4u Sync** on your Desktop. Terminal opens, the browser handles the CAPTCHA automatically, and everything runs to completion.

> **First time only:** macOS may block the script. Go to **System Settings → Privacy & Security** and click **Open Anyway**, then double-click again.

To put the shortcut back if you ever lose it:

```bash
cp /Users/marksMAC/Documents/GitHub/m3u4u_auto/run.command ~/Desktop/m3u4u\ Sync.command
chmod +x ~/Desktop/m3u4u\ Sync.command
```

### From terminal

```bash
cd /Users/marksMAC/Documents/GitHub/m3u4u_auto
source .venv/bin/activate
python sync.py
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `M3U4U_PASSWORD is not set` | Check `.env` exists in the project root with both keys filled in |
| `CAPSOLVER_API_KEY is not set` | Same — check `.env` |
| Cloudflare not solved | Check your Capsolver balance; the API key may have expired |
| Login fails after CAPTCHA | Verify your password works in a real browser |
| Row not found | The playlist name in `sync.py` must exactly match the name on the site |
| Confirmation dialog timeout | The site UI may have changed — check `error_screenshot.png` |
| Script won't open on double-click | Run `chmod +x ~/Desktop/m3u4u\ Sync.command` in Terminal |

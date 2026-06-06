# m3u4u Auto Sync

Automates syncing and Dropbox-pushing two m3u4u playlists using Python + Playwright.

**What it does, in order:**
1. Logs into m3u4u.com
2. Syncs **Silver-Surf - Copy**
3. Syncs **MARK Small List**
4. Pushes **Silver-Surf - Copy** to Dropbox
5. Pushes **MARK Small List** to Dropbox

Each operation is separated by a 60-second wait. Total runtime is ~5–6 minutes.

The browser runs in **non-headless mode** so Cloudflare's Turnstile challenge can pass automatically.

---

## Prerequisites

- Python 3.9+
- pip
- A logged-in Dropbox connection already configured in your m3u4u account

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

Open `.env` and replace `your_password_here` with your actual m3u4u password:

```
M3U4U_PASSWORD=your_actual_password
```

The `.env` file is git-ignored and will never be committed.

---

## Running manually

```bash
source .venv/bin/activate   # if not already activated
python sync.py
```

A Chromium window will open. Watch the terminal for step-by-step progress. If anything fails, `error_screenshot.png` is saved in the project folder.

---

## Scheduling on macOS

Because Playwright opens a real browser window, the script must run while your Mac is **awake and has an active GUI session** (screen locked is fine; screen saver is fine; logged-out is not).

### Option A — launchd (recommended)

launchd runs in your login session and handles GUI apps reliably.

1. Create the plist:

```bash
mkdir -p ~/Library/LaunchAgents
```

Save the following as `~/Library/LaunchAgents/com.markwpirie.m3u4u-sync.plist`, adjusting paths as needed:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.markwpirie.m3u4u-sync</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/marksMAC/Documents/GitHub/m3u4u_auto/.venv/bin/python</string>
        <string>/Users/marksMAC/Documents/GitHub/m3u4u_auto/sync.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/marksMAC/Documents/GitHub/m3u4u_auto</string>

    <!-- Run daily at 08:00 -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/marksMAC/Documents/GitHub/m3u4u_auto/sync.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/marksMAC/Documents/GitHub/m3u4u_auto/sync_error.log</string>
</dict>
</plist>
```

2. Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.markwpirie.m3u4u-sync.plist
```

3. Test it immediately (optional):

```bash
launchctl start com.markwpirie.m3u4u-sync
```

4. To unload/disable:

```bash
launchctl unload ~/Library/LaunchAgents/com.markwpirie.m3u4u-sync.plist
```

---

### Option B — cron

cron works but is less reliable for GUI apps on modern macOS. You may also need to grant `cron` Full Disk Access in **System Settings → Privacy & Security → Full Disk Access**.

```bash
crontab -e
```

Add a line (adjust paths, this runs daily at 08:00):

```
0 8 * * * cd /Users/marksMAC/Documents/GitHub/m3u4u_auto && .venv/bin/python sync.py >> sync.log 2>&1
```

> **Note:** If cron runs while no one is logged in, the browser window cannot open and the script will fail. launchd (Option A) is more reliable for this use-case.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `M3U4U_PASSWORD is not set` | Check your `.env` file exists and is in the project root |
| Login fails | Verify your email/password in a real browser first |
| Row not found error | The playlist name in the script must exactly match the name shown on the site |
| Confirmation dialog timeout | The site may have changed its UI — check `error_screenshot.png` |
| Cloudflare challenge stuck | Run manually first; the non-headless browser usually handles it automatically |
| cron job doesn't run | Switch to launchd (Option A); verify with `launchctl list | grep m3u4u` |

import streamlit as st
import time
import os
import json
import subprocess
import sys

COUNTS_FILE = "counts.json"
STATUS_FILE = "status.json"
BOT_FILE = "bot_runner.py"

def load_counts():
    try:
        if os.path.exists(COUNTS_FILE):
            with open(COUNTS_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {}

def load_status():
    try:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {"current_url": None, "phase": "starting", "countdown": 0}

def get_urls():
    if not os.path.exists("website.txt"):
        return []
    with open("website.txt", "r") as f:
        return [line.strip() for line in f if line.strip()]

def is_bot_running():
    if not os.path.exists("bot.pid"):
        return False
    try:
        with open("bot.pid", "r") as f:
            pid = int(f.read().strip())
        # Check if process is alive
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError, FileNotFoundError):
        return False

def start_bot():
    proc = subprocess.Popen(
        [sys.executable, BOT_FILE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    with open("bot.pid", "w") as f:
        f.write(str(proc.pid))
    print(f"[MAIN] Bot started with PID {proc.pid}")

# --- Write bot_runner.py if it doesn't exist ---
BOT_CODE = '''
import time
import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

COUNTS_FILE = "counts.json"
STATUS_FILE = "status.json"
WAIT_SECONDS = 20

def load_counts():
    try:
        if os.path.exists(COUNTS_FILE):
            with open(COUNTS_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {}

def save_counts(counts):
    with open(COUNTS_FILE, "w") as f:
        json.dump(counts, f)
        f.flush()
        os.fsync(f.fileno())

def save_status(current_url=None, phase="idle", countdown=0):
    with open(STATUS_FILE, "w") as f:
        json.dump({"current_url": current_url, "phase": phase, "countdown": countdown}, f)
        f.flush()
        os.fsync(f.fileno())
    print(f"[BOT] phase={phase} | url={current_url} | countdown={countdown}")

def get_urls():
    if not os.path.exists("website.txt"):
        return []
    with open("website.txt", "r") as f:
        return [line.strip() for line in f if line.strip()]

def main():
    save_status(phase="installing_driver")
    print("[BOT] Installing ChromeDriver...")

    try:
        driver_path = ChromeDriverManager().install()
        print(f"[BOT] Driver: {driver_path}")
        save_status(phase="launching_chrome")
    except Exception as e:
        save_status(phase=f"driver_failed: {str(e)[:80]}")
        return

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    try:
        driver = webdriver.Chrome(service=Service(driver_path), options=options)
        print("[BOT] Chrome ready")
        save_status(phase="chrome_ready")
    except Exception as e:
        save_status(phase=f"chrome_failed: {str(e)[:80]}")
        return

    try:
        while True:
            urls = get_urls()
            if not urls:
                save_status(phase="no_urls")
                time.sleep(5)
                continue

            print(f"[BOT] === Cycle start: {len(urls)} URLs ===")
            save_status(phase="cycle_start")
            time.sleep(1)

            for url in urls:
                full_url = url if url.startswith("http") else f"https://{url}"
                print(f"[BOT] Visiting: {full_url}")
                save_status(current_url=url, phase="visiting")

                try:
                    driver.get(full_url)
                    time.sleep(3)

                    wake_button = driver.find_elements(
                        By.XPATH, "//button[contains(., \'Yes, get this app back up!\')]"
                    )

                    counts = load_counts()
                    if url not in counts:
                        counts[url] = 0

                    if wake_button:
                        driver.execute_script("arguments[0].click();", wake_button[0])
                        counts[url] += 1
                        save_counts(counts)
                        save_status(current_url=url, phase="clicked")
                        print(f"[BOT] Clicked on {url} | count={counts[url]}")
                        time.sleep(1)
                    else:
                        save_counts(counts)
                        save_status(current_url=url, phase="no_button")
                        print(f"[BOT] No button: {url}")
                        time.sleep(1)

                except Exception as e:
                    print(f"[BOT] Error on {url}: {e}")
                    save_status(current_url=url, phase=f"error: {str(e)[:60]}")
                    time.sleep(1)

            print(f"[BOT] Cycle done. Waiting {WAIT_SECONDS}s...")
            for remaining in range(WAIT_SECONDS, 0, -1):
                save_status(phase="waiting", countdown=remaining)
                time.sleep(1)

    except Exception as e:
        print(f"[BOT] Crashed: {e}")
        save_status(phase=f"crashed: {str(e)[:80]}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
'''

# Write bot_runner.py to disk on first run
if not os.path.exists(BOT_FILE):
    with open(BOT_FILE, "w") as f:
        f.write(BOT_CODE)
    print("[MAIN] Wrote bot_runner.py")

# Start bot process if not already running
if not is_bot_running():
    start_bot()

# --- UI ---
st.set_page_config(page_title="Auto-Awakener Dashboard", page_icon="⚡", layout="centered")
st.title("⚡ Auto-Awakener Status Dashboard")
st.caption("Refreshes every 3 seconds.")

urls = get_urls()
status = load_status()
counts = load_counts()

phase = status.get("phase", "unknown")
current_url = status.get("current_url")
countdown = status.get("countdown", 0)

st.caption(f"🔧 phase: `{phase}` | bot running: `{is_bot_running()}`")

# --- Status Banner ---
if phase == "visiting":
    st.info(f"🔍 Visiting: **{current_url}**")
elif phase == "clicked":
    st.success(f"✅ Clicked on: **{current_url}**")
elif phase == "no_button":
    st.warning(f"🔘 No button on: **{current_url}**")
elif phase == "waiting":
    st.info(f"⏳ Next cycle in **{countdown}s**...")
elif phase == "cycle_start":
    st.info("🔄 Starting new cycle...")
elif phase == "no_urls":
    st.warning("⚠️ website.txt is empty or missing.")
elif phase == "installing_driver":
    st.info("📦 Installing ChromeDriver...")
elif phase == "launching_chrome":
    st.info("🌐 Launching Chrome...")
elif phase == "chrome_ready":
    st.info("✅ Chrome ready, first cycle starting...")
elif phase == "starting":
    st.info("🚀 Bot starting...")
elif any(x in phase for x in ["failed", "crashed", "error"]):
    st.error(f"❌ {phase}")
else:
    st.info(f"🤖 {phase}")

st.divider()

if not urls:
    st.warning("⚠️ `website.txt` is missing or empty.")
else:
    rows = []
    for url in urls:
        is_current = (url == current_url and phase == "visiting")
        rows.append({
            "Status": "🔍 Now" if is_current else "⏸️",
            "Website": url,
            "Wake-up Clicks": counts.get(url, 0),
        })

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.TextColumn("", width="small"),
            "Website": st.column_config.TextColumn("🌐 Website", width="large"),
            "Wake-up Clicks": st.column_config.NumberColumn("🖱️ Clicks", width="small"),
        }
    )

    st.metric("Total Wake-up Clicks", sum(r["Wake-up Clicks"] for r in rows))

time.sleep(3)
st.rerun()

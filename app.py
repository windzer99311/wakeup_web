import streamlit as st
import threading
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

_bot_thread = None
_bot_lock = threading.Lock()

def load_counts():
    try:
        if os.path.exists(COUNTS_FILE):
            with open(COUNTS_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {}

def save_counts(counts):
    try:
        with open(COUNTS_FILE, "w") as f:
            json.dump(counts, f)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"[SAVE_COUNTS ERROR] {e}")

def load_status():
    try:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {"current_url": None, "phase": "starting", "countdown": 0}

def save_status(current_url=None, phase="idle", countdown=0):
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump({"current_url": current_url, "phase": phase, "countdown": countdown}, f)
            f.flush()
            os.fsync(f.fileno())
        print(f"[STATUS] phase={phase} url={current_url} countdown={countdown}")
    except Exception as e:
        print(f"[SAVE_STATUS ERROR] {e}")

def get_urls():
    if not os.path.exists("website.txt"):
        return []
    with open("website.txt", "r") as f:
        return [line.strip() for line in f if line.strip()]

def bot_worker():
    print("[BOT] ===== Thread entered =====")
    save_status(phase="thread_alive")

    print("[BOT] Installing ChromeDriver...")
    save_status(phase="installing_driver")

    try:
        driver_path = ChromeDriverManager().install()
        print(f"[BOT] ChromeDriver path: {driver_path}")
        save_status(phase="driver_installed")
    except Exception as e:
        print(f"[BOT] ChromeDriverManager failed: {e}")
        save_status(phase=f"driver_install_failed: {str(e)[:80]}")
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

    print("[BOT] Launching Chrome...")
    save_status(phase="launching_chrome")

    try:
        driver = webdriver.Chrome(service=Service(driver_path), options=options)
        print("[BOT] Chrome launched successfully")
        save_status(phase="chrome_ready")
    except Exception as e:
        print(f"[BOT] Chrome launch failed: {e}")
        save_status(phase=f"chrome_failed: {str(e)[:80]}")
        return

    try:
        while True:
            urls = get_urls()
            if not urls:
                save_status(phase="no_urls")
                print("[BOT] No URLs found, sleeping 5s")
                time.sleep(5)
                continue

            print(f"[BOT] === New cycle: {len(urls)} URLs ===")
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
                        By.XPATH, "//button[contains(., 'Yes, get this app back up!')]"
                    )

                    counts = load_counts()
                    if url not in counts:
                        counts[url] = 0

                    if wake_button:
                        driver.execute_script("arguments[0].click();", wake_button[0])
                        counts[url] += 1
                        save_counts(counts)
                        save_status(current_url=url, phase="clicked")
                        print(f"[BOT] Clicked on {url}, total={counts[url]}")
                        time.sleep(1)
                    else:
                        save_counts(counts)
                        save_status(current_url=url, phase="no_button")
                        print(f"[BOT] No button on {url}")
                        time.sleep(1)

                except Exception as e:
                    err = str(e)[:60]
                    print(f"[BOT] Error on {url}: {e}")
                    save_status(current_url=url, phase=f"error: {err}")
                    time.sleep(1)

            print("[BOT] Cycle done. Waiting 60s...")
            for remaining in range(60, 0, -1):
                save_status(phase="waiting", countdown=remaining)
                time.sleep(1)

    except Exception as e:
        print(f"[BOT] Loop crashed: {e}")
        save_status(phase=f"crashed: {str(e)[:80]}")
    finally:
        print("[BOT] Quitting driver")
        driver.quit()


def ensure_bot_running():
    global _bot_thread
    with _bot_lock:
        if _bot_thread is None or not _bot_thread.is_alive():
            print("[MAIN] Starting bot thread")
            _bot_thread = threading.Thread(target=bot_worker, daemon=True)
            _bot_thread.start()
            print(f"[MAIN] Thread alive: {_bot_thread.is_alive()}")


ensure_bot_running()

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

# --- Raw phase always visible for debugging ---
st.caption(f"🔧 Raw phase: `{phase}`")

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
elif phase == "thread_alive":
    st.info("🧵 Thread started, initializing...")
elif phase == "installing_driver":
    st.info("📦 Installing ChromeDriver (one-time, may take 30s)...")
elif phase == "driver_installed":
    st.info("✅ ChromeDriver installed, launching Chrome...")
elif phase == "launching_chrome":
    st.info("🌐 Launching Chrome browser...")
elif phase == "chrome_ready":
    st.info("✅ Chrome ready, starting first cycle...")
elif phase == "starting":
    st.info("🚀 Bot starting up...")
elif "failed" in phase or "crashed" in phase or "error" in phase:
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

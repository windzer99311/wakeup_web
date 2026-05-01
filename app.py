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

# Global thread guard - lives in process memory, not session state
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
    with open(COUNTS_FILE, "w") as f:
        json.dump(counts, f)

def load_status():
    try:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {"current_url": None, "phase": "starting", "countdown": 0}

def save_status(current_url=None, phase="idle", countdown=0):
    with open(STATUS_FILE, "w") as f:
        json.dump({"current_url": current_url, "phase": phase, "countdown": countdown}, f)

def get_urls():
    if not os.path.exists("website.txt"):
        return []
    with open("website.txt", "r") as f:
        return [line.strip() for line in f if line.strip()]

def bot_worker():
    print("[BOT] Thread started")
    save_status(phase="starting")

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
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        print("[BOT] Chrome driver ready")
    except Exception as e:
        print(f"[BOT] Driver failed: {e}")
        save_status(phase=f"driver_error: {str(e)[:80]}")
        return

    try:
        while True:
            urls = get_urls()
            if not urls:
                save_status(phase="no_urls")
                time.sleep(5)
                continue

            print(f"[BOT] Starting cycle with {len(urls)} URLs")
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
                        print(f"[BOT] Clicked button on {url}")
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

            print("[BOT] Cycle done, waiting 60s")
            for remaining in range(60, 0, -1):
                save_status(phase="waiting", countdown=remaining)
                time.sleep(1)

    except Exception as e:
        print(f"[BOT] Crashed: {e}")
        save_status(phase=f"crashed: {str(e)[:80]}")
    finally:
        driver.quit()


def ensure_bot_running():
    global _bot_thread
    with _bot_lock:
        if _bot_thread is None or not _bot_thread.is_alive():
            print("[MAIN] Spawning bot thread")
            _bot_thread = threading.Thread(target=bot_worker, daemon=True)
            _bot_thread.start()


# --- Ensure bot is running ---
ensure_bot_running()

# --- UI ---
st.set_page_config(page_title="Auto-Awakener Dashboard", page_icon="⚡", layout="centered")
st.title("⚡ Auto-Awakener Status Dashboard")
st.caption("Read-only dashboard. Refreshes every 3 seconds.")

urls = get_urls()
status = load_status()
counts = load_counts()

phase = status.get("phase", "starting")
current_url = status.get("current_url")
countdown = status.get("countdown", 0)

# --- Status Banner ---
if phase == "visiting":
    st.info(f"🔍 Visiting: **{current_url}**")
elif phase == "clicked":
    st.success(f"✅ Button clicked on: **{current_url}**")
elif phase == "no_button":
    st.warning(f"🔘 No button found on: **{current_url}**")
elif phase == "waiting":
    st.info(f"⏳ Cycle complete. Next cycle in **{countdown}s**...")
elif phase == "cycle_start":
    st.info("🔄 Starting new cycle...")
elif phase == "no_urls":
    st.warning("⚠️ `website.txt` is empty or missing.")
elif phase == "starting":
    st.info("🚀 Bot is starting up, please wait...")
elif phase.startswith("driver_error"):
    st.error(f"🚫 Chrome driver failed: {phase}")
elif phase.startswith("error:"):
    st.error(f"⚠️ {phase} on **{current_url}**")
elif phase.startswith("crashed"):
    st.error(f"💀 {phase}")
else:
    st.info(f"🤖 Status: {phase}")

st.divider()

# --- Table ---
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

    total = sum(r["Wake-up Clicks"] for r in rows)
    st.metric("Total Wake-up Clicks", total)

time.sleep(3)
st.rerun()

import streamlit as st
import time
import os
import json
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- FILE PATHS ---
STATUS_FILE = "status.json"
COUNTS_FILE = "counts.json"
WEBSITE_FILE = "website.txt"

# --- PERSISTENCE LOGIC ---
def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)

# --- THE BACKGROUND WORKER ---
def worker_loop():
    """Background thread that manages Selenium independently of the UI."""
    save_json(STATUS_FILE, {"state": "Startup", "detail": "Initializing browser engine..."})
    
    # Configure Chrome Options for Cloud Linux
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.binary_location = "/usr/bin/chromium"
    
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        save_json(STATUS_FILE, {"state": "Startup", "detail": "Browser ready. Starting cycles..."})
    except Exception as e:
        save_json(STATUS_FILE, {"state": "Error", "detail": f"Browser failed: {str(e)[:50]}"})
        return

    while True:
        try:
            if not os.path.exists(WEBSITE_FILE):
                save_json(STATUS_FILE, {"state": "Waiting", "detail": "Missing website.txt"})
                time.sleep(10)
                continue
                
            with open(WEBSITE_FILE, "r") as f:
                urls = [l.strip() for l in f if l.strip()]
            
            counts = load_json(COUNTS_FILE)

            for url in urls:
                target = url if url.startswith("http") else f"https://{url}"
                save_json(STATUS_FILE, {"state": "Visiting", "detail": target})
                
                try:
                    driver.get(target)
                    time.sleep(5) # Give page time to load
                    
                    # Search for the wake-up button
                    btn = driver.find_elements(By.XPATH, "//button[contains(., 'Yes, get this app back up!')]")
                    if btn:
                        driver.execute_script("arguments[0].click();", btn[0])
                        counts[url] = counts.get(url, 0) + 1
                        save_json(COUNTS_FILE, counts)
                except:
                    continue

            save_json(STATUS_FILE, {"state": "Waiting", "detail": "Cycle finished. Sleeping 30s."})
            time.sleep(30)
            
        except Exception as e:
            save_json(STATUS_FILE, {"state": "Error", "detail": f"Loop error: {str(e)[:50]}"})
            time.sleep(10)

# --- THREAD MANAGEMENT ---
def ensure_worker_alive():
    """Ensures exactly one background thread is running at all times."""
    is_alive = any(t.name == "AwakenerWorker" for t in threading.enumerate())
    if not is_alive:
        t = threading.Thread(target=worker_loop, name="AwakenerWorker", daemon=True)
        t.start()

# --- STREAMLIT UI ---
st.set_page_config(page_title="24/7 Global Awakener", page_icon="🤖")

# Kickstart the background process
ensure_worker_alive()

st.title("🤖 Live Global Bot Status")
st.write("This bot runs in the background. Counts persist across refreshes.")

# Load and Display Global Status
status = load_json(STATUS_FILE)
state = status.get("state", "Starting")
detail = status.get("detail", "Initializing worker thread...")

if state == "Visiting":
    st.info(f"🛰️ **Current Action:** Visiting {detail}")
elif state == "Waiting":
    st.success(f"💤 **Status:** {detail}")
elif state == "Error":
    st.error(f"⚠️ **Status:** {detail}")
else:
    st.warning(f"🕒 **Status:** {state} - {detail}")

st.divider()

# Display Statistics Table
st.subheader("Wake-up Statistics")
counts = load_json(COUNTS_FILE)
if counts:
    st.table([{"URL": k, "Clicks": v} for k, v in counts.items()])
else:
    st.info("No clicks recorded yet. Monitoring in progress...")

# UI Auto-refresh every 10 seconds to show latest global status
time.sleep(10)
st.rerun()

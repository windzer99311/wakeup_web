import streamlit as st
import time
import os
import json
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- CONFIG ---
STATUS_FILE = "status.json"
COUNTS_FILE = "counts.json"
WEBSITE_FILE = "website.txt"

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_json(path, data):
    with open(path, "w") as f: json.dump(data, f)

# --- BACKGROUND WORKER ---
def worker_loop():
    save_json(STATUS_FILE, {"state": "Initializing", "detail": "Starting Browser..."})
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = "/usr/bin/chromium"
    
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        save_json(STATUS_FILE, {"state": "Error", "detail": f"Browser Crash: {str(e)}"})
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
                    time.sleep(5)
                    btn = driver.find_elements(By.XPATH, "//button[contains(., 'Yes, get this app back up!')]")
                    if btn:
                        driver.execute_script("arguments[0].click();", btn[0])
                        counts[url] = counts.get(url, 0) + 1
                        save_json(COUNTS_FILE, counts)
                except: continue

            save_json(STATUS_FILE, {"state": "Waiting", "detail": "Cycle finished. Sleeping 30s."})
            time.sleep(30)
        except Exception as e:
            save_json(STATUS_FILE, {"state": "Error", "detail": f"Loop error: {str(e)}"})
            time.sleep(10)

# --- THREAD MANAGER ---
def ensure_worker_alive():
    is_alive = any(t.name == "AwakenerWorker" for t in threading.enumerate())
    if not is_alive:
        t = threading.Thread(target=worker_loop, name="AwakenerWorker", daemon=True)
        t.start()

# --- UI ---
st.set_page_config(page_title="24/7 Awakener", page_icon="🤖")
ensure_worker_alive()

st.title("🤖 Global Awakener Bot")

status = load_json(STATUS_FILE)
state = status.get("state", "Starting")
detail = status.get("detail", "Initializing worker...")

if state == "Visiting":
    st.info(f"🛰️ **Currently Visiting:** {detail}")
elif state == "Waiting":
    st.success(f"💤 **Status:** {detail}")
else:
    st.warning(f"⚠️ **Status:** {state} - {detail}")

st.divider()
st.subheader("Persistent Statistics")
counts = load_json(COUNTS_FILE)
if counts:
    st.table([{"URL": k, "Clicks": v} for k, v in counts.items()])

# Refresh UI every 10 seconds
time.sleep(10)
st.rerun()

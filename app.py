import streamlit as st
import time
import os
import json
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- CONFIGURATION ---
COUNTS_FILE = "counts.json"
WEBSITE_FILE = "website.txt"
STATUS_FILE = "status.json"

# --- DATA PERSISTENCE ---
def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f)

def get_urls():
    if not os.path.exists(WEBSITE_FILE):
        return []
    with open(WEBSITE_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]

# --- THE BACKGROUND WORKER ---
def background_worker():
    """This function runs in a separate thread forever, independent of UI."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    
    driver = webdriver.Chrome(service=service, options=options)
    
    while True:
        urls = get_urls()
        counts = load_json(COUNTS_FILE)
        
        if not urls:
            save_json(STATUS_FILE, {"state": "Idle", "detail": "website.txt is empty"})
            time.sleep(10)
            continue

        for url in urls:
            full_url = url if url.startswith("http") else f"https://{url}"
            # Update global status
            save_json(STATUS_FILE, {"state": "Visiting", "detail": full_url})
            
            try:
                driver.get(full_url)
                time.sleep(4) 
                
                wake_button = driver.find_elements(By.XPATH, "//button[contains(., 'Yes, get this app back up!')]")
                
                if wake_button:
                    driver.execute_script("arguments[0].click();", wake_button[0])
                    counts[url] = counts.get(url, 0) + 1
                    save_json(COUNTS_FILE, counts)
                elif url not in counts:
                    counts[url] = 0
                    save_json(COUNTS_FILE, counts)
            except Exception as e:
                print(f"Worker error on {url}: {e}")
        
        # Wait cycle status
        save_json(STATUS_FILE, {"state": "Waiting", "detail": "Sleeping before next cycle"})
        time.sleep(30)

# --- START WORKER ONCE (GLOBAL SCOPE) ---
if "worker_started" not in st.session_state:
    thread_exists = False
    for thread in threading.enumerate():
        if thread.name == "AwakenerWorker":
            thread_exists = True
            break
    
    if not thread_exists:
        t = threading.Thread(target=background_worker, name="AwakenerWorker", daemon=True)
        t.start()
    st.session_state.worker_started = True

# --- STREAMLIT UI ---
st.set_page_config(page_title="24/7 Global Awakener", page_icon="🤖")
st.title("🤖 Live Global Bot Status")

# 1. Show Global Status
status_data = load_json(STATUS_FILE)
current_state = status_data.get("state", "Initializing")
current_detail = status_data.get("detail", "Starting up...")

if current_state == "Visiting":
    st.info(f"**Current Action:** 🛰️ Visiting {current_detail}")
elif current_state == "Waiting":
    st.success(f"**Current Action:** 💤 {current_detail}")
else:
    st.warning(f"**Current Action:** {current_state} - {current_detail}")

st.divider()

# 2. Show Persistent Counts
st.subheader("Wake-up Statistics")
counts = load_json(COUNTS_FILE)
if counts:
    st.table([{"Website": k, "Wake-up Clicks": v} for k, v in counts.items()])
else:
    st.info("No data yet. Waiting for first cycle...")

# 3. Auto-Refresh the UI for the user every 5 seconds
time.sleep(5)
st.rerun()

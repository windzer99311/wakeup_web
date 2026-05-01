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
    """This function runs in a separate thread forever."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.binary_location = "/usr/bin/chromium"
    
    # Update status that we are launching the browser
    save_json(STATUS_FILE, {"state": "Initializing", "detail": "Launching Chromium Browser..."})
    
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        save_json(STATUS_FILE, {"state": "Error", "detail": f"Driver failed: {str(e)}"})
        return

    while True:
        try:
            urls = get_urls()
            counts = load_json(COUNTS_FILE)
            
            if not urls:
                save_json(STATUS_FILE, {"state": "Waiting", "detail": "website.txt is empty"})
                time.sleep(10)
                continue

            for url in urls:
                full_url = url if url.startswith("http") else f"https://{url}"
                save_json(STATUS_FILE, {"state": "Visiting", "detail": full_url})
                
                try:
                    driver.get(full_url)
                    time.sleep(5) 
                    
                    wake_button = driver.find_elements(By.XPATH, "//button[contains(., 'Yes, get this app back up!')]")
                    
                    if wake_button:
                        driver.execute_script("arguments[0].click();", wake_button[0])
                        counts[url] = counts.get(url, 0) + 1
                        save_json(COUNTS_FILE, counts)
                except:
                    pass # Ignore individual page errors
            
            save_json(STATUS_FILE, {"state": "Waiting", "detail": "Cycle complete. Resting..."})
            time.sleep(30)
        except Exception as e:
            save_json(STATUS_FILE, {"state": "Error", "detail": f"Loop error: {str(e)}"})
            time.sleep(10)

# --- WORKER MANAGEMENT ---
def start_worker():
    thread_exists = False
    for thread in threading.enumerate():
        if thread.name == "AwakenerWorker":
            thread_exists = True
            break
    
    if not thread_exists:
        t = threading.Thread(target=background_worker, name="AwakenerWorker", daemon=True)
        t.start()
        return True
    return False

# --- STREAMLIT UI ---
st.set_page_config(page_title="24/7 Global Awakener", page_icon="🤖")

# Attempt to start the worker immediately
start_worker()

st.title("🤖 Live Global Bot Status")

# Load Global Status
status_data = load_json(STATUS_FILE)
current_state = status_data.get("state", "Initializing")
current_detail = status_data.get("detail", "Starting up background worker...")

# Display Status UI
if current_state == "Visiting":
    st.info(f"**Current Action:** 🛰️ Visiting {current_detail}")
elif current_state == "Waiting":
    st.success(f"**Current Action:** 💤 {current_detail}")
elif current_state == "Error":
    st.error(f"**Bot Error:** {current_detail}")
    if st.button("Attempt Manual Restart"):
        save_json(STATUS_FILE, {"state": "Initializing", "detail": "Restarting..."})
        start_worker()
else:
    st.warning(f"**Current Action:** {current_state} - {current_detail}")

st.divider()

# Display Table
st.subheader("Wake-up Statistics")
counts = load_json(COUNTS_FILE)
if counts:
    st.table([{"Website": k, "Wake-up Clicks": v} for k, v in counts.items()])
else:
    st.info("Waiting for first cycle results...")

# Force UI refresh every 10 seconds
time.sleep(10)
st.rerun()

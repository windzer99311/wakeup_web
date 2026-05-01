import streamlit as st
import time
import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- CONFIG ---
COUNTS_FILE = "counts.json"
WEBSITE_FILE = "website.txt"
STATUS_FILE = "status.json" # Global status memory

# --- PERSISTENCE ---
def load_json(path):
    if os.path.exists(path):
        try: 
            with open(path, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_json(path, data):
    with open(path, "w") as f: json.dump(data, f)

# --- BROWSER ENGINE ---
@st.cache_resource
def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)

# --- THE BOT FRAGMENT ---
@st.fragment(run_every=2.0) # Runs the check every 2 seconds
def bot_worker():
    # Load global progress from the file
    global_status = load_json(STATUS_FILE)
    last_run_time = global_status.get("last_run", 0)
    
    current_time = time.time()
    
    # Run a new cycle every 60 seconds
    if current_time - last_run_time > 60:
        if not os.path.exists(WEBSITE_FILE):
            save_json(STATUS_FILE, {"state": "Error", "detail": "website.txt missing", "last_run": last_run_time})
            return

        with open(WEBSITE_FILE, "r") as f:
            urls = [l.strip() for l in f if l.strip()]

        driver = get_driver()
        counts = load_json(COUNTS_FILE)

        for url in urls:
            target = url if url.startswith("http") else f"https://{url}"
            # Update GLOBAL status file so it's visible on refresh
            save_json(STATUS_FILE, {"state": "Visiting", "detail": target, "last_run": last_run_time})
            
            try:
                driver.get(target)
                time.sleep(5)
                btn = driver.find_elements(By.XPATH, "//button[contains(., 'Yes, get this app back up!')]")
                if btn:
                    driver.execute_script("arguments[0].click();", btn[0])
                    counts[url] = counts.get(url, 0) + 1
                    save_json(COUNTS_FILE, counts)
            except:
                continue
        
        # Cycle finished: Update the last run time globally
        save_json(STATUS_FILE, {"state": "Waiting", "detail": "Cycle Complete. Resting...", "last_run": current_time})
        st.rerun()

# --- MAIN UI ---
st.set_page_config(page_title="24/7 Awakener", page_icon="🤖")

st.title("🤖 Global Bot Dashboard")

# Load Global Status from File
global_status = load_json(STATUS_FILE)
state = global_status.get("state", "Starting")
detail = global_status.get("detail", "Initializing...")

# Display global status (survives refreshes)
if state == "Visiting":
    st.info(f"🛰️ **Current Action:** {detail}")
else:
    st.success(f"💤 **Status:** {detail}")

st.divider()

# Display Statistics Table
st.subheader("Wake-up Statistics")
counts = load_json(COUNTS_FILE)
if counts:
    st.table([{"URL": k, "Clicks": v} for k, v in counts.items()])

# Call the fragment
bot_worker()

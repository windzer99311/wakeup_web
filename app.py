import streamlit as st
import time
import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
# Import the autorefresh component
from streamlit_autorefresh import st_autorefresh

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

# --- HELPER TO CLEAN NAME FOR STATUS ONLY ---
def get_app_name(url):
    name = url
    return name

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
@st.fragment(run_every=2.0) 
def bot_worker():
    global_status = load_json(STATUS_FILE)
    last_run_time = global_status.get("last_run", 0)
    current_time = time.time()
    
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
            # Keep status message clean
            save_json(STATUS_FILE, {"state": "Visiting", "detail": get_app_name(target), "last_run": last_run_time})
            
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
        
        save_json(STATUS_FILE, {"state": "Waiting", "detail": "Cycle Complete. Resting...", "last_run": current_time})
        st.rerun()

# --- MAIN UI ---
st.set_page_config(page_title="24/7 Awakener", page_icon="🤖")

# --- AUTO-REFRESHER ---
# Refreshes the dashboard every 5 seconds to show real-time progress
st_autorefresh(interval=5000, key="datarefresh")

st.title("🤖 Global Bot Dashboard")

global_status = load_json(STATUS_FILE)
state = global_status.get("state", "Starting")
detail = global_status.get("detail", "Initializing...")

if state == "Visiting":
    st.info(f"🛰️ **Current Action:** Visiting {detail}")
else:
    st.success(f"💤 **Status:** {detail}")

st.divider()

st.subheader("Wake-up Statistics")

if os.path.exists(WEBSITE_FILE):
    with open(WEBSITE_FILE, "r") as f:
        current_urls = [l.strip() for l in f if l.strip()]
    
    counts = load_json(COUNTS_FILE)
    
    table_data = []
    for url in current_urls:
        click_count = counts.get(url, 0)
        # Showing the full URL as stored in website.txt
        table_data.append({"URL": url, "Clicks": click_count})
    
    if table_data:
        st.table(table_data)
    else:
        st.info("No websites found in website.txt.")
else:
    st.error("website.txt not found.")

bot_worker()

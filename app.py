import streamlit as st
import time
import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from streamlit_autorefresh import st_autorefresh

# --- CONFIG ---
COUNTS_FILE = "counts.json"
WEBSITE_FILE = "website.txt"
STATUS_FILE = "status.json"

# --- PERSISTENCE ---
def load_json(path):
    if os.path.exists(path):
        try: 
            with open(path, "r") as f: 
                data = json.load(f)
                return data
        except: return {}
    return {}

def save_json(path, data):
    with open(path, "w") as f: 
        json.dump(data, f)

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
    # Load fresh status every 2 seconds
    global_status = load_json(STATUS_FILE)
    
    # 'b' value from your logic
    next_run_at = float(global_status.get("next_run_at", 0))
    current_time = time.time()
    
    # Check: Is it time to start the loop? (current time > b)
    if current_time >= next_run_at:
        if not os.path.exists(WEBSITE_FILE):
            return

        with open(WEBSITE_FILE, "r") as f:
            urls = [l.strip() for l in f if l.strip()]

        driver = get_driver()
        counts = load_json(COUNTS_FILE)

        for url in urls:
            target = url if url.startswith("http") else f"https://{url}"
            # Update status to show trace
            save_json(STATUS_FILE, {
                "state": "Visiting", 
                "detail": target, 
                "next_run_at": next_run_at 
            })
            
            try:
                driver.get(target)
                time.sleep(5) # Wait for page load
                btn = driver.find_elements(By.XPATH, "//button[contains(., 'Yes, get this app back up!')]")
                if btn:
                    driver.execute_script("arguments[0].click();", btn[0])
                    counts[url] = counts.get(url, 0) + 1
                    save_json(COUNTS_FILE, counts)
            except:
                continue
        
        # --- END OF LOOP LOGIC ---
        # Note the finish time and add 60 seconds
        finished_at = time.time()
        new_b = finished_at + 60 
        
        save_json(STATUS_FILE, {
            "state": "Waiting", 
            "detail": f"Resting until {time.strftime('%H:%M:%S', time.localtime(new_b))}", 
            "next_run_at": new_b
        })
        # Force the UI to update immediately after the loop
        st.rerun()

# --- MAIN UI ---
st.set_page_config(page_title="24/7 Awakener", page_icon="🤖")

# Keep the UI alive and tracing the status
st_autorefresh(interval=5000, key="ui_refresh")

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
    table_data = [{"URL": url, "Clicks": counts.get(url, 0)} for url in current_urls]
    st.table(table_data)

bot_worker()

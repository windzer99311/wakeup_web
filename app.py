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
@st.experimental_fragment(run_every=1.0)
def bot_worker():
    # Check if we should run the next cycle
    if "last_run" not in st.session_state:
        st.session_state.last_run = 0
    
    current_time = time.time()
    
    # Run every 60 seconds
    if current_time - st.session_state.last_run > 60:
        if not os.path.exists(WEBSITE_FILE):
            st.session_state.status = "Error: website.txt missing"
            return

        with open(WEBSITE_FILE, "r") as f:
            urls = [l.strip() for l in f if l.strip()]

        driver = get_driver()
        counts = load_json(COUNTS_FILE)

        for url in urls:
            target = url if url.startswith("http") else f"https://{url}"
            st.session_state.status = f"🛰️ Visiting: {target}"
            
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
        
        st.session_state.last_run = current_time
        st.session_state.status = "💤 Cycle Complete. Waiting..."
        st.rerun()

# --- MAIN UI ---
st.set_page_config(page_title="24/7 Awakener", page_icon="🤖")

if "status" not in st.session_state:
    st.session_state.status = "Initializing..."

st.title("🤖 Live Bot Status")

# Display Status
if "Visiting" in st.session_state.status:
    st.info(st.session_state.status)
else:
    st.success(st.session_state.status)

st.divider()

# Display Table
st.subheader("Wake-up Statistics")
counts = load_json(COUNTS_FILE)
if counts:
    st.table([{"URL": k, "Clicks": v} for k, v in counts.items()])

# Start the worker fragment
bot_worker()

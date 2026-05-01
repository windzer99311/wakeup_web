import streamlit as st
import time
import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- CONFIGURATION ---
COUNTS_FILE = "counts.json"

# --- HELPER FUNCTIONS ---
def load_counts():
    if os.path.exists(COUNTS_FILE):
        with open(COUNTS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_counts(counts):
    with open(COUNTS_FILE, "w") as f:
        json.dump(counts, f)

def get_urls():
    if not os.path.exists("website.txt"):
        return []
    with open("website.txt", "r") as f:
        return [line.strip() for line in f if line.strip()]

# --- PAGE CONFIG ---
st.set_page_config(page_title="24/7 Auto-Awakener", page_icon="🚀")

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

# --- MAIN UI ---
st.title("🚀 24/7 Persistent Awakener")
st.write("Counts are saved to disk. They will not reset on refresh.")

status_msg = st.empty()
table_placeholder = st.empty()

# --- EXECUTION ---
driver = get_driver()
counts = load_counts()
urls = get_urls()

if not urls:
    st.warning("Please add URLs to website.txt")
    time.sleep(10)
    st.rerun()

# Run one cycle
for url in urls:
    full_url = url if url.startswith("http") else f"https://{url}"
    status_msg.info(f"Checking: {full_url}...")
    
    try:
        driver.get(full_url)
        time.sleep(3) 
        
        wake_button = driver.find_elements(By.XPATH, "//button[contains(., 'Yes, get this app back up!')]")
        
        if wake_button:
            driver.execute_script("arguments[0].click();", wake_button[0])
            # Update and Save immediately to disk
            counts[url] = counts.get(url, 0) + 1
            save_counts(counts)
        elif url not in counts:
            counts[url] = 0
            save_counts(counts)
            
    except Exception as e:
        print(f"Error: {e}")

    # Display live data from the JSON file
    table_placeholder.table([
        {"Website": k, "Wake-up Clicks": v} 
        for k, v in counts.items()
    ])

status_msg.success("Cycle complete. Re-running in 15s...")
time.sleep(15)
st.rerun()

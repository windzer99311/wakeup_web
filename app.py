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

# --- DATA PERSISTENCE ---
def load_counts():
    if os.path.exists(COUNTS_FILE):
        try:
            with open(COUNTS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_counts(counts):
    with open(COUNTS_FILE, "w") as f:
        json.dump(counts, f)

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
    service = Service("/usr/bin/chromedriver")
    
    driver = webdriver.Chrome(service=service, options=options)
    
    while True:
        urls = get_urls()
        counts = load_counts()
        
        for url in urls:
            full_url = url if url.startswith("http") else f"https://{url}"
            try:
                driver.get(full_url)
                time.sleep(4) 
                
                wake_button = driver.find_elements(By.XPATH, "//button[contains(., 'Yes, get this app back up!')]")
                
                if wake_button:
                    driver.execute_script("arguments[0].click();", wake_button[0])
                    counts[url] = counts.get(url, 0) + 1
                    save_counts(counts)
                elif url not in counts:
                    counts[url] = 0
                    save_counts(counts)
            except Exception as e:
                print(f"Worker error on {url}: {e}")
        
        time.sleep(20) # Wait before next global cycle

# --- START WORKER ONCE ---
if "worker_started" not in st.session_state:
    # Check if a thread is already running in the global scope to prevent duplicates
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
st.set_page_config(page_title="24/7 Background Awakener", page_icon="🤖")
st.title("🤖 Background Bot Dashboard")
st.write("The bot is running as a background thread. You can close this tab or refresh; the bot will keep working.")

# Auto-refresh the UI every 10 seconds to show new counts
st.empty() 
counts = load_counts()

if counts:
    st.table([{"Website": k, "Wake-up Clicks": v} for k, v in counts.items()])
else:
    st.info("Waiting for first cycle to complete...")

# This small script tells the browser to refresh the UI only
time.sleep(10)
st.rerun()

import streamlit as st
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- PAGE CONFIG ---
st.set_page_config(page_title="Auto-Awakener Bot", page_icon="⚡")

# Use st.cache_resource to keep the driver alive across reruns
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

# Initialize counts in session state
if 'click_counts' not in st.session_state:
    st.session_state.click_counts = {}

def get_urls():
    if not os.path.exists("website.txt"):
        return []
    with open("website.txt", "r") as f:
        return [line.strip() for line in f if line.strip()]

st.title("⚡ Streamlit Auto-Awakener")

# --- UI DISPLAY ---
table_placeholder = st.empty()
status_msg = st.empty()

# Show current counts immediately
table_placeholder.table([
    {"Website": k, "Wake-up Clicks": v} 
    for k, v in st.session_state.click_counts.items()
])

# --- EXECUTION ---
driver = get_driver()
urls = get_urls()

if not urls:
    st.warning("website.txt is empty.")
else:
    # We check each URL once per script execution
    for url in urls:
        full_url = url if url.startswith("http") else f"https://{url}"
        status_msg.info(f"Checking: {full_url}...")
        
        try:
            driver.get(full_url)
            time.sleep(3) 
            
            wake_button = driver.find_elements(By.XPATH, "//button[contains(., 'Yes, get this app back up!')]")
            
            if wake_button:
                driver.execute_script("arguments[0].click();", wake_button[0])
                # UPDATE STATE
                st.session_state.click_counts[url] = st.session_state.click_counts.get(url, 0) + 1
                status_msg.success(f"✅ Clicked button for {url}")
            else:
                if url not in st.session_state.click_counts:
                    st.session_state.click_counts[url] = 0
                    
        except Exception as e:
            print(f"Error: {e}")

    # Refresh the table display before the rerun
    table_placeholder.table([
        {"Website": k, "Wake-up Clicks": v} 
        for k, v in st.session_state.click_counts.items()
    ])

    # Wait 15 seconds then RERUN the entire script to update the UI
    time.sleep(15)
    st.rerun()

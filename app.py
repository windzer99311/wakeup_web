import streamlit as st
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- PAGE CONFIG ---
st.set_page_config(page_title="Auto-Awakener Bot", page_icon="⚡")

# --- INITIALIZE SESSION STATE ---
if 'click_counts' not in st.session_state:
    st.session_state.click_counts = {}

def get_urls():
    if not os.path.exists("website.txt"):
        return []
    with open("website.txt", "r") as f:
        return [line.strip() for line in f if line.strip()]

# --- MAIN INTERFACE ---
st.title("⚡ Streamlit Auto-Awakener")
st.write("The bot is running. Refresh this page to see updated counts.")

status_msg = st.empty()
table_placeholder = st.empty()

# --- SELENIUM SETUP FOR STREAMLIT CLOUD ---
options = Options()
options.add_argument("--headless=new") 
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Explicit paths for Chromium on Streamlit Cloud
options.binary_location = "/usr/bin/chromium"
service = Service("/usr/bin/chromedriver")

# Use cache_resource to prevent opening a new browser on every rerun
@st.cache_resource
def get_driver():
    return webdriver.Chrome(service=service, options=options)

try:
    driver = get_driver()
    
    urls = get_urls()
    
    if not urls:
        status_msg.warning("website.txt is empty or missing.")
        time.sleep(10)
        st.rerun() # Re-check file

    for url in urls:
        full_url = url if url.startswith("http") else f"https://{url}"
        status_msg.info(f"Checking: {full_url}...")
        
        try:
            driver.get(full_url)
            time.sleep(3) # Wait for "Sleep" UI to render
            
            # Search for the wake-up button
            wake_button = driver.find_elements(By.XPATH, "//button[contains(., 'Yes, get this app back up!')]")
            
            if wake_button:
                # Click and move to next site immediately
                driver.execute_script("arguments[0].click();", wake_button[0])
                st.session_state.click_counts[url] = st.session_state.click_counts.get(url, 0) + 1
            else:
                if url not in st.session_state.click_counts:
                    st.session_state.click_counts[url] = 0
                    
        except Exception as e:
            print(f"Error checking {url}: {e}")

        # Update the UI table in real-time
        table_placeholder.table([
            {"Website": k, "Wake-up Clicks": v} 
            for k, v in st.session_state.click_counts.items()
        ])
    
    status_msg.success("Cycle complete. Restarting soon...")
    time.sleep(15)
    st.rerun() # THIS LINE TRiggers THE UI UPDATE

except Exception as main_e:
    st.error(f"Critical Bot Error: {main_e}")

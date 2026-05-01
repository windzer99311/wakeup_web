import streamlit as st
import threading
import time
import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

COUNTS_FILE = "counts.json"
LOCK = threading.Lock()

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

def bot_worker():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    try:
        while True:
            urls = get_urls()
            if not urls:
                time.sleep(5)
                continue

            for url in urls:
                full_url = url if url.startswith("http") else f"https://{url}"
                try:
                    driver.get(full_url)
                    time.sleep(3)

                    wake_button = driver.find_elements(
                        By.XPATH, "//button[contains(., 'Yes, get this app back up!')]"
                    )

                    with LOCK:
                        counts = load_counts()
                        if url not in counts:
                            counts[url] = 0
                        if wake_button:
                            driver.execute_script("arguments[0].click();", wake_button[0])
                            counts[url] += 1
                        save_counts(counts)

                except Exception as e:
                    print(f"Error on {url}: {e}")

            time.sleep(10)
    except Exception as e:
        print(f"Bot thread crashed: {e}")
    finally:
        driver.quit()

# --- Start background thread only once ---
if "bot_started" not in st.session_state:
    st.session_state.bot_started = True
    t = threading.Thread(target=bot_worker, daemon=True)
    t.start()

# --- UI ---
st.set_page_config(page_title="Auto-Awakener Dashboard", page_icon="⚡", layout="centered")
st.title("⚡ Auto-Awakener Status Dashboard")
st.caption("Read-only dashboard. Refreshes every 5 seconds.")

urls = get_urls()

if not urls:
    st.warning("⚠️ `website.txt` is missing or empty.")
else:
    with LOCK:
        counts = load_counts()

    rows = []
    for url in urls:
        rows.append({
            "Website": url,
            "Wake-up Clicks": counts.get(url, 0)
        })

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Website": st.column_config.TextColumn("🌐 Website", width="large"),
            "Wake-up Clicks": st.column_config.NumberColumn("🖱️ Wake-up Clicks", width="small"),
        }
    )

    total = sum(r["Wake-up Clicks"] for r in rows)
    st.metric("Total Wake-up Clicks", total)

time.sleep(5)
st.rerun()

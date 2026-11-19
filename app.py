import os

import pandas as pd
import requests
import streamlit as st

# Base URL of the FastAPI app (override with env var BASE_API or .streamlit/secrets.toml)
BASE_API = os.environ.get("BASE_API", "https://windzer007.alwaysdata.net").rstrip("/")
TIMEOUT = 20

st.set_page_config(page_title="Keep-Alive Dashboard", page_icon="💤", layout="wide")


# ---------------------------------------------------------------- API helpers
def api_get(path: str):
    """GET -> parsed JSON, or None (and an on-screen error) if the API is unreachable."""
    try:
        r = requests.get(f"{BASE_API}{path}", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Could not load `{path}` from {BASE_API}: {e}")
        return None


def error_text(r: requests.Response) -> str:
    try:
        return str(r.json().get("detail", r.text))
    except ValueError:
        return r.text[:200]


def flash(kind: str, message: str):
    """Show a message after st.rerun()."""
    st.session_state["flash"] = (kind, message)


def show_flash():
    if "flash" in st.session_state:
        kind, message = st.session_state.pop("flash")
        getattr(st, kind)(message)


def short(site: str) -> str:
    return site.replace("https://", "").replace("http://", "")


# ---------------------------------------------------------------- pages
def page_status_counts():
    st.header("📊 Status checks")
    st.caption("How many times each website's status has been checked (one check per minute).")

    counts = api_get("/count_status")
    if counts is None:
        return
    live = api_get("/status") or {}

    if not counts:
        st.info("No websites yet. Add one from the **Add website** page.")
        return

    df = pd.DataFrame(
        [
            {
                "Website": short(site),
                "Status checks": n,
                "Current state": live.get(site, {}).get("state", "not checked yet"),
            }
            for site, n in counts.items()
        ]
    )
    c1, c2 = st.columns(2)
    c1.metric("Websites", len(df))
    c2.metric("Total status checks", int(df["Status checks"].sum()))

    st.dataframe(df, hide_index=True)


def page_click_count():
    st.header("🖱️ Wake-up clicks")
    st.caption("How many times the wake-up button was clicked for each website.")

    counts = api_get("/click_count")
    if counts is None:
        return
    if not counts:
        st.info("No websites yet. Add one from the **Add website** page.")
        return

    df = pd.DataFrame(
        [{"Website": short(site), "Clicks": n} for site, n in counts.items()]
    )
    c1, c2 = st.columns(2)
    c1.metric("Websites", len(df))
    c2.metric("Total clicks", int(df["Clicks"].sum()))

    st.dataframe(df, hide_index=True)


def page_add_website():
    st.header("➕ Add website")
    show_flash()

    with st.form("add_form", clear_on_submit=True):
        url = st.text_input(
            "Website URL",
            placeholder="https://example.streamlit.app  (trailing / is fine)",
        )
        submitted = st.form_submit_button("Add website")

    if submitted:
        if not url.strip():
            st.warning("Please enter a URL.")
        else:
            try:
                r = requests.post(f"{BASE_API}/websites", json={"url": url}, timeout=TIMEOUT)
                if r.ok:
                    data = r.json()
                    if data["added"]:
                        flash("success", f"Added {data['website']}")
                    else:
                        flash("info", f"{data['website']} is already in the list")
                    st.rerun()
                else:
                    st.error(f"Could not add: {error_text(r)}")
            except requests.RequestException as e:
                st.error(f"API error: {e}")

    st.subheader("Current websites")
    sites = api_get("/websites")
    if sites is not None:
        st.write(f"{len(sites)} website(s)")
        st.dataframe(pd.DataFrame({"Website": sites}), hide_index=True)


def page_delete_website():
    st.header("🗑️ Delete website")
    show_flash()

    sites = api_get("/websites")
    if sites is None:
        return
    if not sites:
        st.info("The list is empty.")
        return

    site = st.selectbox("Choose a website to delete", sites)
    confirm = st.checkbox("Yes, delete this website")
    if st.button("Delete", type="primary", disabled=not confirm):
        try:
            r = requests.delete(f"{BASE_API}/websites", params={"url": site}, timeout=TIMEOUT)
            if r.ok:
                flash("success", f"Deleted {site}")
                st.rerun()
            else:
                st.error(f"Could not delete: {error_text(r)}")
        except requests.RequestException as e:
            st.error(f"API error: {e}")


# ---------------------------------------------------------------- navigation
PAGES = {
    "📊 Status checks": page_status_counts,
    "🖱️ Click count": page_click_count,
    "➕ Add website": page_add_website,
    "🗑️ Delete website": page_delete_website,
}

st.sidebar.title("💤 Keep-Alive")
choice = st.sidebar.radio("Page", list(PAGES), label_visibility="collapsed")
if st.sidebar.button("🔄 Refresh"):
    st.rerun()
st.sidebar.caption(f"API: {BASE_API}")

PAGES[choice]()

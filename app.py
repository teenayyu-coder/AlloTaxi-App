# app.py
import streamlit as st
import pandas as pd
import hashlib
import re
import json
import base64
from copy import deepcopy
import time
import requests
from streamlit_autorefresh import st_autorefresh

# =======================================================
#               CONFIGURATION ADMIN HARD-CODÉE
# =======================================================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = hashlib.sha256("adminpass".encode()).hexdigest()

# =======================================================
#               CONFIGURATION STREAMLIT
# =======================================================
st.set_page_config(
    page_title="AlloTaxitana",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =======================================================
#               CSS
# =======================================================
def load_css():
    try:
        with open('style.css', 'r') as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        fallback_css = """
        .trip-card {padding: 15px; border-radius: 12px; background: #f0f4f8; margin-bottom: 15px; border: 1px solid #dcdfe4;}
        .status-available {color: #28a745; font-weight: bold;}
        .status-accepted {color: #ffc107; font-weight: bold;}
        .status-completed {color: #6c757d; font-weight: bold;}
        .status-cancelled {color: #dc3545; font-weight: bold;}
        """
        st.markdown(f"<style>{fallback_css}</style>", unsafe_allow_html=True)

load_css()

# =======================================================
#               SCHEMAS
# =======================================================
SHEET_SCHEMAS = {
    "Users": [
        "Category", "First Name", "Phone", "Password",
        "Vehicle Brand", "Vehicle Type", "Engine Displacement",
        "Is Online", "Login Time", "Delivery Start Time"
    ],
    "Trips": [
        "Client Name", "Client Phone", "Start Point",
        "End Point", "Budget", "Status", "Driver"
    ],
    "Notifications": ["Target", "Message", "TripIndex", "Read", "Timestamp"]
}

# =======================================================
#               DONNÉES INITIALES
# =======================================================
INITIAL_DATA = {
    "Users": [],
    "Trips": [],
    "Notifications": []
}

DEFAULT_REPO = "teenayyu-coder/AlloTaxi-App"
DEFAULT_FILE = "data.json"

def github_credentials_available():
    return all(k in st.secrets for k in ("GITHUB_TOKEN", "GITHUB_REPO", "GITHUB_FILE"))

def get_github_api_url():
    repo = st.secrets["GITHUB_REPO"] if github_credentials_available() else DEFAULT_REPO
    file = st.secrets["GITHUB_FILE"] if github_credentials_available() else DEFAULT_FILE
    return f"https://api.github.com/repos/{repo}/contents/{file}"

# =======================================================
#               LOAD / SAVE (CORRIGÉ)
# =======================================================
def load_data():
    if github_credentials_available():
        api_url = get_github_api_url()
        headers = {"Authorization": f"Bearer {st.secrets['GITHUB_TOKEN']}"}
        r = requests.get(api_url, headers=headers)
        if r.status_code == 200:
            content = r.json()
            file_content = base64.b64decode(content["content"]).decode("utf-8")
            return json.loads(file_content)
    return deepcopy(INITIAL_DATA)

def save_data(data, initial_create=False):
    if not github_credentials_available():
        return

    api_url = get_github_api_url()
    headers = {
        "Authorization": f"Bearer {st.secrets['GITHUB_TOKEN']}",
        "Content-Type": "application/json"
    }
    payload = {
        "message": "Update data.json from Streamlit",
        "content": base64.b64encode(json.dumps(data, indent=4).encode()).decode()
    }

    r = requests.put(api_url, headers=headers, data=json.dumps(payload))

# =======================================================
#               HELPERS DATA
# =======================================================
def fetch_data(sheet):
    data = load_data()
    df = pd.DataFrame(data.get(sheet, []))
    for col in SHEET_SCHEMAS.get(sheet, []):
        if col not in df.columns:
            df[col] = ""
    return df

def append_row(sheet, row):
    data = load_data()
    data.setdefault(sheet, []).append(row)
    save_data(data)

def update_row_field(sheet, idx, field, value):
    data = load_data()
    if sheet in data and 0 <= idx < len(data[sheet]):
        data[sheet][idx][field] = value
        save_data(data)

# =======================================================
#               NOTIFICATIONS
# =======================================================
def add_notification(target, message, trip_index):
    append_row("Notifications", {
        "Target": target,
        "Message": message,
        "TripIndex": trip_index,
        "Read": False,
        "Timestamp": time.time()
    })

def get_unread_notifications(target):
    df = fetch_data("Notifications")
    return df[(df["Target"] == target) & (df["Read"] == False)]

def mark_notification_read(idx):
    update_row_field("Notifications", idx, "Read", True)

# =======================================================
#               PAGES
# =======================================================
def show_admin_page():
    st_autorefresh(interval=3000, key="admin_refresh")

    st.title("Admin")
    notifs = get_unread_notifications("Admin")
    for idx, n in notifs.iterrows():
        st.warning(n["Message"])
        if st.button("Lu", key=f"a{idx}"):
            mark_notification_read(idx)
            st.rerun()

def show_client_page():
    st_autorefresh(interval=3000, key="client_refresh")

    st.title("Client")

def show_driver_page():
    st_autorefresh(interval=3000, key="driver_refresh")

    st.title("Driver")

# =======================================================
#               ROUTING
# =======================================================
if "page" not in st.session_state:
    st.session_state.page = "login"

if st.session_state.page == "admin":
    show_admin_page()
elif st.session_state.page == "client":
    show_client_page()
elif st.session_state.page == "driver":
    show_driver_page()
else:
    st.title("Login")

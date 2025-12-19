# app.py
import streamlit as st
import pandas as pd
import hashlib
import re
import json
import base64
import time
import requests
from copy import deepcopy
from streamlit_autorefresh import st_autorefresh

# =======================================================
# CONFIG ADMIN
# =======================================================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = hashlib.sha256("adminpass".encode()).hexdigest()

# =======================================================
# CONFIG STREAMLIT
# =======================================================
st.set_page_config(page_title="AlloTaxitana", layout="wide")

# =======================================================
# CSS
# =======================================================
def load_css():
    css = """
    .trip-card {padding:15px;border-radius:12px;background:#f0f4f8;margin-bottom:15px;border:1px solid #dcdfe4;}
    .status-available {color:#28a745;font-weight:bold;}
    .status-accepted {color:#ffc107;font-weight:bold;}
    .status-completed {color:#6c757d;font-weight:bold;}
    .status-cancelled {color:#dc3545;font-weight:bold;}
    """
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

load_css()

# =======================================================
# SCHEMAS
# =======================================================
SHEET_SCHEMAS = {
    "Users": ["Category","First Name","Phone","Password","Vehicle Brand","Vehicle Type","Engine Displacement","Is Online","Login Time","Delivery Start Time"],
    "Trips": ["Client Name","Client Phone","Start Point","End Point","Budget","Status","Driver"],
    "Notifications": ["Target","Message","TripIndex","Read","Timestamp"]
}

INITIAL_DATA = {"Users": [], "Trips": [], "Notifications": []}

DEFAULT_REPO = "teenayyu-coder/AlloTaxi-App"
DEFAULT_FILE = "data.json"

# =======================================================
# GITHUB
# =======================================================
def github_available():
    return all(k in st.secrets for k in ("GITHUB_TOKEN","GITHUB_REPO","GITHUB_FILE"))

def github_url():
    repo = st.secrets["GITHUB_REPO"] if github_available() else DEFAULT_REPO
    file = st.secrets["GITHUB_FILE"] if github_available() else DEFAULT_FILE
    return f"https://api.github.com/repos/{repo}/contents/{file}"

def load_data():
    if github_available():
        r = requests.get(
            github_url(),
            headers={"Authorization": f"Bearer {st.secrets['GITHUB_TOKEN']}"}
        )
        if r.status_code == 200:
            return json.loads(base64.b64decode(r.json()["content"]).decode())
    return deepcopy(INITIAL_DATA)

def save_data(data):
    if not github_available():
        return
    payload = {
        "message": "Update data.json",
        "content": base64.b64encode(json.dumps(data, indent=2).encode()).decode()
    }
    requests.put(
        github_url(),
        headers={"Authorization": f"Bearer {st.secrets['GITHUB_TOKEN']}"},
        data=json.dumps(payload)
    )

# =======================================================
# HELPERS
# =======================================================
def fetch_data(sheet):
    df = pd.DataFrame(load_data().get(sheet, []))
    for c in SHEET_SCHEMAS[sheet]:
        if c not in df:
            df[c] = ""
    return df

def update_row(sheet, idx, field, value):
    data = load_data()
    data[sheet][idx][field] = value
    save_data(data)

def add_notification(target, msg, idx):
    data = load_data()
    data["Notifications"].append({
        "Target": target,
        "Message": msg,
        "TripIndex": idx,
        "Read": False,
        "Timestamp": time.time()
    })
    save_data(data)

def unread_notifications(target):
    df = fetch_data("Notifications")
    return df[(df["Target"] == target) & (df["Read"] == False)]

# =======================================================
# LOGIN
# =======================================================
def show_login():
    st.title("Connexion")
    name = st.text_input("Prénom")
    pwd = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter"):
        if name == ADMIN_USERNAME and hashlib.sha256(pwd.encode()).hexdigest() == ADMIN_PASSWORD_HASH:
            st.session_state.update({"logged":True,"role":"Admin","name":name})
            st.rerun()

        df = fetch_data("Users")
        row = df[df["First Name"] == name]
        if row.empty:
            st.error("Utilisateur introuvable")
            return
        if hashlib.sha256(pwd.encode()).hexdigest() != row["Password"].iloc[0]:
            st.error("Mot de passe incorrect")
            return

        st.session_state.update({
            "logged":True,
            "role":row["Category"].iloc[0],
            "name":name,
            "phone":row["Phone"].iloc[0]
        })
        st.rerun()

# =======================================================
# ADMIN
# =======================================================
def show_admin():
    st_autorefresh(3000,"admin")
    st.title("Admin")

    for i,n in unread_notifications("Admin").iterrows():
        if st.button(n["Message"], key=f"a{i}"):
            update_row("Notifications", i, "Read", True)
            st.rerun()

    st.dataframe(fetch_data("Users"), use_container_width=True)
    st.dataframe(fetch_data("Trips"), use_container_width=True)

# =======================================================
# CLIENT
# =======================================================
def show_client():
    st_autorefresh(3000,"client")
    st.title("Client")

    with st.form("new"):
        s = st.text_input("Départ")
        e = st.text_input("Arrivée")
        b = st.number_input("Budget",1000)
        if st.form_submit_button("Publier"):
            data = load_data()
            data["Trips"].append({
                "Client Name":st.session_state.name,
                "Client Phone":st.session_state.phone,
                "Start Point":s,
                "End Point":e,
                "Budget":str(int(b)),
                "Status":"Available",
                "Driver":""
            })
            save_data(data)
            st.rerun()

    df = fetch_data("Trips")
    for i,r in df[df["Client Phone"]==st.session_state.phone].iterrows():
        st.markdown(f"<div class='trip-card'>{r['Start Point']} → {r['End Point']} ({r['Status']})</div>", unsafe_allow_html=True)
        if r["Status"] in ["Available","Accepted"]:
            if st.button("Annuler", key=f"c{i}"):
                update_row("Trips", i, "Status", "Cancelled")
                update_row("Trips", i, "Driver", "")
                add_notification("Admin","Course annulée",i)
                st.rerun()

# =======================================================
# DRIVER
# =======================================================
def show_driver():
    st_autorefresh(3000,"driver")
    st.title("Driver")

    for i,n in unread_notifications(st.session_state.name).iterrows():
        if st.button(n["Message"], key=f"d{i}"):
            update_row("Notifications", i, "Read", True)
            st.rerun()

    df = fetch_data("Trips")
    mine = df[(df["Status"]=="Accepted") & (df["Driver"]==st.session_state.name)]
    if not mine.empty:
        idx = mine.index[0]
        if st.button("Terminer"):
            update_row("Trips", idx, "Status", "Completed")
            st.rerun()
        if st.button("Annuler"):
            update_row("Trips", idx, "Status", "Available")
            update_row("Trips", idx, "Driver", "")
            add_notification("Admin","Driver a annulé",idx)
            st.rerun()
        return

    for i,r in df[df["Status"]=="Available"].iterrows():
        st.markdown(f"<div class='trip-card'>{r['Start Point']} → {r['End Point']}</div>", unsafe_allow_html=True)
        if st.button("Accepter", key=f"a{i}"):
            update_row("Trips", i, "Status", "Accepted")
            update_row("Trips", i, "Driver", st.session_state.name)
            st.rerun()

# =======================================================
# ROUTING
# =======================================================
if "logged" not in st.session_state:
    st.session_state.logged = False

if not st.session_state.logged:
    show_login()
elif st.session_state.role == "Admin":
    show_admin()
elif st.session_state.role == "Client":
    show_client()
else:
    show_driver()

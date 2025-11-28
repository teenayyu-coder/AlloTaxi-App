# app.py
import streamlit as st
import pandas as pd
import hashlib
import re
import json
import base64
from copy import deepcopy
import time  # Pour la gestion du statut en ligne simple
import requests

# =======================================================
#               CONFIGURATION STREAMLIT & STYLE
# =======================================================
st.set_page_config(
    page_title="AlloTaxi",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------------
#   🔵 FONCTION POUR CHARGER LE LOGO (BASE64)
# -------------------------------------------------------
def load_logo_base64():
    try:
        with open("allotaxi.ico", "rb") as file:
            data = file.read()
            return base64.b64encode(data).decode()
    except:
        return None

LOGO_BASE64 = load_logo_base64()


def load_css():
    """Charge le style CSS de base directement via markdown."""
    css = """
    body {
        font-family: 'Inter', sans-serif;
    }
    .main-header {
        color: #FF4B4B;
        text-align: center;
        margin-bottom: 20px;
    }
    .trip-card {
        padding: 15px;
        border-radius: 12px;
        background: #f0f4f8;
        margin-bottom: 15px;
        border: 1px solid #dcdfe4;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .trip-card h3 {
        color: #333;
        border-bottom: 2px solid #ddd;
        padding-bottom: 5px;
        margin-top: 0;
    }
    .status-available { color: #28a745; font-weight: bold; }
    .status-accepted { color: #ffc107; font-weight: bold; }
    .status-completed { color: #6c757d; font-weight: bold; }
    .status-cancelled { color: #dc3545; font-weight: bold; }
    """
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


load_css()

# =======================================================
#               SCHEMAS DES DONNÉES
# =======================================================
SHEET_SCHEMAS = {
    "Users": [
        "Category", "First Name", "Phone", "Password",
        "Vehicle Brand", "Vehicle Type", "Engine Displacement", "Is Online"
    ],
    "Trips": [
        "Client Name", "Client Phone", "Start Point",
        "End Point", "Budget", "Status", "Driver"
    ]
}

# =======================================================
#               GESTION JSON
# =======================================================

INITIAL_DATA = {
    "Users": [
        {
            "Category": "Admin",
            "First Name": "admin",
            "Phone": "000000000",
            "Password": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",
            "Vehicle Brand": "",
            "Vehicle Type": "",
            "Engine Displacement": "",
            "Is Online": False
        },
        {
            "Category": "Client",
            "First Name": "testclient",
            "Phone": "032111111",
            "Password": "5e884898da28047151d0e56f8dc6292773603d0d6aabf35d2153c3e017d23d8c",
            "Vehicle Brand": "",
            "Vehicle Type": "",
            "Engine Displacement": "",
            "Is Online": False
        },
        {
            "Category": "Driver",
            "First Name": "testdriver",
            "Phone": "034222222",
            "Password": "5e884898da28047151d0e56f8dc6292773603d0d6aabf35d2153c3e017d23d8c",
            "Vehicle Brand": "Peugeot",
            "Vehicle Type": "Voiture",
            "Engine Displacement": "1.0L",
            "Is Online": False
        }
    ],
    "Trips": [
        {
            "Client Name": "Admin",
            "Client Phone": "000000000",
            "Start Point": "Place de l'Indépendance",
            "End Point": "Analakely",
            "Budget": "5000",
            "Status": "Available",
            "Driver": ""
        },
        {
            "Client Name": "testclient",
            "Client Phone": "032111111",
            "Start Point": "Antananarivo",
            "End Point": "Imerina",
            "Budget": "15000",
            "Status": "Accepted",
            "Driver": "testdriver"
        }
    ]
}

DEFAULT_REPO = "teenayyu-coder/AlloTaxi-App"
DEFAULT_FILE = "data.json"


def github_credentials_available():
    return all(k in st.secrets for k in ("GITHUB_TOKEN", "GITHUB_REPO", "GITHUB_FILE"))


def get_github_api_url():
    if github_credentials_available():
        repo = st.secrets["GITHUB_REPO"]
        filename = st.secrets["GITHUB_FILE"]
    else:
        repo = DEFAULT_REPO
        filename = DEFAULT_FILE
    return f"https://api.github.com/repos/{repo}/contents/{filename}"


def load_data():
    if "data_store" in st.session_state:
        return st.session_state.data_store

    if github_credentials_available():
        api_url = get_github_api_url()
        headers = {"Authorization": f"Bearer {st.secrets['GITHUB_TOKEN']}"}
        try:
            r = requests.get(api_url, headers=headers)
            if r.status_code == 200:
                content = r.json()
                file_content = base64.b64decode(content["content"]).decode("utf-8")
                st.session_state.data_store = json.loads(file_content)
                st.session_state.file_sha = content.get("sha")
                st.info("Merci de vous connecter.")
                return st.session_state.data_store
            elif r.status_code == 404:
                st.warning("data.json introuvable. Création...")
                st.session_state.data_store = deepcopy(INITIAL_DATA)
                save_data(st.session_state.data_store, initial_create=True)
                return st.session_state.data_store
            else:
                st.error(f"Erreur GitHub {r.status_code}, utilisation locale.")
        except Exception as e:
            st.error(f"Erreur GitHub : {e}")

    st.session_state.data_store = deepcopy(INITIAL_DATA)
    st.info("Données locales initialisées.")
    return st.session_state.data_store


def save_data(data, initial_create=False):
    st.session_state.data_store = data

    if not github_credentials_available():
        st.info("Secrets GitHub absents : sauvegarde locale.")
        return

    api_url = get_github_api_url()
    headers = {
        "Authorization": f"Bearer {st.secrets['GITHUB_TOKEN']}",
        "Content-Type": "application/json"
    }

    payload = {
        "message": "Update data.json",
        "content": base64.b64encode(json.dumps(data, indent=4).encode()).decode()
    }

    if not initial_create and st.session_state.get("file_sha"):
        payload["sha"] = st.session_state.file_sha

    try:
        r = requests.put(api_url, headers=headers, data=json.dumps(payload))
        resp = r.json()
        new_sha = resp.get("content", {}).get("sha")
        if new_sha:
            st.session_state.file_sha = new_sha
        st.success("Données sauvegardées ✔️")
    except Exception as e:
        st.error(f"Erreur sauvegarde GitHub : {e}")


def fetch_data(sheet_name):
    data = load_data()
    df = pd.DataFrame(data.get(sheet_name, []))
    for col in SHEET_SCHEMAS.get(sheet_name, []):
        if col not in df.columns:
            df[col] = ''
    return df


def append_row(sheet_name, new_row_dict):
    data = load_data()
    if sheet_name not in data:
        data[sheet_name] = []
    data[sheet_name].append(new_row_dict)
    save_data(data)


def update_row_field(sheet_name, index_to_update, field, new_value):
    data = load_data()
    if sheet_name in data and 0 <= index_to_update < len(data[sheet_name]):
        data[sheet_name][index_to_update][field] = new_value
        save_data(data)
        return True
    return False


def update_user_online_status(user_name, is_online):
    df_users = fetch_data("Users")
    user_row = df_users[df_users["First Name"] == user_name]
    if not user_row.empty:
        df_index = user_row.index[0]
        update_row_field("Users", df_index, "Is Online", is_online)


# =======================================================
#               SÉCURITÉ
# =======================================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def check_password_strength(password):
    if len(password) < 6:
        return False, "Mot de passe trop court."
    if not re.search(r"[A-Z]", password):
        return False, "Doit contenir une majuscule."
    return True, ""


# =======================================================
#           BOUTON LOGOUT
# =======================================================
def logout_button():
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🚪 Déconnexion"):
            if st.session_state.user_category in ["Driver", "Admin"]:
                update_user_online_status(st.session_state.user_name, False)

            st.session_state.logged_in = False
            st.session_state.page = "login"
            st.session_state.user_name = None
            st.session_state.user_category = None
            st.session_state.user_phone = None
            st.session_state.driver_accepted_trip = None
            st.success("Déconnecté ✔️")
            st.rerun()


# =======================================================
#               PAGE LOGIN
# =======================================================
def show_login_page():
    """Affiche la page de connexion."""

    # ---------------------------------------------------
    #   🔵 TITRE AVEC LOGO COLLÉ : [LOGO]lloTaxi
    # ---------------------------------------------------
    if LOGO_BASE64:
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; justify-content:center; margin-bottom:25px;">
                <img src="data:image/x-icon;base64,{LOGO_BASE64}"
                     style="width:55px; height:55px; margin-right:6px;"/>
                <h1 style="margin:0; padding:0; font-size:48px; font-weight:700;">
                    lloTaxi
                </h1>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.title("AlloTaxi")

    st.header("Connexion")

    with st.form("login_form"):
        login_name = st.text_input("Prénom")
        login_pass = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")

    if submitted:
        df = fetch_data("Users")

        row = df[df["First Name"] == login_name]

        if row.empty:
            st.error("Prénom introuvable.")
            return

        if hash_password(login_pass) != row["Password"].iloc[0]:
            st.error("Mot de passe incorrect.")
            return

        st.session_state.logged_in = True
        st.session_state.user_name = row["First Name"].iloc[0]
        st.session_state.user_category = row["Category"].iloc[0]
        st.session_state.user_phone = row["Phone"].iloc[0]

        if st.session_state.user_category in ["Driver", "Admin"]:
            update_user_online_status(st.session_state.user_name, True)

        st.success(f"Bienvenue {st.session_state.user_name} 👋")
        st.rerun()

    if st.button("Créer un compte"):
        st.session_state.page = "register"


# =======================================================
#   LES AUTRES PAGES (IDENTIQUES À TON CODE INITIAL)
# =======================================================

def show_register_page():
    ...


def show_admin_page():
    ...


def show_client_page():
    ...


def show_driver_page():
    ...


# =======================================================
#               ROUTING PRINCIPAL
# =======================================================
load_data()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page" not in st.session_state:
    st.session_state.page = "login"

if st.session_state.page == "register":
    show_register_page()
elif st.session_state.logged_in:
    if st.session_state.user_category == "Admin":
        show_admin_page()
    elif st.session_state.user_category == "Client":
        show_client_page()
    elif st.session_state.user_category == "Driver":
        show_driver_page()
else:
    show_login_page()

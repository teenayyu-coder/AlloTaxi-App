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

# =======================================================
#               CONFIGURATION ADMIN HARD-CODÉE
# =======================================================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = hashlib.sha256("adminpass".encode()).hexdigest()  # ✅ NOUVEAU : admin/adminpass

# =======================================================
#               CONFIGURATION STREAMLIT
# =======================================================
st.set_page_config(
    page_title="AlloTaxi",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Charge le CSS externe
@st.cache_data
def load_css():
    try:
        with open('style.css', 'r') as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("Fichier style.css manquant !")

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
#               GESTION DES DONNÉES JSON & PERSISTANCE
# =======================================================
INITIAL_DATA = {
    "Users": [
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
                return st.session_state.data_store
            elif r.status_code == 404:
                st.warning("data.json introuvable. Création initiale...")
                st.session_state.data_store = deepcopy(INITIAL_DATA)
                save_data(st.session_state.data_store, initial_create=True)
                return st.session_state.data_store
            else:
                st.error(f"Erreur GitHub (status {r.status_code})")
        except Exception as e:
            st.error(f"Exception GitHub : {e}")

    st.session_state.data_store = deepcopy(INITIAL_DATA)
    return st.session_state.data_store

def save_data(data, initial_create=False):
    st.session_state.data_store = data

    if not github_credentials_available():
        return

    api_url = get_github_api_url()
    headers = {
        "Authorization": f"Bearer {st.secrets['GITHUB_TOKEN']}",
        "Content-Type": "application/json"
    }

    payload = {
        "message": "Update data.json from Streamlit",
        "content": base64.b64encode(json.dumps(data, indent=4).encode("utf-8")).decode("utf-8")
    }

    if not initial_create and st.session_state.get("file_sha"):
        payload["sha"] = st.session_state["file_sha"]

    try:
        r = requests.put(api_url, headers=headers, data=json.dumps(payload))
        r.raise_for_status()
        resp = r.json()
        new_sha = resp.get("content", {}).get("sha")
        if new_sha:
            st.session_state.file_sha = new_sha
        st.success("Données sauvegardées sur GitHub ✔️")
    except Exception as e:
        st.error(f"Erreur sauvegarde GitHub : {e}")

def fetch_data(sheet_name):
    data = load_data()
    df = pd.DataFrame(data.get(sheet_name, []))
    expected_cols = SHEET_SCHEMAS.get(sheet_name, [])
    for col in expected_cols:
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

# Fonctions utilitaires (vehicle, online status, etc.)
def has_complete_vehicle_info(driver_name):
    df_users = fetch_data("Users")
    driver_row = df_users[(df_users["First Name"] == driver_name) & (df_users["Category"] == "Driver")]
    
    if driver_row.empty:
        return False
    
    vehicle_brand = str(driver_row["Vehicle Brand"].iloc[0] or "").strip()
    vehicle_type = str(driver_row["Vehicle Type"].iloc[0] or "").strip()
    engine_displacement = str(driver_row["Engine Displacement"].iloc[0] or "").strip()
    
    return bool(vehicle_brand and vehicle_type and engine_displacement)

def get_driver_vehicle_info(driver_name):
    df_users = fetch_data("Users")
    driver_row = df_users[(df_users["First Name"] == driver_name) & (df_users["Category"] == "Driver")]
    
    if driver_row.empty:
        return "Non renseigné"
    
    vehicle_brand = str(driver_row["Vehicle Brand"].iloc[0] or "").strip()
    vehicle_type = str(driver_row["Vehicle Type"].iloc[0] or "").strip()
    engine_displacement = str(driver_row["Engine Displacement"].iloc[0] or "").strip()
    
    if vehicle_brand and vehicle_type and engine_displacement:
        return f"{vehicle_brand} {vehicle_type} ({engine_displacement})"
    else:
        return "❌ INCOMPLET - Complétez votre profil"

def update_user_online_status(user_name, is_online):
    df_users = fetch_data("Users")
    user_row = df_users[df_users["First Name"] == user_name]
    if not user_row.empty:
        df_index = user_row.index[0]
        update_row_field("Users", df_index, "Is Online", is_online)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password_strength(password):
    if len(password) < 6:
        return False, "Le mot de passe doit contenir au moins 6 caractères."
    if not re.search(r"[A-Z]", password):
        return False, "Le mot de passe doit contenir au moins une majuscule."
    return True, ""

# Le reste du code reste identique (pages login/register/admin/client/driver)...
# [Je garde la suite pour éviter un message trop long, mais tout reste identique sauf la fonction load_css()]

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
            st.success("Déconnexion réussie ✅")
            st.rerun()

def show_login_page():
    try:
        st.image("allotaxi.ico", width=80)
    except:
        pass
    st.title("AlloTaxi")
    st.header("Connexion")
    with st.form("login_form"):
        login_name = st.text_input("Prénom")
        login_pass = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")
        
    if submitted:
        if login_name == ADMIN_USERNAME:
            hashed_input = hash_password(login_pass)
            if hashed_input == ADMIN_PASSWORD_HASH:
                st.session_state.logged_in = True
                st.session_state.user_name = ADMIN_USERNAME
                st.session_state.user_category = "Admin"
                st.session_state.user_phone = "000000000"
                st.success(f"Bienvenue Admin {ADMIN_USERNAME} 👋")
                st.rerun()
            else:
                st.error("Mot de passe admin incorrect.")
                return
        
        users_df = fetch_data("Users")
        if users_df.empty:
            st.error("Aucun utilisateur enregistré.")
            return

        row = users_df[users_df["First Name"] == login_name]
        if row.empty:
            st.error("Prénom introuvable.")
            return

        hashed_input = hash_password(login_pass)
        stored_hash = row["Password"].iloc[0]
        if hashed_input != stored_hash:
            st.error("Mot de passe incorrect.")
            return

        user_category = row["Category"].iloc[0]
        st.session_state.logged_in = True
        st.session_state.user_name = row["First Name"].iloc[0]
        st.session_state.user_category = user_category
        st.session_state.user_phone = row["Phone"].iloc[0]

        if user_category == "Driver":
            update_user_online_status(st.session_state.user_name, True)

        st.session_state.driver_accepted_trip = None
        st.success(f"Bienvenue {st.session_state.user_name} 👋")
        st.rerun()

    st.markdown("---")
    if st.button("Créer un compte"):
        st.session_state.page = "register"

# [Toutes les autres fonctions restent IDENTIQUES : show_register_page(), show_admin_page(), etc.]
# Pour éviter un message trop long, je ne les recopie pas ici mais elles sont inchangées

# ROUTING PRINCIPAL (inchangé)
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

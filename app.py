import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import hashlib
import re

# --- CONFIGURATION STREAMLIT & CSS ---
st.set_page_config(
    page_title="AlloTaxi",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def load_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Le fichier CSS '{file_name}' est introuvable. Style par défaut utilisé.")

load_css("style.css")

# --- GOOGLE SHEETS ---
GOOGLE_SHEET_ID = "1JUG3IuVPrIDkDqLxaRwfZh1ArWYarrS4pQIOSqDE1WY"

@st.cache_resource
def get_google_sheet_client():
    try:
        creds_json = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Erreur Google Sheets : {e}")
        return None

client = get_google_sheet_client()

# --- SCHEMA DES FEUILLES ---
USERS_COLUMNS = [
    "Category", "First Name", "Phone", "Password",
    "Vehicle Brand", "Vehicle Type", "Engine Displacement"
]

TRIPS_COLUMNS = [
    "Client Name", "Client Phone", "Start Point", "End Point",
    "Budget", "Status", "Driver"
]

# --- CREATION AUTOMATIQUE DES FEUILLES (OPTION A) ---
def ensure_sheet(sheet_name, required_columns):
    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        try:
            ws = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=len(required_columns))
            ws.append_row(required_columns)
            return ws

        # Vérifier et ajouter colonnes manquantes
        existing_cols = ws.row_values(1)
        missing_cols = [c for c in required_columns if c not in existing_cols]

        if missing_cols:
            new_header = existing_cols + missing_cols
            ws.delete_row(1)
            ws.insert_row(new_header, 1)
        return ws
    except Exception as e:
        st.error(f"Erreur lors de la vérification de la feuille {sheet_name} : {e}")
        return None

# S'assurer que les feuilles existent
if client:
    ensure_sheet("Users", USERS_COLUMNS)
    ensure_sheet("Trips", TRIPS_COLUMNS)

# --- DATA UTILS ---
def get_worksheet(sheet_name):
    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        return spreadsheet.worksheet(sheet_name)
    except:
        return None

def fetch_data(sheet_name):
    ws = get_worksheet(sheet_name)
    if not ws:
        return pd.DataFrame(columns=USERS_COLUMNS if sheet_name == "Users" else TRIPS_COLUMNS)

    data = ws.get_all_records()
    if not data:
        return pd.DataFrame(columns=USERS_COLUMNS if sheet_name == "Users" else TRIPS_COLUMNS)

    df = pd.DataFrame(data)
    df.columns = df.columns.map(lambda x: str(x).strip())
    return df

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password_strength(password):
    if len(password) < 6:
        return False, "Le mot de passe doit contenir au moins 6 caractères."
    if not re.search(r"[A-Z]", password):
        return False, "Une majuscule est requise."
    return True, ""

# --- UI ---
def show_login_page():
    st.title("🚖 AlloTaxi")
    st.header("Connexion")

    with st.form("login_form"):
        name = st.text_input("Prénom")
        pwd = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")

        if submitted:
            users_df = fetch_data('Users')
            user = users_df[users_df['First Name'] == name]

            if user.empty:
                st.error("Utilisateur introuvable.")
                return

            if hash_password(pwd) != user.iloc[0]['Password']:
                st.error("Mot de passe incorrect.")
                return

            st.session_state.logged_in = True
            st.session_state.user_name = name
            st.session_state.user_category = user.iloc[0]['Category']
            st.session_state.user_phone = user.iloc[0]['Phone']
            st.success("Connexion réussie !")
            st.rerun()

    if st.button("Créer un compte"):
        st.session_state.page = "register"


def show_register_page():
    st.title("✍️ Créer un Compte AlloTaxi")

    with st.form("register_form"):
        category = st.selectbox("Catégorie", ["Client", "Driver"])
        first_name = st.text_input("Prénom")
        phone = st.text_input("Téléphone")
        password = st.text_input("Mot de passe", type="password")

        details = {}
        if category == "Driver":
            details['Vehicle Brand'] = st.text_input("Marque du véhicule")
            details['Vehicle Type'] = st.selectbox("Type", ["Voiture", "Moto"])
            details['Engine Displacement'] = st.text_input("Cylindrée")

        submitted = st.form_submit_button("S'inscrire")

        if submitted:
            valid, msg = check_password_strength(password)
            if not valid:
                st.error(msg)
                return

            users_df = fetch_data("Users")
            if first_name in users_df['First Name'].values:
                st.error("Ce prénom existe déjà.")
                return

            row = [
                category, first_name, phone, hash_password(password),
                details.get('Vehicle Brand', ''), details.get('Vehicle Type', ''), details.get('Engine Displacement', '')
            ]

            ws = get_worksheet("Users")
            ws.append_row(row)
            st.success("Compte créé !")
            st.session_state.page = "login"
            st.rerun()

    if st.button("Retour"):
        st.session_state.page = "login"


def show_client_page():
    st.title(f"👋 Client : Bonjour {st.session_state.user_name}")

    with st.form("trip_form"):
        start = st.text_input("Départ")
        end = st.text_input("Arrivée")
        budget = st.number_input("Budget", min_value=1000)

        submitted = st.form_submit_button("Publier la course")

        if submitted:
            row = [
                st.session_state.user_name,
                st.session_state.user_phone,
                start, end, budget,
                "Available", ""
            ]
            ws = get_worksheet("Trips")
            ws.append_row(row)
            st.success("Course publiée !")


def show_driver_page():
    st.title(f"🏍️ Driver : Bonjour {st.session_state.user_name}")

    trips = fetch_data("Trips")

    # Vérifier si ce driver a déjà une course acceptée
    active = trips[(trips["Status"] == "Accepted") & (trips["Driver"] == st.session_state.user_name)]

    if not active.empty:
        row = active.iloc[0]
        st.warning(f"Course en cours : {row['Start Point']} → {row['End Point']}")

        if st.button("Terminer la course"):
            idx = active.index[0] + 2
            ws = get_worksheet("Trips")
            ws.update_cell(idx, TRIPS_COLUMNS.index("Status") + 1, "Completed")
            st.success("Course terminée !")
            st.rerun()
        return

    available = trips[trips["Status"] == "Available"]

    if available.empty:
        st.info("Aucune course disponible.")
        return

    for index, row in available.iterrows():
        gs_row = index + 2

        st.subheader(f"Course {index+1}")
        st.write(f"Départ : {row['Start Point']}")
        st.write(f"Arrivée : {row['End Point']}")
        st.write(f"Budget : {row['Budget']} Ar")

        if st.button(f"Accepter cette course", key=f"accept_{index}"):
            ws = get_worksheet("Trips")
            ws.update_cell(gs_row, TRIPS_COLUMNS.index("Status") + 1, "Accepted")
            ws.update_cell(gs_row, TRIPS_COLUMNS.index("Driver") + 1, st.session

# app.py
import streamlit as st
import pandas as pd
import hashlib
import re
import json
from copy import deepcopy
import time  # Pour la gestion du statut en ligne simple
import requests
import base64

# -------------------------------------------------------
#               CONFIGURATION STREAMLIT & STYLE
# -------------------------------------------------------
st.set_page_config(
    page_title="AlloTaxi",
    layout="wide",
    initial_sidebar_state="collapsed"
)


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

# -------------------------------------------------------
#               SCHEMAS DES DONNÉES
# -------------------------------------------------------
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

# -------------------------------------------------------
#               GESTION DES DONNÉES JSON & PERSISTANCE
# -------------------------------------------------------

# Structure initiale
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

        except Exception:
            st.error("Erreur GitHub. Données locales utilisées.")

    st.session_state.data_store = deepcopy(INITIAL_DATA)
    st.info("Données initialisées localement.")
    return st.session_state.data_store


def save_data(data, initial_create=False):
    st.session_state.data_store = data

    if not github_credentials_available():
        st.info("Pas de secrets GitHub : sauvegarde locale uniquement.")
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

        st.success("Données sauvegardées ✔️")
    except Exception as e:
        st.error(f"Erreur GitHub : {e}")


def fetch_data(sheet):
    data = load_data()
    df = pd.DataFrame(data.get(sheet, []))
    for col in SHEET_SCHEMAS[sheet]:
        if col not in df.columns:
            df[col] = ""
    return df


def append_row(sheet, row):
    data = load_data()
    data[sheet].append(row)
    save_data(data)


def update_row_field(sheet, index, field, value):
    data = load_data()
    if sheet in data and 0 <= index < len(data[sheet]):
        data[sheet][index][field] = value
        save_data(data)
        return True
    return False


def update_user_online_status(name, state):
    df = fetch_data("Users")
    row = df[df["First Name"] == name]
    if not row.empty:
        idx = row.index[0]
        update_row_field("Users", idx, "Is Online", state)


# -------------------------------------------------------
#               SÉCURITÉ MOT DE PASSE
# -------------------------------------------------------
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def check_password_strength(password):
    if len(password) < 6:
        return False, "Minimum 6 caractères."
    if not re.search(r"[A-Z]", password):
        return False, "Il faut une majuscule."
    return True, ""


# -------------------------------------------------------
#                       LOGOUT
# -------------------------------------------------------
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
            st.success("Déconnexion réussie ✔️")
            st.rerun()


# -------------------------------------------------------
#                       PAGE LOGIN
# -------------------------------------------------------
def show_login_page():

    # 🔥🔥🔥 MODIFICATION DEMANDÉE 🔥🔥🔥
    st.markdown("""
    <div style='display:flex; align-items:center; justify-content:center; margin-bottom:20px;'>
        <img src='allotaxi.ico' style='width:40px; height:40px; margin-right:4px; margin-top:-4px;'/>
        <h1 style='margin:0; padding:0; font-size:42px;'>lloTaxi</h1>
    </div>
    """, unsafe_allow_html=True)

    st.header("Connexion")
    with st.form("login_form"):
        login_name = st.text_input("Prénom")
        login_pass = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")

    if submitted:
        users = fetch_data("Users")

        row = users[users["First Name"] == login_name]
        if row.empty:
            st.error("Prénom introuvable.")
            return

        hashed_input = hash_password(login_pass)
        if hashed_input != row["Password"].iloc[0]:
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

    st.markdown("---")
    if st.button("Créer un compte"):
        st.session_state.page = "register"


# -------------------------------------------------------
#                       PAGE REGISTER
# -------------------------------------------------------
def show_register_page():
    st.title("✍️ Créer un Compte AlloTaxi")
    with st.form("register_form"):
        category = st.selectbox("Catégorie", ["Client", "Driver"])
        first_name = st.text_input("Prénom")
        phone = st.text_input("Téléphone")
        password = st.text_input("Mot de passe", type="password")

        driver_data = {}
        if category == "Driver":
            st.subheader("Informations Véhicule")
            driver_data["Vehicle Brand"] = st.text_input("Marque du véhicule")
            driver_data["Vehicle Type"] = st.selectbox("Type", ["Voiture", "Moto"])
            driver_data["Engine Displacement"] = st.text_input("Cylindrée")

        submitted = st.form_submit_button("Créer le compte")

    if submitted:

        if first_name.lower() == "admin":
            st.error("Ce prénom est réservé.")
            return

        ok, msg = check_password_strength(password)
        if not ok:
            st.error(msg)
            return

        df = fetch_data("Users")
        if first_name in df["First Name"].values:
            st.error("Ce prénom existe déjà.")
            return

        new_user = {
            "Category": category,
            "First Name": first_name,
            "Phone": phone,
            "Password": hash_password(password),
            "Vehicle Brand": driver_data.get("Vehicle Brand", ""),
            "Vehicle Type": driver_data.get("Vehicle Type", ""),
            "Engine Displacement": driver_data.get("Engine Displacement", ""),
            "Is Online": False
        }

        append_row("Users", new_user)
        st.success("Compte créé ✔️")
        st.session_state.page = "login"
        st.rerun()

    if st.button("Retour"):
        st.session_state.page = "login"


# -------------------------------------------------------
#                       PAGE ADMIN
# -------------------------------------------------------
def show_admin_page():
    st.title(f"👑 Admin : Gestion des Drivers")
    logout_button()
    st.markdown("---")

    df_users = fetch_data("Users")
    df_trips = fetch_data("Trips")

    drivers = df_users[df_users["Category"] == "Driver"]

    if drivers.empty:
        st.info("Aucun driver enregistré.")
        return

    accepted = df_trips[df_trips["Status"] == "Accepted"]

    lst = []
    for _, d in drivers.iterrows():
        name = d["First Name"]
        in_progress = accepted[accepted["Driver"] == name]

        online = "🟢 En Ligne" if d["Is Online"] else "🔴 Hors Ligne"

        if not in_progress.empty:
            info = (
                f"En Course: {in_progress.iloc[0]['Start Point']} → "
                f"{in_progress.iloc[0]['End Point']} (Client: {in_progress.iloc[0]['Client Name']})"
            )
            race = "🟡 EN COURSE"
        else:
            info = "En attente"
            race = "✅ Disponible"

        lst.append({
            "Driver": name,
            "Statut Connexion": online,
            "Statut Course": race,
            "Course en Cours": info
        })

    st.dataframe(pd.DataFrame(lst), use_container_width=True)


# -------------------------------------------------------
#                       PAGE CLIENT
# -------------------------------------------------------
def show_client_page():
    st.title(f"👋 Client : Bonjour {st.session_state.user_name}")
    logout_button()
    st.markdown("---")

    st.header("Créer une nouvelle course")
    with st.form("new_trip_form"):
        start = st.text_input("Départ")
        end = st.text_input("Arrivée")
        budget = st.number_input("Budget (Ariary)", min_value=1000)
        submitted = st.form_submit_button("Créer la course")

    if submitted:
        if not start or not end:
            st.error("Champs manquants.")
            return

        new_trip = {
            "Client Name": st.session_state.user_name,
            "Client Phone": st.session_state.user_phone,
            "Start Point": start,
            "End Point": end,
            "Budget": str(int(budget)),
            "Status": "Available",
            "Driver": ""
        }

        append_row("Trips", new_trip)
        st.success("Course créée ✔️")

    st.markdown("---")
    st.header("Historique")

    df = fetch_data("Trips")
    client_trips = df[df["Client Phone"] == st.session_state.user_phone]

    if client_trips.empty:
        st.info("Aucune course pour le moment.")
        return

    for _, row in client_trips.iterrows():

        color = {
            "Available": "status-available",
            "Accepted": "status-accepted",
            "Completed": "status-completed",
            "Cancelled": "status-cancelled",
        }.get(row["Status"], "status-completed")

        st.markdown(f"""
        <div class="trip-card">
            <h4>{row['Start Point']} → {row['End Point']}</h4>
            <p>💰 Budget : <b>{row['Budget']} Ar</b></p>
            <p>🏁 Statut : <span class="{color}">{row['Status']}</span></p>
            <p>🚕 Driver : <b>{row['Driver'] if row['Driver'] else "En attente"}</b></p>
        </div>
        """, unsafe_allow_html=True)


# -------------------------------------------------------
#                       PAGE DRIVER
# -------------------------------------------------------
def show_driver_page():
    st.title(f"🏍️ Driver : Bonjour {st.session_state.user_name}")
    logout_button()

    df = fetch_data("Trips")

    # Course en cours ?
    accepted = df[(df["Status"] == "Accepted") & (df["Driver"] == st.session_state.user_name)]

    if not accepted.empty:
        row = accepted.iloc[0]
        idx = accepted.index[0]

        st.warning(f"🚨 Course : {row['Start Point']} → {row['End Point']} (Client: {row['Client Name']})")

        col_end, col_cancel, _ = st.columns([1.5, 1.5, 3])

        with col_end:
            if st.button("🏁 Terminer"):
                update_row_field("Trips", idx, "Status", "Completed")
                st.success("Course terminée ✔️")
                st.rerun()

        with col_cancel:
            if st.button("❌ Annuler"):
                update_row_field("Trips", idx, "Status", "Available")
                update_row_field("Trips", idx, "Driver", "")
                st.warning("Course annulée.")
                st.rerun()

        return

    # Courses disponibles
    avail = df[df["Status"] == "Available"]
    st.header(f"Courses disponibles ({len(avail)})")
    st.markdown("---")

    if avail.empty:
        st.info("Aucune course disponible.")
        return

    for idx, row in avail.iterrows():
        st.markdown(f"""
            <div class="trip-card">
                <h3>🚗 Course #{idx + 1}</h3>
                <p>📍 Départ : <b>{row['Start Point']}</b></p>
                <p>🏁 Arrivée : <b>{row['End Point']}</b></p>
                <p>💰 Budget : <b>{row['Budget']} Ar</b></p>
                <p style='font-size: small; color: #888;'>(Client: {row['Client Name']} / Tél: {row['Client Phone']})</p>
            </div>
        """, unsafe_allow_html=True)

        if st.button("✅ Accepter", key=f"acc_{idx}"):
            update_row_field("Trips", idx, "Status", "Accepted")
            update_row_field("Trips", idx, "Driver", st.session_state.user_name)
            st.success("Course acceptée ✔️")
            st.rerun()

        st.markdown("---")


# -------------------------------------------------------
#               ROUTAGE PRINCIPAL
# -------------------------------------------------------

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

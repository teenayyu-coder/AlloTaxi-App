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
#               CONFIGURATION STREAMLIT & STYLE
# =======================================================
st.set_page_config(
    page_title="AlloTaxi",
    layout="wide",
    initial_sidebar_state="collapsed"
)


def load_css():
    css = """
    body { font-family: 'Inter', sans-serif; }
    .main-header { color: #FF4B4B; text-align: center; margin-bottom: 20px; }
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
#        DONNÉES JSON PAR DÉFAUT (SI PAS DE GITHUB)
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

# =======================================================
#               GESTION GITHUB
# =======================================================
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
                st.warning("data.json introuvable dans GitHub. Création…")
                st.session_state.data_store = deepcopy(INITIAL_DATA)
                save_data(st.session_state.data_store, initial_create=True)
                return st.session_state.data_store
        except Exception:
            pass

    st.session_state.data_store = deepcopy(INITIAL_DATA)
    st.info("Données initialisées localement.")
    return st.session_state.data_store


def save_data(data, initial_create=False):
    st.session_state.data_store = data

    if not github_credentials_available():
        return

    api_url = get_github_api_url()
    headers = {"Authorization": f"Bearer {st.secrets['GITHUB_TOKEN']}"}

    payload = {
        "message": "Update data.json",
        "content": base64.b64encode(json.dumps(data, indent=4).encode("utf-8")).decode()
    }

    if not initial_create and st.session_state.get("file_sha"):
        payload["sha"] = st.session_state.file_sha

    r = requests.put(api_url, headers=headers, json=payload)
    if r.status_code in (200, 201):
        st.session_state.file_sha = r.json()["content"]["sha"]


def fetch_data(sheet):
    data = load_data()
    df = pd.DataFrame(data.get(sheet, []))
    for c in SHEET_SCHEMAS[sheet]:
        if c not in df.columns:
            df[c] = ""
    return df


def append_row(sheet, row):
    data = load_data()
    data[sheet].append(row)
    save_data(data)


def update_row_field(sheet, idx, field, value):
    data = load_data()
    if sheet in data and 0 <= idx < len(data[sheet]):
        data[sheet][idx][field] = value
        save_data(data)
        return True
    return False


def update_user_online_status(user, online):
    df = fetch_data("Users")
    row = df[df["First Name"] == user]
    if not row.empty:
        idx = row.index[0]
        update_row_field("Users", idx, "Is Online", online)

# =======================================================
#                     SÉCURITÉ
# =======================================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def check_password_strength(password):
    if len(password) < 6:
        return False, "Minimum 6 caractères."
    if not re.search(r"[A-Z]", password):
        return False, "Une majuscule requise."
    return True, ""


# =======================================================
#                     LOGOUT
# =======================================================
def logout_button():
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🚪 Déconnexion"):
            if st.session_state.user_category in ["Driver", "Admin"]:
                update_user_online_status(st.session_state.user_name, False)
            st.session_state.logged_in = False
            st.session_state.page = "login"
            st.rerun()

# =======================================================
#                     PAGES
# =======================================================

# ---------------- LOGIN PAGE ----------------
def show_login_page():
    st.title("AlloTaxi — Connexion")

    with st.form("login_form"):
        login_name = st.text_input("Prénom")
        login_pass = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")

    if submitted:
        df = fetch_data("Users")
        row = df[df["First Name"] == login_name]

        if row.empty:
            st.error("Utilisateur introuvable.")
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

        st.success("Connexion réussie")
        st.rerun()

    if st.button("Créer un compte"):
        st.session_state.page = "register"


# ---------------- REGISTER PAGE ----------------
def show_register_page():
    st.title("✍️ Créer un Compte")

    with st.form("register_form"):

        # ✔ Catégorie par défaut = "Client"
        category = st.selectbox("Catégorie", ["Client", "Driver"], index=0)

        first_name = st.text_input("Prénom")
        phone = st.text_input("Téléphone")
        password = st.text_input("Mot de passe", type="password")

        driver_data = {}

        # ✔ Affichage conditionnel : seulement si Driver
        if category == "Driver":
            st.subheader("Informations Véhicule")
            driver_data["Vehicle Brand"] = st.text_input("Marque")
            driver_data["Vehicle Type"] = st.selectbox("Type", ["Voiture", "Moto"])
            driver_data["Engine Displacement"] = st.text_input("Cylindrée")

        submitted = st.form_submit_button("Créer le compte")

    if submitted:
        if first_name.lower() == "admin":
            st.error("Le prénom 'admin' est réservé.")
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
        st.success("Compte créé !")

        st.session_state.page = "login"
        st.rerun()

    if st.button("Retour"):
        st.session_state.page = "login"


# ---------------- ADMIN PAGE ----------------
def show_admin_page():
    st.title(f"👑 Admin : Gestion Drivers")
    logout_button()

    df_users = fetch_data("Users")
    df_trips = fetch_data("Trips")

    drivers = df_users[df_users["Category"] == "Driver"]

    if drivers.empty:
        st.info("Aucun driver.")
        return

    accepted = df_trips[df_trips["Status"] == "Accepted"]

    rows = []
    for _, d in drivers.iterrows():
        driver_name = d["First Name"]
        trip = accepted[accepted["Driver"] == driver_name]

        rows.append({
            "Driver": driver_name,
            "Statut Connexion": "🟢 En Ligne" if d["Is Online"] else "🔴 Hors Ligne",
            "Statut Course": "🟡 En course" if not trip.empty else "✅ Disponible",
            "Course": f"{trip.iloc[0]['Start Point']} → {trip.iloc[0]['End Point']}" if not trip.empty else "-"
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True)


# ---------------- CLIENT PAGE ----------------
def show_client_page():
    st.title(f"👋 Client : Bonjour {st.session_state.user_name}")
    logout_button()

    st.header("Créer une course")
    with st.form("new_trip"):
        start = st.text_input("Départ")
        end = st.text_input("Arrivée")
        budget = st.number_input("Budget", min_value=1000)
        submitted = st.form_submit_button("Créer")

    if submitted:
        append_row("Trips", {
            "Client Name": st.session_state.user_name,
            "Client Phone": st.session_state.user_phone,
            "Start Point": start,
            "End Point": end,
            "Budget": str(int(budget)),
            "Status": "Available",
            "Driver": ""
        })
        st.success("Course ajoutée !")

    df = fetch_data("Trips")
    my_trips = df[df["Client Phone"] == st.session_state.user_phone]

    st.header("Historique")
    for _, row in my_trips.sort_index(ascending=False).iterrows():
        st.markdown(f"""
        <div class="trip-card">
            <h4>{row['Start Point']} → {row['End Point']}</h4>
            <p>💰 {row['Budget']} Ar</p>
            <p>Statut : {row['Status']}</p>
        </div>
        """, unsafe_allow_html=True)


# ---------------- DRIVER PAGE ----------------
def show_driver_page():
    st.title(f"🏍️ Driver : Bonjour {st.session_state.user_name}")
    logout_button()

    df = fetch_data("Trips")

    accepted = df[(df["Status"] == "Accepted") &
                  (df["Driver"] == st.session_state.user_name)]

    if not accepted.empty:
        row = accepted.iloc[0]
        idx = accepted.index[0]
        st.warning(f"🚨 En course : {row['Start Point']} → {row['End Point']}")

        col1, col2 = st.columns(2)

        if col1.button("🏁 Terminer"):
            update_row_field("Trips", idx, "Status", "Completed")
            st.rerun()

        if col2.button("❌ Annuler"):
            update_row_field("Trips", idx, "Status", "Available")
            update_row_field("Trips", idx, "Driver", "")
            st.rerun()

        return

    available = df[df["Status"] == "Available"]
    st.header(f"Courses disponibles : {len(available)}")

    for idx, row in available.iterrows():
        st.markdown(f"""
        <div class="trip-card">
            <h3>Course #{idx}</h3>
            <p>📍 {row['Start Point']} → {row['End Point']}</p>
            <p>💰 {row['Budget']} Ar</p>
        </div>""", unsafe_allow_html=True)

        if st.button("Accepter", key=f"acc_{idx}"):
            update_row_field("Trips", idx, "Status", "Accepted")
            update_row_field("Trips", idx, "Driver", st.session_state.user_name)
            st.rerun()

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

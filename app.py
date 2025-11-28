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
#               GESTION DES DONNÉES JSON & PERSISTANCE
# =======================================================

# Structure initiale des données
INITIAL_DATA = {
    "Users": [
        {
            "Category": "Admin",
            "First Name": "admin",
            "Phone": "000000000",
            "Password": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",  # 'adminpass' hashé
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

# Valeurs par défaut du repo/fichier (si vous n'utilisez pas st.secrets)
DEFAULT_REPO = "teenayyu-coder/AlloTaxi-App"
DEFAULT_FILE = "data.json"

def github_credentials_available():
    """Retourne True si les secrets GitHub sont configurés."""
    return all(k in st.secrets for k in ("GITHUB_TOKEN", "GITHUB_REPO", "GITHUB_FILE"))

def get_github_api_url():
    """Construit l'URL API pour le fichier data.json sur le repo."""
    if github_credentials_available():
        repo = st.secrets["GITHUB_REPO"]
        filename = st.secrets["GITHUB_FILE"]
    else:
        repo = DEFAULT_REPO
        filename = DEFAULT_FILE
    return f"https://api.github.com/repos/{repo}/contents/{filename}"

def load_data():
    """
    Charge data.json depuis GitHub (via API) si les secrets sont présents,
    sinon utilise st.session_state en mémoire.
    """
    # Si déjà chargé en session -> renvoyer
    if "data_store" in st.session_state:
        return st.session_state.data_store

    # Si secrets disponibles -> tenter de charger depuis GitHub
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
                # Fichier absent -> créer avec INITIAL_DATA
                st.warning("data.json introuvable dans le repo. Création d'un fichier initial sur GitHub...")
                st.session_state.data_store = deepcopy(INITIAL_DATA)
                # On crée le fichier (PUT sans sha)
                save_data(st.session_state.data_store, initial_create=True)
                return st.session_state.data_store
            else:
                st.error(f"Erreur chargement GitHub (status {r.status_code}). Utilisation des données locales.")
        except Exception as e:
            st.error(f"Exception lors du chargement GitHub : {e}. Utilisation des données locales.")

    # Fallback : initialiser en mémoire
    st.session_state.data_store = deepcopy(INITIAL_DATA)
    st.info("Données initialisées en mémoire (fallback).")
    return st.session_state.data_store

def save_data(data, initial_create=False):
    """
    Sauvegarde data sur GitHub si les secrets sont configurés.
    - si initial_create=True, la requête fera un PUT sans sha (création).
    - sinon inclut le sha si disponible pour mise à jour.
    Sinon sauvegarde seulement en mémoire (st.session_state).
    """
    # Toujours mettre à jour la session mémoire
    st.session_state.data_store = data

    if not github_credentials_available():
        st.info("Secrets GitHub non configurés : sauvegarde uniquement en mémoire.")
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

    # Si on a déjà récupéré un sha, l'envoyer (pour la mise à jour)
    if not initial_create and st.session_state.get("file_sha"):
        payload["sha"] = st.session_state["file_sha"]

    try:
        r = requests.put(api_url, headers=headers, data=json.dumps(payload))
        r.raise_for_status()
        resp = r.json()
        # Mettre à jour le sha pour les prochaines modifications
        new_sha = resp.get("content", {}).get("sha")
        if new_sha:
            st.session_state.file_sha = new_sha
        st.success("Données sauvegardées sur GitHub ✔️")
    except requests.HTTPError as he:
        st.error(f"Erreur HTTP lors de la sauvegarde GitHub : {he} (status {getattr(he.response, 'status_code', 'N/A')}).")
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde GitHub : {e}")

def fetch_data(sheet_name):
    """Récupère les données d'une 'feuille' et les renvoie sous forme de DataFrame."""
    data = load_data()
    df = pd.DataFrame(data.get(sheet_name, []))
    expected_cols = SHEET_SCHEMAS.get(sheet_name, [])
    # Assurer que les colonnes attendues existent pour éviter les erreurs
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ''
    return df

def append_row(sheet_name, new_row_dict):
    """Ajoute une nouvelle ligne (dictionnaire) à une 'feuille' de données."""
    data = load_data()
    if sheet_name not in data:
        data[sheet_name] = []
    data[sheet_name].append(new_row_dict)
    save_data(data)

def update_row_field(sheet_name, index_to_update, field, new_value):
    """Met à jour un champ spécifique dans une ligne par son index pandas."""
    data = load_data()
    # L'index pandas correspond à l'index dans la liste Python
    if sheet_name in data and 0 <= index_to_update < len(data[sheet_name]):
        data[sheet_name][index_to_update][field] = new_value
        save_data(data)
        return True
    return False

# Fonction pour mettre à jour le statut en ligne d'un utilisateur
def update_user_online_status(user_name, is_online):
    df_users = fetch_data("Users")
    user_row = df_users[df_users["First Name"] == user_name]
    if not user_row.empty:
        # L'index du DataFrame est l'index dans la liste Python
        df_index = user_row.index[0]
        update_row_field("Users", df_index, "Is Online", is_online)

# =======================================================
#               SÉCURITÉ MOT DE PASSE
# =======================================================
def hash_password(password):
    """Hashe le mot de passe en utilisant SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password_strength(password):
    """Vérifie la robustesse minimale du mot de passe."""
    if len(password) < 6:
        return False, "Le mot de passe doit contenir au moins 6 caractères."
    if not re.search(r"[A-Z]", password):
        return False, "Le mot de passe doit contenir au moins une majuscule."
    return True, ""

# =======================================================
#               BOUTON DE DÉCONNEXION
# =======================================================
def logout_button():
    """Affiche un bouton de déconnexion et gère le statut en ligne."""
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🚪 Déconnexion"):
            # Mettre à jour le statut "Hors Ligne" pour les Drivers/Admins
            if st.session_state.user_category in ["Driver", "Admin"]:
                update_user_online_status(st.session_state.user_name, False)

            # Réinitialisation de l'état de session
            st.session_state.logged_in = False
            st.session_state.page = "login"
            st.session_state.user_name = None
            st.session_state.user_category = None
            st.session_state.user_phone = None
            st.session_state.driver_accepted_trip = None
            st.success("Déconnexion réussie ✅")
            st.rerun()

# =======================================================
#                       PAGES DE L'APPLICATION
# =======================================================

# ----------------- PAGE LOGIN --------------------------
def show_login_page():
    """Affiche la page de connexion."""
    # Affichage du logo si disponible (base64 préféré)
    if LOGO_BASE64:
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; justify-content:center; margin-bottom:25px;">
                <img src="data:image/x-icon;base64,{LOGO_BASE64}"
                     style="width:60px; height:55px; margin-right:10px;"/>
                <h1 style="margin:0; padding:0; font-size:48px; font-weight:500;">
                    lloTaxi
                </h1>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        # Fallback vers st.image si fichier icône accessible, sinon titre simple
        try:
            st.image("allotaxi.ico", width=80)
        except Exception:
            st.title("AlloTaxi")

    st.header("Connexion")
    with st.form("login_form"):
        login_name = st.text_input("Prénom")
        login_pass = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")
        
    if submitted:
        users_df = fetch_data("Users")
        if users_df.empty:
            st.error("Aucun utilisateur enregistré.")
            return

        row = users_df[users_df["First Name"] == login_name]

        if row.empty:
            st.error("Prénom introuvable.")
            return

        # Vérification du mot de passe
        hashed_input = hash_password(login_pass)
        stored_hash = row["Password"].iloc[0]

        if hashed_input != stored_hash:
            st.error("Mot de passe incorrect.")
            return

        # Connexion réussie
        user_category = row["Category"].iloc[0]
        st.session_state.logged_in = True
        st.session_state.user_name = row["First Name"].iloc[0]
        st.session_state.user_category = user_category
        st.session_state.user_phone = row["Phone"].iloc[0]

        # Mettre à jour le statut "En Ligne" pour les Drivers/Admins
        if user_category in ["Driver", "Admin"]:
            update_user_online_status(st.session_state.user_name, True)

        st.session_state.driver_accepted_trip = None
        st.success(f"Bienvenue {st.session_state.user_name} 👋")
        st.rerun()

    st.markdown("---")

    # IMPORTANT: lorsque l'on clique sur "Créer un compte", on force la page register
    # et on mémorise qu'on vient de cliquer pour afficher "Driver" par défaut.
    if st.button("Créer un compte"):
        st.session_state.default_category_driver = True
        st.session_state.page = "register"

# ----------------- PAGE REGISTER --------------------------
def show_register_page():
    """Affiche la page d'inscription."""
    st.title("✍️ Créer un Compte AlloTaxi")

    # Formulaire d'inscription
    with st.form("register_form"):
        # Choix de la catégorie — si l'utilisateur vient du bouton "Créer un compte",
        # on force l'index sur "Driver" par défaut (index=1) pour afficher les champs véhicule.
        # st.session_state.default_category_driver est défini quand on clique sur "Créer un compte".
        category = st.selectbox(
            "Catégorie",
            ["Client", "Driver"],
            index=1 if st.session_state.get("default_category_driver", False) else 0
        )

        # Réinitialiser le flag pour ne pas forcer Driver à chaque ouverture ultérieure
        st.session_state.default_category_driver = False

        first_name = st.text_input("Prénom")
        phone = st.text_input("Téléphone")
        password = st.text_input("Mot de passe", type="password")

        driver_data = {}
        if category == "Driver":
            st.subheader("Informations Véhicule")
            driver_data["Vehicle Brand"] = st.text_input("Marque du véhicule")
            driver_data["Vehicle Type"] = st.selectbox("Type du véhicule", ["Voiture", "Moto"])
            driver_data["Engine Displacement"] = st.text_input("Cylindrée")

        submitted = st.form_submit_button("Créer le compte")

    if submitted:
        if first_name.lower() == 'admin':
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

        # Construction du dictionnaire de la nouvelle ligne
        new_user_dict = {
            "Category": category,
            "First Name": first_name,
            "Phone": phone,
            "Password": hash_password(password),
            "Vehicle Brand": driver_data.get("Vehicle Brand", ""),
            "Vehicle Type": driver_data.get("Vehicle Type", ""),
            "Engine Displacement": driver_data.get("Engine Displacement", ""),
            "Is Online": False  # Par défaut, déconnecté
        }

        append_row("Users", new_user_dict)
        st.success("Compte créé ! Vous pouvez vous connecter.")
        st.session_state.page = "login"
        st.rerun()

    if st.button("Retour"):
        st.session_state.page = "login"

# ----------------- PAGE ADMIN --------------------------
def show_admin_page():
    """Affiche le tableau de bord d'administration."""
    st.title(f"👑 Admin : Gestion des Drivers")
    logout_button()
    st.markdown("---")

    st.header("Statut des Drivers")

    df_users = fetch_data("Users")
    df_trips = fetch_data("Trips")

    driver_df = df_users[df_users["Category"] == "Driver"].copy()

    if driver_df.empty:
        st.info("Aucun driver enregistré.")
        return

    accepted_trips = df_trips[df_trips["Status"] == "Accepted"]

    driver_list = []
    for _, driver in driver_df.iterrows():
        driver_name = driver['First Name']

        trip_in_progress = accepted_trips[accepted_trips["Driver"] == driver_name]

        status_online = "🟢 En Ligne" if driver['Is Online'] else "🔴 Hors Ligne"

        if not trip_in_progress.empty:
            trip_info = f"En Course: {trip_in_progress.iloc[0]['Start Point']} → {trip_in_progress.iloc[0]['End Point']} (Client: {trip_in_progress.iloc[0]['Client Name']})"
            status_race = "🟡 EN COURSE"
        else:
            trip_info = "En attente de course"
            status_race = "✅ Disponible"

        driver_list.append({
            "Driver": driver_name,
            "Statut Connexion": status_online,
            "Statut Course": status_race,
            "Course en Cours": trip_info
        })

    st.dataframe(pd.DataFrame(driver_list), use_container_width=True)

# ----------------- PAGE CLIENT --------------------------
def show_client_page():
    """Affiche la page du client (création de course et historique)."""
    st.title(f"👋 Client : Bonjour {st.session_state.user_name}")
    logout_button()
    st.markdown("---")

    st.header("Créer une nouvelle course")
    with st.form("new_trip_form"):
        start_point = st.text_input("Départ")
        end_point = st.text_input("Arrivée")
        budget = st.number_input("Budget (Ariary)", min_value=1000)
        submitted = st.form_submit_button("Créer la course")

    if submitted:
        if not start_point or not end_point:
            st.error("Veuillez remplir tous les champs.")
            return

        try:
            new_trip = {
                "Client Name": str(st.session_state.user_name or ""),
                "Client Phone": str(st.session_state.user_phone or ""),
                "Start Point": str(start_point or ""),
                "End Point": str(end_point or ""),
                "Budget": str(int(budget)),  # Assurez-vous que c'est une chaîne pour JSON
                "Status": "Available",
                "Driver": ""
            }
            append_row("Trips", new_trip)
            st.success("✅ Course ajoutée avec succès ! (Actualisez pour voir le statut)")
            # st.rerun() # Optionnel: pour forcer l'actualisation
        except Exception as e:
            st.error(f"Erreur lors de l’ajout de la course : {e}")

    st.markdown("---")
    st.header("Historique de vos courses")

    df_trips = fetch_data("Trips")

    # Filtrer les courses créées par ce client (en utilisant le téléphone pour plus de fiabilité)
    client_trips = df_trips[df_trips["Client Phone"] == st.session_state.user_phone]

    if client_trips.empty:
        st.info("Vous n'avez créé aucune course pour l'instant.")
        return

    # Inverser l'ordre pour voir les plus récentes en premier
    for index, row in client_trips.sort_index(ascending=False).iterrows():
        status_color = {
            "Available": "status-available",
            "Accepted": "status-accepted",
            "Completed": "status-completed",
            "Cancelled": "status-cancelled",
        }.get(row['Status'], "status-completed")

        st.markdown(f"""
            <div class="trip-card">
                <h4>{row['Start Point']} → {row['End Point']}</h4>
                <p>💰 Budget : <b>{row['Budget']} Ar</b></p>
                <p>🏁 Statut : <span class="{status_color}">{row['Status']}</span></p>
                <p>🚕 Driver Assigné : <b>{row['Driver'] if row['Driver'] else 'En attente'}</b></p>
            </div>
        """, unsafe_allow_html=True)

# ----------------- PAGE DRIVER --------------------------
def show_driver_page():
    """Affiche la page du driver (gestion des courses acceptées et disponibles)."""
    st.title(f"🏍️ Driver : Bonjour {st.session_state.user_name}")
    logout_button()

    df = fetch_data("Trips")

    # 1. Vérification des courses acceptées par ce driver
    accepted = df[(df["Status"] == "Accepted") & (df["Driver"] == st.session_state.user_name)]

    if not accepted.empty:
        row = accepted.iloc[0]
        # On utilise l'index du DataFrame pour la mise à jour
        df_index = accepted.index[0]

        st.warning(f"🚨 Course en cours : {row['Start Point']} → {row['End Point']} (Client: {row['Client Name']})")

        col_finish, col_cancel, _ = st.columns([1.5, 1.5, 3])

        with col_finish:
            if st.button("🏁 Terminer la course", use_container_width=True):
                if update_row_field("Trips", df_index, "Status", "Completed"):
                    st.success("Course terminée ! Félicitations.")
                    st.rerun()
                else:
                    st.error("Erreur lors de la mise à jour de la course.")

        with col_cancel:
            if st.button("❌ Annuler la course", use_container_width=True):
                # Remettre le statut à "Available" et enlever l'assignation du Driver
                if update_row_field("Trips", df_index, "Status", "Available") and \
                            update_row_field("Trips", df_index, "Driver", ""):
                    st.warning("Course annulée et remise en attente d'acceptation.")
                    st.rerun()
                else:
                    st.error("Erreur lors de l'annulation de la course.")

        return

    # 2. Affichage des courses disponibles
    avail = df[df["Status"] == "Available"]
    st.header(f"Courses disponibles ({len(avail)})")
    st.markdown("---")

    if avail.empty:
        st.info("Aucune course disponible actuellement.")
        return

    for df_index, row in avail.iterrows():
        # Utiliser st.container pour regrouper la carte et le bouton d'acceptation
        with st.container():
            st.markdown(f"""
                <div class="trip-card">
                    <h3>🚗 Course #{df_index + 1}</h3>
                    <p>📍 Départ : <b>{row['Start Point']}</b></p>
                    <p>🏁 Arrivée : <b>{row['End Point']}</b></p>
                    <p>💰 Budget : <b>{row['Budget']} Ar</b></p>
                    <p style="font-size: small; color: #6c757d;">(Client: {row['Client Name']} / Tél: {row['Client Phone']})</p>
                </div>
            """, unsafe_allow_html=True)

            if st.button("✅ Accepter cette course", key=f"acc_{df_index}"):
                status_ok = update_row_field("Trips", df_index, "Status", "Accepted")
                driver_ok = update_row_field("Trips", df_index, "Driver", st.session_state.user_name)

                if status_ok and driver_ok:
                    st.success("Course acceptée ✅. Vous pouvez commencer la course.")
                    st.rerun()
                else:
                    st.error("Erreur lors de l'acceptation de la course.")

            st.markdown("---")

# =======================================================
#               ROUTING PRINCIPAL
# =======================================================

# Initialisation des données JSON en mémoire au démarrage
load_data()

# Initialisation de l'état de session si non existant
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page" not in st.session_state:
    st.session_state.page = "login"

# Initialisation du flag pour forcer la catégorie Driver sur la page register
if "default_category_driver" not in st.session_state:
    st.session_state.default_category_driver = False

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
        st.error("Catégorie inconnue ou page non trouvée.")
else:
    show_login_page()

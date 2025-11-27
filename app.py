import streamlit as st
import pandas as pd
import hashlib
import re
import json
from copy import deepcopy

# -------------------------------------------------------
#                CONFIGURATION STREAMLIT
# -------------------------------------------------------
st.set_page_config(
    page_title="AlloTaxi",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def load_css(file_name):
    """Charge le fichier CSS externe."""
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Le fichier CSS '{file_name}' est introuvable.")

load_css("style.css")

# -------------------------------------------------------
#                GESTION DES DONNÉES JSON (Simulées)
# -------------------------------------------------------

# Structure initiale des données (à remplacer par la lecture de 'data.json' si possible)
# Pour une utilisation Streamlit Cloud, les données seront stockées ici au démarrage.
INITIAL_DATA = {
    "Users": [
        # Exemple d'utilisateur/driver pré-enregistré pour les tests
        # Note: Les mots de passe sont hashés (ex: "password" -> hash)
        {
          "Category": "Client",
          "First Name": "testclient",
          "Phone": "032111111",
          "Password": "5e884898da28047151d0e56f8dc6292773603d0d6aabf35d2153c3e017d23d8c", # 'password' hashé
          "Vehicle Brand": "",
          "Vehicle Type": "",
          "Engine Displacement": ""
        },
        {
          "Category": "Driver",
          "First Name": "testdriver",
          "Phone": "034222222",
          "Password": "5e884898da28047151d0e56f8dc6292773603d0d6aabf35d2153c3e017d23d8c", # 'password' hashé
          "Vehicle Brand": "Peugeot",
          "Vehicle Type": "Voiture",
          "Engine Displacement": "1.0L"
        }
    ],
    "Trips": [
        # Exemple de course initiale
        {
          "Client Name": "Admin",
          "Client Phone": "000000000",
          "Start Point": "Place de l'Indépendance",
          "End Point": "Analakely",
          "Budget": "5000",
          "Status": "Available",
          "Driver": ""
        }
    ]
}

def load_data():
    """Charge les données JSON depuis l'état de session ou l'initialise."""
    if 'data_store' not in st.session_state:
        # Idéalement ici : Lire le fichier data.json
        # Mais dans Streamlit Cloud, on utilise une version en mémoire
        st.session_state.data_store = deepcopy(INITIAL_DATA)
        st.info("Données initialisées en mémoire.")
    return st.session_state.data_store

def save_data(data):
    """Simule la sauvegarde des données (mise à jour de l'état de session)."""
    # Ce point serait l'endroit où vous feriez la requête PUT/POST vers l'API GitHub
    st.session_state.data_store = data
    # st.success("Données mises à jour en mémoire (Simulée) !") # Optionnel

def fetch_data(sheet_name):
    """Récupère les données d'une 'feuille' et les renvoie sous forme de DataFrame."""
    data = load_data()
    df = pd.DataFrame(data.get(sheet_name, []))
    # Assurer que les colonnes attendues existent pour éviter les erreurs
    expected_cols = SHEET_SCHEMAS.get(sheet_name, [])
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ''
    return df

def append_row(sheet_name, new_row_dict):
    """Ajoute une nouvelle ligne (dictionnaire) à une 'feuille' de données."""
    data = load_data()
    data[sheet_name].append(new_row_dict)
    save_data(data)

def update_row_field(sheet_name, index_to_update, field, new_value):
    """Met à jour un champ spécifique dans une ligne par son index pandas."""
    data = load_data()
    # L'index pandas correspond à l'index dans la liste Python
    if 0 <= index_to_update < len(data[sheet_name]):
        data[sheet_name][index_to_update][field] = new_value
        save_data(data)
        return True
    return False

# -------------------------------------------------------
#                SCHEMAS DES DONNÉES
# -------------------------------------------------------
SHEET_SCHEMAS = {
    "Users": [
        "Category", "First Name", "Phone", "Password",
        "Vehicle Brand", "Vehicle Type", "Engine Displacement"
    ],
    "Trips": [
        "Client Name", "Client Phone", "Start Point",
        "End Point", "Budget", "Status", "Driver"
    ]
}

# -------------------------------------------------------
#                SÉCURITÉ MOT DE PASSE
# -------------------------------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password_strength(password):
    if len(password) < 6:
        return False, "Le mot de passe doit contenir au moins 6 caractères."
    if not re.search(r"[A-Z]", password):
        return False, "Le mot de passe doit contenir au moins une majuscule."
    return True, ""

# -------------------------------------------------------
#                BOUTON DE DÉCONNEXION
# -------------------------------------------------------
def logout_button():
    """Affiche un bouton de déconnexion en haut à droite."""
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🚪 Déconnexion"):
            st.session_state.logged_in = False
            st.session_state.page = "login"
            st.session_state.user_name = None
            st.session_state.user_category = None
            st.success("Déconnexion réussie ✅")
            st.rerun()

# -------------------------------------------------------
#                   PAGE LOGIN
# -------------------------------------------------------
def show_login_page():
    st.title("🚖 AlloTaxi")
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
            
        st.session_state.logged_in = True
        st.session_state.user_name = row["First Name"].iloc[0]
        st.session_state.user_category = row["Category"].iloc[0]
        st.session_state.user_phone = row["Phone"].iloc[0]
        st.session_state.driver_accepted_trip = None
        st.success(f"Bienvenue {st.session_state.user_name} 👋")
        st.rerun()
    st.markdown("---")
    if st.button("Créer un compte"):
        st.session_state.page = "register"

# -------------------------------------------------------
#                   PAGE REGISTER
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
            driver_data["Vehicle Brand"] = st.text_input("Marque du véhicule")
            driver_data["Vehicle Type"] = st.selectbox("Type du véhicule", ["Voiture", "Moto"])
            driver_data["Engine Displacement"] = st.text_input("Cylindrée")

        submitted = st.form_submit_button("Créer le compte")
    
    if submitted:
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
            "Engine Displacement": driver_data.get("Engine Displacement", "")
        }
        
        append_row("Users", new_user_dict)
        st.success("Compte créé ! Vous pouvez vous connecter.")
        st.session_state.page = "login"
        st.rerun()

    if st.button("Retour"):
        st.session_state.page = "login"

# -------------------------------------------------------
#                   PAGE CLIENT
# -------------------------------------------------------
def show_client_page():
    st.title(f"👋 Client : Bonjour {st.session_state.user_name}")
    logout_button()
    st.markdown("---")
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
                "Budget": str(int(budget)), # Assurez-vous que c'est une chaîne pour JSON
                "Status": "Available",
                "Driver": ""
            }
            append_row("Trips", new_trip)
            st.success("✅ Course ajoutée avec succès !")
        except Exception as e:
            st.error(f"Erreur lors de l’ajout de la course : {e}")

# -------------------------------------------------------
#                   PAGE DRIVER
# -------------------------------------------------------
def show_driver_page():
    st.title(f"🏍️ Driver : Bonjour {st.session_state.user_name}")
    logout_button()
    
    df = fetch_data("Trips")
    
    # 1. Vérification des courses acceptées par ce driver
    accepted = df[(df["Status"] == "Accepted") & (df["Driver"] == st.session_state.user_name)]
    
    if not accepted.empty:
        row = accepted.iloc[0]
        # On utilise l'index du DataFrame pour la mise à jour
        df_index = accepted.index[0] 

        st.warning(f"🚨 Course en cours : {row['Start Point']} → {row['End Point']}")
        
        if st.button("Terminer la course"):
            if update_row_field("Trips", df_index, "Status", "Completed"):
                st.session_state.driver_accepted_trip = None
                st.success("Course terminée !")
                st.rerun()
            else:
                st.error("Erreur lors de la mise à jour de la course.")
        return
    
    # 2. Affichage des courses disponibles
    avail = df[df["Status"] == "Available"]
    st.header(f"Courses disponibles ({len(avail)})")
    st.markdown("---")
    
    if avail.empty:
        st.info("Aucune course disponible.")
        return
    
    for df_index, row in avail.iterrows():
        st.markdown(f"""
            <div class="trip-card" style="padding:10px; border-radius:10px; background:#f8f9fa; margin-bottom:10px;">
                <h3>🚗 Course #{df_index + 1}</h3>
                <p>👤 Client : <b>{row['Client Name']}</b></p>
                <p>📞 Téléphone : <b>{row['Client Phone']}</b></p>
                <p>📍 Départ : <b>{row['Start Point']}</b></p>
                <p>🏁 Arrivée : <b>{row['End Point']}</b></p>
                <p>💰 Budget : <b>{row['Budget']} Ar</b></p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("✅ Accepter cette course", key=f"acc_{df_index}"):
            # Mise à jour des deux champs dans la ligne Trips correspondante
            status_ok = update_row_field("Trips", df_index, "Status", "Accepted")
            driver_ok = update_row_field("Trips", df_index, "Driver", st.session_state.user_name)
            
            if status_ok and driver_ok:
                st.session_state.driver_accepted_trip = f"{row['Start Point']} → {row['End Point']}"
                st.success("Course acceptée ✅")
                st.rerun()
            else:
                st.error("Erreur lors de l'acceptation de la course.")
                
        st.markdown("---")

# -------------------------------------------------------
#                ROUTING PRINCIPAL
# -------------------------------------------------------

# ⚠️ IMPORTANT : Initialisation des données JSON en mémoire au démarrage
# Ceci doit être fait avant le routing
load_data() 

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page" not in st.session_state:
    st.session_state.page = "login"

# Suppression de la vérification de la connexion Google Sheets
# puisque nous utilisons la méthode de simulation JSON en mémoire

if st.session_state.page == "register":
    show_register_page()
elif st.session_state.logged_in:
    if st.session_state.user_category == "Client":
        show_client_page()
    elif st.session_state.user_category == "Driver":
        show_driver_page()
    else:
        st.error("Catégorie inconnue.")
else:
    show_login_page()

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import hashlib
import re

# --- CONFIGURATION STREAMLIT & CSS ---
# Définit la mise en page
st.set_page_config(
    page_title="AlloTaxi",
    layout="wide", # Essentiel pour le responsive mobile (pas de colonnes latérales par défaut)
    initial_sidebar_state="collapsed"
)

# Fonction pour charger le CSS
def load_css(file_name):
    # En production (Streamlit Cloud), cette méthode lit le fichier local.
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        # En cas d'erreur de lecture sur certains environnements de déploiement,
        # on pourrait insérer le CSS directement ici si besoin.
        st.warning(f"Le fichier CSS '{file_name}' n'a pas été trouvé. L'application utilisera le style par défaut.")
        pass

# Charge le fichier CSS pour le design moderne et mobile
load_css("style.css")

# --- CONNEXION GOOGLE SHEETS SÉCURISÉE (VIA SECRETS) ---

# ID de votre document Google Sheet (récupéré de votre entrée)
GOOGLE_SHEET_ID = "1JUG3IuVPrIDkDqLxaRwfZh1ArWYarrS4pQIOSqDE1WY"

@st.cache_resource
def get_google_sheet_client():
    """Initialise et retourne le client gspread en utilisant les secrets Streamlit."""
    try:
        # Récupère les informations d'authentification depuis st.secrets
        # La clé 'gcp_service_account' correspond à la section [gcp_service_account] dans secrets.toml
        creds_json = st.secrets["gcp_service_account"]
        
        # Le scope est nécessaire pour indiquer les permissions demandées
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']
        
        # Crée les identifiants à partir du dictionnaire de secrets
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        
        client = gspread.authorize(creds)
        return client
    except KeyError:
        st.error("Erreur de configuration : Le secret 'gcp_service_account' n'est pas trouvé. Veuillez vérifier les paramètres 'Secrets' de votre application Streamlit.")
        return None
    except Exception as e:
        st.error(f"Erreur de connexion à Google Sheets. Détail: {e}")
        return None

client = get_google_sheet_client()

# --- FONCTIONS DE GESTION DES DONNÉES ---

def get_worksheet(sheet_name):
    """Récupère une feuille de calcul spécifique par son nom."""
    if client:
        try:
            spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
            worksheet = spreadsheet.worksheet(sheet_name)
            return worksheet
        except Exception as e:
            st.error(f"Erreur lors de la récupération de la feuille '{sheet_name}'. Détail: {e}")
            return None
    return None

def fetch_data(sheet_name):
    worksheet = get_worksheet(sheet_name)
    if not worksheet:
        return pd.DataFrame()

    data = worksheet.get_all_records()

    # Si la feuille est vide, créer DF avec colonnes attendues
    if not data:
        return pd.DataFrame(columns=[
            "Category",
            "First Name",
            "Phone",
            "Password",
            "Vehicle Brand",
            "Vehicle Type",
            "Engine Displacement"
        ])

    df = pd.DataFrame(data)
    df.columns = df.columns.map(lambda x: str(x).strip())
    return df
    
    return pd.DataFrame()

def hash_password(password):
    """Hache le mot de passe pour le stockage sécurisé."""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password_strength(password):
    """Vérifie que le mot de passe a 6+ caractères et au moins 1 majuscule."""
    if len(password) < 6:
        return False, "Le mot de passe doit contenir au moins 6 caractères."
    if not re.search(r'[A-Z]', password):
        return False, "Le mot de passe doit contenir au moins une majuscule."
    return True, ""

# --- FONCTIONS D'INTERFACE UTILISATEUR ---

def show_login_page():
    """Affiche la page de connexion/inscription."""
    st.title("🚖 AlloTaxi")
    st.header("Connexion")

    with st.form("login_form"):
        st.session_state.login_name = st.text_input("Prénom", key="login_name_input")
        st.session_state.login_pass = st.text_input("Mot de passe", type="password", key="login_pass_input")
        submitted = st.form_submit_button("Se connecter")

        if submitted:
            users_df = fetch_data('Users')
            if users_df.empty:
                st.error("Aucun utilisateur trouvé. Veuillez créer un compte.")
            else:
                user_record = users_df[(users_df['First Name'] == st.session_state.login_name)]

                if not user_record.empty:
                    # Vérification du mot de passe haché
                    hashed_pass = hash_password(st.session_state.login_pass)
                    stored_pass = user_record['Password'].iloc[0]

                    if hashed_pass == stored_pass:
                        st.session_state.logged_in = True
                        st.session_state.user_name = st.session_state.login_name
                        st.session_state.user_category = user_record['Category'].iloc[0]
                        st.session_state.user_phone = user_record['Phone'].iloc[0]
                        st.session_state.driver_accepted_trip = None # Initialise le statut de course du driver
                        st.success(f"Connexion réussie ! Bienvenue {st.session_state.user_name}.")
                        st.experimental_rerun() # Rafraîchit pour afficher la bonne page
                    else:
                        st.error("Mot de passe incorrect.")
                else:
                    st.error("Prénom non trouvé.")

    st.markdown("---")
    st.subheader("Nouveau compte ?")
    if st.button("Créer un compte"):
        st.session_state.page = "register"

def show_register_page():
    """Affiche la page d'inscription."""
    st.title("✍️ Créer un Compte AlloTaxi")

    with st.form("register_form"):
        category = st.selectbox("Catégorie", ["Client", "Driver"])
        first_name = st.text_input("Prénom")
        phone = st.text_input("Téléphone (pour vous contacter)")
        password = st.text_input("Mot de passe (Min. 6 caractères, 1 Maj.)", type="password")

        driver_details = {}
        if category == "Driver":
            driver_details['Vehicle Brand'] = st.text_input("Marque du véhicule (Ex: Toyota)")
            driver_details['Vehicle Type'] = st.selectbox("Type du véhicule", ["Voiture", "Moto"])
            driver_details['Engine Displacement'] = st.text_input("Cylindrée (Ex: 125cc ou 1.6L)")

        submitted = st.form_submit_button("S'inscrire")

        if submitted:
            is_valid, error_msg = check_password_strength(password)
            if not is_valid:
                st.error(error_msg)
            elif not first_name or not phone or not password:
                st.error("Veuillez remplir tous les champs obligatoires.")
            else:
                # Vérification de l'unicité du prénom
                users_df = fetch_data('Users')
                if "First Name" not in users_df.columns:
                    st.error(f"❌ La colonne 'First Name' est manquante. Colonnes trouvées : {users_df.columns.tolist()}")
                    return
                    
                if first_name in users_df['First Name'].values:
                    st.error("Ce Prénom est déjà utilisé. Veuillez en choisir un autre.")
                else:
                    # Préparation des données pour Google Sheet
                    new_user_data = [
                        category,
                        first_name,
                        phone,
                        hash_password(password), # Stockage du mot de passe haché
                        driver_details.get('Vehicle Brand', ''),
                        driver_details.get('Vehicle Type', ''),
                        driver_details.get('Engine Displacement', '')
                    ]

                    # Enregistrement dans Google Sheet
                    users_sheet = get_worksheet('Users')
                    if users_sheet:
                        users_sheet.append_row(new_user_data)
                        st.success("Compte créé avec succès ! Vous pouvez maintenant vous connecter.")
                        st.session_state.page = "login"
                        st.experimental_rerun()

    if st.button("Retour à la connexion"):
        st.session_state.page = "login"

# --- PAGES CLIENT/DRIVER ---

def show_client_page():
    """Page Client : Création de course."""
    st.title(f"👋 Client : Bonjour {st.session_state.user_name}")
    
    st.markdown("---")
    st.header("🚕 Réserver une Course")

    with st.form("new_trip_form"):
        start_point = st.text_input("Point de départ (Ex: Behoririka)")
        end_point = st.text_input("Point d'arrivée (Ex: Faravohitra)")
        budget = st.number_input("Votre budget pour la course (Ariary)", min_value=1000, step=500)
        
        # Le nom et téléphone du client sont pré-remplis
        st.caption(f"Vos coordonnées : **{st.session_state.user_name}** / **{st.session_state.user_phone}**")

        submitted = st.form_submit_button("Créer la course")

        if submitted:
            if not start_point or not end_point or budget < 1000:
                st.error("Veuillez renseigner tous les détails de la course.")
            else:
                # Préparation des données
                new_trip_data = [
                    st.session_state.user_name,
                    st.session_state.user_phone,
                    start_point,
                    end_point,
                    budget,
                    "Available", # Statut initial de la course
                    ""           # Nom du Driver
                ]

                # Enregistrement dans Google Sheet
                trips_sheet = get_worksheet('Trips')
                if trips_sheet:
                    trips_sheet.append_row(new_trip_data)
                    st.success("Votre course a été publiée ! Un driver va l'accepter bientôt.")

def show_driver_page():
    """Page Driver : Liste des courses disponibles."""
    st.title(f"🏍️ Driver : Bonjour {st.session_state.user_name}")

    trips_df = fetch_data('Trips')
    
    # Filtrer les courses disponibles
    available_trips = trips_df[trips_df['Status'] == 'Available'].copy()
    
    # Afficher la course acceptée par le driver actuel, si elle existe
    accepted_trip = trips_df[
        (trips_df['Status'] == 'Accepted') & 
        (trips_df['Driver'] == st.session_state.user_name)
    ]
    
    if not accepted_trip.empty:
        st.session_state.driver_accepted_trip = accepted_trip.iloc[0]['Start Point'] + " -> " + accepted_trip.iloc[0]['End Point']
        st.warning(f"🚨 Course en cours : {st.session_state.driver_accepted_trip}. Terminez-la avant d'en accepter une autre.")
        st.markdown(f"""
            <div class='trip-card' style='background-color: #330000; border-left: 5px solid red;'>
                <h3>Course Acceptée</h3>
                <p>Départ : <strong>{accepted_trip.iloc[0]['Start Point']}</strong></p>
                <p>Arrivée : <strong>{accepted_trip.iloc[0]['End Point']}</strong></p>
                <p>Budget Client : <strong>{accepted_trip.iloc[0]['Budget']} Ar</strong></p>
                <p>Client : <strong>{accepted_trip.iloc[0]['Client Name']} ({accepted_trip.iloc[0]['Client Phone']})</strong></p>
                <p>Statut : <strong>EN COURS</strong></p>
            </div>
        """, unsafe_allow_html=True)
        
        # Bouton pour terminer la course
        if st.button("Marquer comme Terminée"):
             complete_trip_index = accepted_trip.index[0] + 2 # +2 car le df est 0-indexé et GS est 1-indexé avec entêtes
             worksheet = get_worksheet('Trips')
             if worksheet:
                worksheet.update_cell(complete_trip_index, trips_df.columns.get_loc('Status') + 1, 'Completed')
                st.session_state.driver_accepted_trip = None
                st.success("Course marquée comme terminée ! Bien joué.")
                st.experimental_rerun()
                
        # Le driver ne peut pas voir/accepter d'autres courses tant qu'il en a une
        return 

    st.markdown("---")
    st.header(f"Liste des courses disponibles ({len(available_trips)})")
    
    if available_trips.empty:
        st.info("Aucune course disponible pour le moment. Revenez plus tard.")
        return

    # Affichage et gestion des courses
    for index, row in available_trips.iterrows():
        # L'index + 2 donne la ligne réelle dans Google Sheet (0-index + entêtes)
        gs_row_index = index + 2 
        
        # Utiliser un conteneur HTML pour le style
        st.markdown(f"""
            <div class='trip-card'>
                <h3>Course N°{index + 1}</h3>
                <p>📍 Départ : <strong>{row['Start Point']}</strong></p>
                <p>🏁 Arrivée : <strong>{row['End Point']}</strong></p>
                <p>💰 Budget Client : <strong>{row['Budget']} Ar</strong></p>
            </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        
        # Bouton Accepter (avec une clé unique basée sur l'index de la ligne)
        with col1:
            if st.button("Accepter la course", key=f"accept_{index}"):
                worksheet = get_worksheet('Trips')
                if worksheet:
                    # Mettre à jour le statut et le driver dans la ligne GS correspondante
                    worksheet.update_cell(gs_row_index, trips_df.columns.get_loc('Status') + 1, 'Accepted')
                    worksheet.update_cell(gs_row_index, trips_df.columns.get_loc('Driver') + 1, st.session_state.user_name)
                    st.success(f"Course acceptée : {row['Start Point']} -> {row['End Point']}")
                    st.session_state.driver_accepted_trip = row['Start Point'] + " -> " + row['End Point']
                    st.experimental_rerun()

        # Le bouton Rejeter est conditionnel (Règle : on rejette si on a déjà accepté une course)
        with col2:
            # Règle : Le driver peut cliquer sur "Rejeter" uniquement s’il a déjà accepté une course.
            # J'ai interprété cela comme : il ne peut pas rejeter une course non acceptée par lui. 
            # Si vous vouliez qu'il puisse rejeter une course AVANT de l'accepter, il faudrait changer la logique.
            # Dans le contexte d'une liste de courses disponibles, le bouton Rejeter est désactivé ici.
            if st.button("Rejeter la course", key=f"reject_{index}", disabled=True):
                 st.info("Pour le moment, vous ne pouvez rejeter que si vous avez déjà accepté une course (cette fonctionnalité n'est pas encore implémentée pour les courses non acceptées).")
                 pass

# --- GESTION DE LA NAVIGATION PRINCIPALE ---

# Initialisation des états de session (comme un cookie de navigation)
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'page' not in st.session_state:
    st.session_state.page = "login"

# Affiche le bouton de déconnexion si l'utilisateur est connecté
if st.session_state.logged_in:
    if st.sidebar.button("Déconnexion"):
        st.session_state.logged_in = False
        st.session_state.page = "login"
        st.experimental_rerun()
        
    st.markdown("---") # Séparation visuelle

# Logique de routage/affichage
if not client:
    st.error("L'application ne peut pas se connecter à Google Sheets. Veuillez vérifier votre configuration dans les secrets Streamlit.")
elif st.session_state.page == "register":
    show_register_page()
elif st.session_state.logged_in:
    # Si connecté, affiche la page spécifique Client ou Driver
    if st.session_state.user_category == "Client":
        show_client_page()
    elif st.session_state.user_category == "Driver":
        show_driver_page()
    else:
        # Cas improbable
        st.error("Catégorie d'utilisateur inconnue.")
else:
    # Par défaut (non connecté)
    show_login_page()







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
#                CONFIGURATION ADMIN HARD-CODÉE
# =======================================================
ADMIN_USERNAME = "admin"
# Ligne 16: Caractères invisibles nettoyés
ADMIN_PASSWORD_HASH = hashlib.sha256("adminpass".encode()).hexdigest() # ✅ admin/adminpass

# =======================================================
#                CONFIGURATION STREAMLIT
# =======================================================
st.set_page_config(
    page_title="AlloTaxi", # Ligne 22: Indentation nettoyée
    layout="wide",        # Ligne 23: Indentation nettoyée
    initial_sidebar_state="collapsed"
)

# Charge le CSS externe
def load_css():
    try:
        with open('style.css', 'r') as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        # CSS de fallback si style.css manquant
        fallback_css = """
        .trip-card {padding: 15px; border-radius: 12px; background: #f0f4f8; margin-bottom: 15px; border: 1px solid #dcdfe4;}
        .status-available {color: #28a745; font-weight: bold;}
        .status-accepted {color: #ffc107; font-weight: bold;}
        .status-completed {color: #6c757d; font-weight: bold;}
        .status-cancelled {color: #dc3545; font-weight: bold;}
        .vehicle-warning {background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; margin: 20px 0;}
        .chrono {font-weight: bold; color: #007bff;}
        """
        st.markdown(f"<style>{fallback_css}</style>", unsafe_allow_html=True)

load_css()

# =======================================================
#                SCHEMAS DES DONNÉES
# =======================================================
SHEET_SCHEMAS = {
    "Users": [
        "Category", "First Name", "Phone", "Password",
        "Vehicle Brand", "Vehicle Type", "Engine Displacement", "Is Online",
        "Login Time", "Delivery Start Time", "Profile Photo"
    ],
    "Trips": [
        "Client Name", "Client Phone", "Start Point",
        "End Point", "Budget", "Status", "Driver"
    ]
}

# =======================================================
#                GESTION DES DONNÉES JSON & PERSISTANCE
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
            "Is Online": False,
            "Login Time": 0,
            "Delivery Start Time": 0,
            "Profile Photo": ""
        },
        {
            "Category": "Driver",
            "First Name": "testdriver",
            "Phone": "034222222",
            "Password": "5e884898da28047151d0e56f8dc6292773603d0d6aabf35d2153c3e017d23d8c",
            "Vehicle Brand": "Peugeot",
            "Vehicle Type": "Voiture",
            "Engine Displacement": "1.0L",
            "Is Online": False,
            "Login Time": 0,
            "Delivery Start Time": 0
        }
    ],
    "Trips": []
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
        except:
            pass

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
        if resp.get("content", {}).get("sha"):
            st.session_state.file_sha = resp["content"]["sha"]
    except:
        pass

def fetch_data(sheet_name):
    data = load_data()
    df = pd.DataFrame(data.get(sheet_name, []))
    expected_cols = SHEET_SCHEMAS.get(sheet_name, [])
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ''
    # Convertir les timestamps en float pour éviter les erreurs
    if "Login Time" in df.columns:
        df["Login Time"] = pd.to_numeric(df["Login Time"], errors='coerce').fillna(0)
    if "Delivery Start Time" in df.columns:
        df["Delivery Start Time"] = pd.to_numeric(df["Delivery Start Time"], errors='coerce').fillna(0)
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

def delete_row(sheet_name, index_to_delete):
    data = load_data()
    if sheet_name in data and 0 <= index_to_delete < len(data[sheet_name]):
        del data[sheet_name][index_to_delete]
        save_data(data)
        return True
    return False

# =======================================================
#                FONCTIONS UTILITAIRES
# =======================================================
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
    return "❌ INCOMPLET"

def update_driver_vehicle_info(driver_name, brand, vehicle_type, displacement):
    df_users = fetch_data("Users")
    driver_row = df_users[(df_users["First Name"] == driver_name) & (df_users["Category"] == "Driver")]
    if not driver_row.empty:
        df_index = driver_row.index[0]
        update_row_field("Users", df_index, "Vehicle Brand", brand)
        update_row_field("Users", df_index, "Vehicle Type", vehicle_type)
        update_row_field("Users", df_index, "Engine Displacement", displacement)
        return True
    return False

def update_user_online_status(user_name, is_online):
    df_users = fetch_data("Users")
    user_row = df_users[df_users["First Name"] == user_name]
    if not user_row.empty:
        df_index = user_row.index[0]
        if is_online:
            update_row_field("Users", df_index, "Login Time", time.time())
        else:
            update_row_field("Users", df_index, "Login Time", 0)
        update_row_field("Users", df_index, "Is Online", is_online)

def get_connection_time(user_name):
    df_users = fetch_data("Users")
    user_row = df_users[df_users["First Name"] == user_name]
    if user_row.empty or not user_row["Is Online"].iloc[0]:
        return "0s"
    login_time = float(user_row["Login Time"].iloc[0])
    if login_time == 0 or pd.isna(login_time):
        return "0s"
    duration = int(time.time() - login_time)
    hours, remainder = divmod(duration, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h{minutes:02d}m"
    elif minutes > 0:
        return f"{minutes}m{seconds:02d}s"
    else:
        return f"{seconds}s"

def get_delivery_time(user_name):
    df_users = fetch_data("Users")
    user_row = df_users[df_users["First Name"] == user_name]
    if user_row.empty:
        return "0s"
    delivery_time = float(user_row["Delivery Start Time"].iloc[0])
    if delivery_time == 0 or pd.isna(delivery_time):
        return "0s"
    duration = int(time.time() - delivery_time)
    hours, remainder = divmod(duration, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h{minutes:02d}m"
    elif minutes > 0:
        return f"{minutes}m{seconds:02d}s"
    else:
        return f"{seconds}s"

def set_delivery_start_time(driver_name):
    df_users = fetch_data("Users")
    driver_row = df_users[(df_users["First Name"] == driver_name) & (df_users["Category"] == "Driver")]
    if not driver_row.empty:
        df_index = driver_row.index[0]
        update_row_field("Users", df_index, "Delivery Start Time", time.time())

def reset_delivery_time(driver_name):
    df_users = fetch_data("Users")
    driver_row = df_users[(df_users["First Name"] == driver_name) & (df_users["Category"] == "Driver")]
    if not driver_row.empty:
        df_index = driver_row.index[0]
        update_row_field("Users", df_index, "Delivery Start Time", 0)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password_strength(password):
    if len(password) < 6:
        return False, "Mot de passe : Au moins 6 caractères avec une majuscule et un chiffre"
    if not re.search(r"[A-Z]", password):
        return False, "Au moins 1 majuscule"
    return True, ""

def logout_button():
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🚪 Déconnexion"):
            if st.session_state.get('user_category') in ["Driver", "Admin"]:
                update_user_online_status(st.session_state.user_name, False)
            for key in ['logged_in', 'page', 'user_name', 'user_category', 'user_phone', 'driver_accepted_trip']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.logged_in = False
            st.session_state.page = "login"
            st.success("Déconnexion réussie ✅")
            st.rerun()

def get_base64_image(file):
    """Convertit un fichier téléchargé en chaîne Base64."""
    if file is None:
        return ""
    bytes_data = file.read()
    return base64.b64encode(bytes_data).decode('utf-8')
    
# =======================================================
#                PAGES DE L'APPLICATION
# =======================================================
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
        # Admin hardcodé
        if login_name == ADMIN_USERNAME:
            if hash_password(login_pass) == ADMIN_PASSWORD_HASH:
                st.session_state.logged_in = True
                st.session_state.user_name = ADMIN_USERNAME
                st.session_state.user_category = "Admin"
                st.session_state.user_phone = "000000000"
                st.success(f"Bienvenue Admin {ADMIN_USERNAME} 👋")
                st.rerun()
            else:
                st.error("❌ Mot de passe admin incorrect")
                return
            
        # Utilisateurs JSON
        users_df = fetch_data("Users")
        if users_df.empty:
            st.error("Aucun utilisateur enregistré")
            return
        
        row = users_df[users_df["First Name"] == login_name]
        if row.empty:
            st.error("❌ Prénom introuvable")
            return
        
        if hash_password(login_pass) != row["Password"].iloc[0]:
            st.error("❌ Mot de passe incorrect")
            return
        
        st.session_state.logged_in = True
        st.session_state.user_name = row["First Name"].iloc[0]
        st.session_state.user_category = row["Category"].iloc[0]
        st.session_state.user_phone = row["Phone"].iloc[0]
        
        if st.session_state.user_category == "Driver":
            update_user_online_status(st.session_state.user_name, True)
        
        st.success(f"Bienvenue {st.session_state.user_name} 👋")
        st.rerun()
    
    if st.button("➕ Créer un compte"):
        st.session_state.page = "register"
        st.rerun()

def show_register_page():
    st.title("Créer un Compte")
    with st.form("register_form"):
        category = st.selectbox("Catégorie", ["Client", "Driver"], key="reg_category")
        first_name = st.text_input("Prénom", key="reg_name")
        phone = st.text_input("Téléphone", key="reg_phone")
        password = st.text_input("Mot de passe", type="password", key="reg_password")
        profile_photo = None
        if category == "Client":
            st.subheader("Photo de Profil (Optionnel)")
            profile_photo = st.file_uploader("Choisissez une image (PNG/JPG)", type=["png", "jpg", "jpeg"], key="reg_photo")
        
        # Ajout des champs véhicule pour les Drivers
        vehicle_brand = ""
        vehicle_type = ""
        engine_displacement = ""
        
        if category == "Driver":
            st.subheader("Informations Véhicule")
            vehicle_brand = st.text_input("Marque du Véhicule", key="reg_brand")
            vehicle_type = st.selectbox("Type de Véhicule", ["Voiture", "Moto", "Camionnette"], key="reg_type")
            engine_displacement = st.text_input("Cylindrée (ex: 1.0L)", key="reg_displacement")
        
        submitted = st.form_submit_button("Créer")

    # Traitement de la soumission du formulaire
    if submitted:
        if first_name.lower() in ['admin', 'taxi']:
            st.error("Prénom réservé")
            return
            
        ok, msg = check_password_strength(password)
        if not ok:
            st.error(msg)
            return
            
        df = fetch_data("Users")
        if first_name in df["First Name"].values:
            st.error("Prénom existe déjà")
            return
            
        # Si la catégorie est Driver, les champs ne doivent pas être vides
        if category == "Driver" and (not vehicle_brand or not vehicle_type or not engine_displacement):
            st.error("Veuillez renseigner toutes les informations du véhicule.")
            return

        # Création du nouvel utilisateur
        new_user = {
            "Category": category,
            "First Name": first_name,
            "Phone": phone,
            "Password": hash_password(password),
            "Vehicle Brand": vehicle_brand,
            "Vehicle Type": vehicle_type,
            "Engine Displacement": engine_displacement,
            "Is Online": False,
            "Login Time": 0,
            "Delivery Start Time": 0
        }
            
        append_row("Users", new_user)
        st.success("✅ Compte créé ! Vous pouvez maintenant vous connecter.")
        # Retour à la page de connexion après création réussie
        st.session_state.page = "login"
        st.rerun()
    
    if st.button("← Retour"):
        if "page" in st.session_state:
            del st.session_state.page
        st.rerun()

def show_admin_page():
    st.title(f"🔧 Admin : {st.session_state.user_name}")
    logout_button()
    
    df_users = fetch_data("Users")
    df_trips = fetch_data("Trips")
    
    # onglet Clients
    tab1, tab2 = st.tabs(["👥 Clients", "🚗 Drivers"])
    
    with tab1:
        clients = df_users[df_users["Category"] == "Client"]
        if not clients.empty:
            client_data = []
            for idx, client in clients.iterrows():
                status_online = "🟢 En ligne" if client['Is Online'] else "🔴 Hors ligne"
                conn_time = get_connection_time(client['First Name'])
                client_data.append({
                    "Client": client['First Name'],
                    "Téléphone": client['Phone'],
                    "Statut": status_online,
                    "Connexion": conn_time,
                    "Index": idx
                })
            st.dataframe(pd.DataFrame(client_data), use_container_width=True)
            
            # Boutons suppression clients
            st.markdown("---")
            for row_data in client_data:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{row_data['Client']}** - {row_data['Connexion']}")
                with col2:
                    st.metric("Connexion", row_data['Connexion'])
                with col3:
                    if st.button("🗑️ Supprimer", key=f"del_client_{row_data['Index']}"):
                        if delete_row("Users", row_data['Index']):
                            st.success(f"✅ {row_data['Client']} supprimé")
                            st.rerun()
        else:
            st.info("Aucun client")
    
    with tab2:
        drivers = df_users[df_users["Category"] == "Driver"]
        if drivers.empty:
            st.info("Aucun driver")
            return
        
        driver_data = []
        for idx, driver in drivers.iterrows():
            status_online = "🟢 En ligne" if driver['Is Online'] else "🔴 Hors ligne"
            vehicle_info = get_driver_vehicle_info(driver['First Name'])
            
            accepted_trips = df_trips[(df_trips["Status"] == "Accepted") & (df_trips["Driver"] == driver['First Name'])]
            if not accepted_trips.empty:
                trip = accepted_trips.iloc[0]
                course_info = f"{trip['Start Point']} → {trip['End Point']}"
            else:
                course_info = "Disponible"
            
            conn_time = get_connection_time(driver['First Name'])
            delivery_time = get_delivery_time(driver['First Name'])
            
            driver_data.append({
                "Driver": driver['First Name'],
                "Téléphone": driver['Phone'],
                "Véhicule": vehicle_info,
                "Connexion": status_online,
                "Course": course_info,
                "⏱️": conn_time,
                "🚚": delivery_time,
                "Index": idx
            })
        
        st.dataframe(pd.DataFrame(driver_data), use_container_width=True)
        
        # Boutons suppression drivers
        st.markdown("---")
        for row_data in driver_data:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.write(f"**{row_data['Driver']}**")
            with col2:
                st.metric("Connexion", row_data['⏱️'])
            with col3:
                st.metric("Livraison", row_data['🚚'])
            with col4:
                if st.button("🗑️ Supprimer", key=f"del_driver_{row_data['Index']}"):
                    if delete_row("Users", row_data['Index']):
                        st.success(f"✅ {row_data['Driver']} supprimé")
                        st.rerun()

def show_client_page():
    st.title(f"👤 Client : {st.session_state.user_name}")
    logout_button()
    df_users = fetch_data("Users") # <--- Ligne corrigée (décalage vers la gauche)
    user_row = df_users[df_users["First Name"] == st.session_state.user_name].iloc[0]
    photo_base64 = user_row.get("Profile Photo", "")

    # Création de deux colonnes : une petite pour la photo, une grande pour le titre
    col_photo, col_title = st.columns([1, 4])
    
    with col_photo:
        # Affichage de la photo de profil ou d'un avatar par défaut
        if photo_base64:
            # Créer l'URL d'image Base64
            image_html = f'<img src="data:image/jpeg;base64,{photo_base64}" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover;">'
            st.markdown(image_html, unsafe_allow_html=True)
        else:
            st.image("allotaxi.ico", width=100) # Utiliser une icône par défaut

    with col_title:    
        # La suite du code de la page client a été décalée pour être alignée avec le with col_title:
        st.header("➕ Nouvelle course")
        with st.form("new_trip"):
            start = st.text_input("Départ")
            end = st.text_input("Arrivée")
            budget = st.number_input("Budget (Ar)", min_value=1000, value=5000)
            submitted = st.form_submit_button("Publier")
        
        if submitted and start and end:
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
            st.success("✅ Course publiée !")
            st.rerun()
        
    st.header("📋 Mes courses")
    df_trips = fetch_data("Trips")
    my_trips = df_trips[df_trips["Client Phone"] == st.session_state.user_phone]
    
    if my_trips.empty:
        st.info("Aucune course")
        return
    
    for idx, row in my_trips.iterrows():
        status_class = {
            "Available": "status-available",
            "Accepted": "status-accepted", 
            "Completed": "status-completed",
            "Cancelled": "status-cancelled"
        }.get(row['Status'], "")
        
        st.markdown(f"""
        <div class="trip-card">
            <h4>{row['Start Point']} → {row['End Point']}</h4>
            <p>💰 {row['Budget']} Ar</p>
            <p><span class="{status_class}">{row['Status']}</span></p>
            <p>Driver: {row['Driver'] or 'En attente'}</p>
        </div>
        """, unsafe_allow_html=True)

def show_driver_page():
    st.title(f"🚕 Driver : {st.session_state.user_name}")
    logout_button()
    
    vehicle_complete = has_complete_vehicle_info(st.session_state.user_name)
    vehicle_info = get_driver_vehicle_info(st.session_state.user_name)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Véhicule", vehicle_info)
    with col2:
        st.metric("Profil", "✅ Complet" if vehicle_complete else "❌ Incomplet")
    with col3:
        st.metric("Connexion", get_connection_time(st.session_state.user_name))
    
    if not vehicle_complete:
        st.error("⚠️ Complétez votre profil véhicule")
        
        # FORMULAIRE D'AJOUT/MISE À JOUR DU VÉHICULE
        with st.form("update_vehicle_form", clear_on_submit=True):
            st.subheader("Mettre à jour le Véhicule")
            
            # Récupérer les infos actuelles pour pré-remplir
            df_users = fetch_data("Users")
            driver_row_filter = df_users[(df_users["First Name"] == st.session_state.user_name) & (df_users["Category"] == "Driver")]
            
            current_brand = ""
            current_type = "Voiture"
            current_displacement = ""
            
            if not driver_row_filter.empty:
                driver_row = driver_row_filter.iloc[0]
                current_brand = driver_row["Vehicle Brand"] if pd.notna(driver_row["Vehicle Brand"]) else ""
                current_type = driver_row["Vehicle Type"] if pd.notna(driver_row["Vehicle Type"]) and driver_row["Vehicle Type"] in ["Voiture", "Moto", "Camionnette"] else "Voiture"
                current_displacement = driver_row["Engine Displacement"] if pd.notna(driver_row["Engine Displacement"]) else ""

            type_options = ["Voiture", "Moto", "Camionnette"]
            
            new_brand = st.text_input("Marque du Véhicule", value=current_brand, key="driver_brand")
            new_type = st.selectbox("Type de Véhicule", type_options, index=type_options.index(current_type), key="driver_type")
            new_displacement = st.text_input("Cylindrée (ex: 1.0L)", value=current_displacement, key="driver_displacement")
            
            vehicle_submitted = st.form_submit_button("Sauvegarder les infos véhicule")

        if vehicle_submitted:
            if new_brand and new_type and new_displacement:
                if update_driver_vehicle_info(st.session_state.user_name, new_brand, new_type, new_displacement):
                    st.success("✅ Informations véhicule mises à jour !")
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la mise à jour.")
            else:
                st.error("Veuillez remplir tous les champs du véhicule.")
            
        return
        
    df_trips = fetch_data("Trips")
    
    # Course en cours
    my_accepted = df_trips[(df_trips["Status"] == "Accepted") & (df_trips["Driver"] == st.session_state.user_name)]
    if not my_accepted.empty:
        trip = my_accepted.iloc[0]
        st.warning(f"🚨 Course : {trip['Start Point']} → {trip['End Point']}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🏁 Terminer", use_container_width=True):
                update_row_field("Trips", my_accepted.index[0], "Status", "Completed")
                reset_delivery_time(st.session_state.user_name)
                st.success("✅ Course terminée")
                st.rerun()
        with col2:
            if st.button("❌ Annuler", use_container_width=True):
                update_row_field("Trips", my_accepted.index[0], "Status", "Available")
                update_row_field("Trips", my_accepted.index[0], "Driver", "")
                reset_delivery_time(st.session_state.user_name)
                st.warning("Course annulée")
                st.rerun()
        with col3:
            st.metric("Livraison", get_delivery_time(st.session_state.user_name))
        return
    
    # Courses disponibles
    available = df_trips[df_trips["Status"] == "Available"]
    st.header(f"📍 Courses disponibles ({len(available)})")
    
    for idx, row in available.iterrows():
        with st.container():
            st.markdown(f"""
            <div class="trip-card">
                <h3>{row['Start Point']} → {row['End Point']}</h3>
                <p>💰 {row['Budget']} Ar</p>
                <p>Client: {row['Client Name']} ({row['Client Phone']})</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("✅ Accepter", key=f"accept_{idx}"):
                update_row_field("Trips", idx, "Status", "Accepted")
                update_row_field("Trips", idx, "Driver", st.session_state.user_name)
                set_delivery_start_time(st.session_state.user_name)
                st.success("✅ Course acceptée !")
                st.rerun()

# =======================================================
#                ROUTING PRINCIPAL
# =======================================================
load_data()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page" not in st.session_state:
    st.session_state.page = "login"

# --- DEBUT DU ROUTAGE (IF / ELIF / ELSE) ---

# 1. Page Enregistrement
if st.session_state.page == "register":
    show_register_page()
# 2. Page Connectée (Admin, Client, Driver)
elif st.session_state.logged_in:
    if st.session_state.user_category == "Admin":
        show_admin_page()
    elif st.session_state.user_category == "Client":
        show_client_page()
    elif st.session_state.user_category == "Driver":
        show_driver_page()
# 3. Page Déconnectée (Connexion)
else:
    show_login_page()

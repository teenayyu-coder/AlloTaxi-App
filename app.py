# app.py
import streamlit as st
import pandas as pd
import hashlib
import re
import json
import base64
from copy import deepcopy
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
    css = """
    body { font-family: 'Inter', sans-serif; }
    .trip-card {
        padding: 15px;
        border-radius: 12px;
        background: #f0f4f8;
        margin-bottom: 15px;
        border: 1px solid #dcdfe4;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .trip-card h3 { color: #333; border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-top: 0; }
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
    "Users": ["Category","First Name","Phone","Password","Vehicle Brand","Vehicle Type","Engine Displacement","Is Online"],
    "Trips": ["Client Name","Client Phone","Start Point","End Point","Budget","Status","Driver"]
}

# =======================================================
#               INITIAL DATA
# =======================================================
INITIAL_DATA = {
    "Users": [
        {"Category":"Admin","First Name":"admin","Phone":"000000000","Password":"8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918","Vehicle Brand":"","Vehicle Type":"","Engine Displacement":"","Is Online":False},
        {"Category":"Client","First Name":"testclient","Phone":"032111111","Password":"5e884898da28047151d0e56f8dc6292773603d0d6aabf35d2153c3e017d23d8c","Vehicle Brand":"","Vehicle Type":"","Engine Displacement":"","Is Online":False},
        {"Category":"Driver","First Name":"testdriver","Phone":"034222222","Password":"5e884898da28047151d0e56f8dc6292773603d0d6aabf35d2153c3e017d23d8c","Vehicle Brand":"Peugeot","Vehicle Type":"Voiture","Engine Displacement":"1.0L","Is Online":False}
    ],
    "Trips": [
        {"Client Name":"Admin","Client Phone":"000000000","Start Point":"Place de l'Indépendance","End Point":"Analakely","Budget":"5000","Status":"Available","Driver":""},
        {"Client Name":"testclient","Client Phone":"032111111","Start Point":"Antananarivo","End Point":"Imerina","Budget":"15000","Status":"Accepted","Driver":"testdriver"}
    ]
}

DEFAULT_REPO = "teenayyu-coder/AlloTaxi-App"
DEFAULT_FILE = "data.json"

def github_credentials_available():
    return all(k in st.secrets for k in ("GITHUB_TOKEN","GITHUB_REPO","GITHUB_FILE"))

def get_github_api_url():
    if github_credentials_available():
        repo = st.secrets["GITHUB_REPO"]
        filename = st.secrets["GITHUB_FILE"]
    else:
        repo = DEFAULT_REPO
        filename = DEFAULT_FILE
    return f"https://api.github.com/repos/{repo}/contents/{filename}"

# =======================================================
#               DATA HANDLING
# =======================================================
def load_data():
    if "data_store" in st.session_state:
        return st.session_state.data_store
    if github_credentials_available():
        api_url = get_github_api_url()
        headers = {"Authorization": f"Bearer {st.secrets['GITHUB_TOKEN']}"}
        try:
            r = requests.get(api_url, headers=headers)
            if r.status_code==200:
                content = r.json()
                file_content = base64.b64decode(content["content"]).decode()
                st.session_state.data_store = json.loads(file_content)
                st.session_state.file_sha = content.get("sha")
                return st.session_state.data_store
            elif r.status_code==404:
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
    headers = {"Authorization": f"Bearer {st.secrets['GITHUB_TOKEN']}","Content-Type":"application/json"}
    payload = {"message":"Update data.json","content":base64.b64encode(json.dumps(data,indent=4).encode()).decode()}
    if not initial_create and st.session_state.get("file_sha"):
        payload["sha"] = st.session_state.file_sha
    try:
        r = requests.put(api_url, headers=headers, data=json.dumps(payload))
        resp = r.json()
        new_sha = resp.get("content",{}).get("sha")
        if new_sha: st.session_state.file_sha = new_sha
    except:
        pass

def fetch_data(sheet_name):
    data = load_data()
    df = pd.DataFrame(data.get(sheet_name,[]))
    for col in SHEET_SCHEMAS.get(sheet_name,[]):
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
    if sheet_name in data and 0<=index_to_update<len(data[sheet_name]):
        data[sheet_name][index_to_update][field]=new_value
        save_data(data)
        return True
    return False

def update_user_online_status(user_name, is_online):
    df = fetch_data("Users")
    row = df[df["First Name"]==user_name]
    if not row.empty:
        idx = row.index[0]
        update_row_field("Users", idx, "Is Online", is_online)

# =======================================================
#               UTILITAIRES
# =======================================================
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def check_password_strength(pw):
    if len(pw)<6: return False,"Le mot de passe doit contenir au moins 6 caractères."
    if not re.search(r"[A-Z]",pw): return False,"Le mot de passe doit contenir au moins une majuscule."
    return True,""

def logout_button():
    col1,col2 = st.columns([4,1])
    with col2:
        if st.button("🚪 Déconnexion"):
            if st.session_state.user_category in ["Driver","Admin"]:
                update_user_online_status(st.session_state.user_name, False)
            st.session_state.logged_in=False
            st.session_state.page="login"
            st.session_state.user_name=None
            st.session_state.user_category=None
            st.session_state.user_phone=None
            st.session_state.driver_accepted_trip=None
            st.success("Déconnecté ✔️")
            st.experimental_rerun()

# =======================================================
#               PAGE LOGIN
# =======================================================
def login_page():
    if LOGO_BASE64:
        st.markdown(f"""<div style='display:flex;align-items:center;justify-content:center;margin-bottom:20px;'>
        <img src="data:image/x-icon;base64,{LOGO_BASE64}" width="60" height="55"/>
        <h1 style="margin-left:10px;">lloTaxi</h1></div>""", unsafe_allow_html=True)
    else:
        st.title("AlloTaxi")
    st.header("Connexion")
    with st.form("login_form"):
        name = st.text_input("Prénom")
        pw = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")
    if submitted:
        df = fetch_data("Users")
        row = df[df["First Name"]==name]
        if row.empty:
            st.error("Prénom introuvable")
        elif hash_password(pw)!=row["Password"].iloc[0]:
            st.error("Mot de passe incorrect")
        else:
            st.session_state.logged_in=True
            st.session_state.user_name=row["First Name"].iloc[0]
            st.session_state.user_category=row["Category"].iloc[0]
            st.session_state.user_phone=row["Phone"].iloc[0]
            if st.session_state.user_category in ["Driver","Admin"]:
                update_user_online_status(st.session_state.user_name, True)
            st.success(f"Bienvenue {st.session_state.user_name} 👋")
            # Change la page selon catégorie
            st.session_state.page=st.session_state.user_category.lower()
            st.experimental_rerun()
    if st.button("Créer un compte"):
        st.session_state.page="register"
        st.experimental_rerun()

# =======================================================
#               PAGE REGISTER
# =======================================================
def register_page():
    st.title("✍️ Créer un Compte AlloTaxi")
    with st.form("register_form"):
        category = st.selectbox("Catégorie", ["Client","Driver"])
        first_name = st.text_input("Prénom")
        phone = st.text_input("Téléphone")
        password = st.text_input("Mot de passe", type="password")
        driver_data={}
        if category=="Driver":
            st.subheader("Informations Véhicule")
            driver_data["Vehicle Brand"]=st.text_input("Marque du véhicule")
            driver_data["Vehicle Type"]=st.selectbox("Type du véhicule", ["Voiture","Moto"])
            driver_data["Engine Displacement"]=st.text_input("Cylindrée")
        submitted = st.form_submit_button("Créer le compte")
    if submitted:
        if first_name.lower()=="admin":
            st.error("Le prénom 'admin' est réservé.")
        else:
            ok,msg=check_password_strength(password)
            if not ok:
                st.error(msg)
            else:
                df = fetch_data("Users")
                if first_name in df["First Name"].values:
                    st.error("Ce prénom existe déjà.")
                else:
                    new_user={
                        "Category":category,
                        "First Name":first_name,
                        "Phone":phone,
                        "Password":hash_password(password),
                        "Vehicle Brand":driver_data.get("Vehicle Brand",""),
                        "Vehicle Type":driver_data.get("Vehicle Type",""),
                        "Engine Displacement":driver_data.get("Engine Displacement",""),
                        "Is Online":False
                    }
                    append_row("Users", new_user)
                    st.success("Compte créé ! Vous pouvez vous connecter.")
                    st.session_state.page="login"
                    st.experimental_rerun()
    if st.button("Retour"):
        st.session_state.page="login"
        st.experimental_rerun()

# =======================================================
#               PAGE CLIENT
# =======================================================
def client_page():
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
            st.error("Remplissez tous les champs")
        else:
            new_trip={
                "Client Name":st.session_state.user_name,
                "Client Phone":st.session_state.user_phone,
                "Start Point":start,
                "End Point":end,
                "Budget":str(int(budget)),
                "Status":"Available",
                "Driver":""
            }
            append_row("Trips", new_trip)
            st.success("Course ajoutée ✅")
    st.markdown("---")
    st.header("Historique des courses")
    df=fetch_data("Trips")
    trips=df[df["Client Phone"]==st.session_state.user_phone]
    if trips.empty:
        st.info("Aucune course.")
    else:
        for idx,row in trips.sort_index(ascending=False).iterrows():
            status_color={
                "Available":"status-available",
                "Accepted":"status-accepted",
                "Completed":"status-completed",
                "Cancelled":"status-cancelled"
            }.get(row["Status"],"status-completed")
            st.markdown(f"""
            <div class="trip-card">
            <h4>{row['Start Point']} → {row['End Point']}</h4>
            <p>💰 Budget : <b>{row['Budget']} Ar</b></p>
            <p>🏁 Statut : <span class="{status_color}">{row['Status']}</span></p>
            <p>🚕 Driver Assigné : <b>{row['Driver'] if row['Driver'] else 'En attente'}</b></p>
            </div>
            """,unsafe_allow_html=True)

# =======================================================
#               PAGE DRIVER
# =======================================================
def driver_page():
    st.title(f"🏍️ Driver : Bonjour {st.session_state.user_name}")
    logout_button()
    df=fetch_data("Trips")
    accepted=df[(df["Status"]=="Accepted") & (df["Driver"]==st.session_state.user_name)]
    if not accepted.empty:
        idx=accepted.index[0]
        row=accepted.iloc[0]
        st.warning(f"🚨 Course en cours : {row['Start Point']} → {row['End Point']} (Client: {row['Client Name']})")
        col1,col2,_=st.columns([1.5,1.5,3])
        with col1:
            if st.button("🏁 Terminer la course",key=f"finish_{idx}"):
                update_row_field("Trips", idx, "Status","Completed")
                st.success("Course terminée !")
                st.experimental_rerun()
        with col2:
            if st.button("❌ Annuler la course",key=f"cancel_{idx}"):
                update_row_field("Trips", idx, "Status","Available")
                update_row_field("Trips", idx, "Driver","")
                st.warning("Course annulée.")
                st.experimental_rerun()
        return
    avail=df[df["Status"]=="Available"]
    st.header(f"Courses disponibles ({len(avail)})")
    st.markdown("---")
    if avail.empty:
        st.info("Aucune course disponible")
        return
    for idx,row in avail.iterrows():
        with st.container():
            st.markdown(f"""
            <div class="trip-card">
            <h3>🚗 Course #{idx+1}</h3>
            <p>📍 Départ : <b>{row['Start Point']}</b></p>
            <p>🏁 Arrivée : <b>{row['End Point']}</b></p>
            <p>💰 Budget : <b>{row['Budget']} Ar</b></p>
            <p style="font-size:small;color:#6c757d;">(Client: {row['Client Name']} / Tél: {row['Client Phone']})</p>
            </div>
            """,unsafe_allow_html=True)
            if st.button("✅ Accepter cette course",key=f"acc_{idx}"):
                update_row_field("Trips", idx,"Status","Accepted")
                update_row_field("Trips", idx,"Driver",st.session_state.user_name)
                st.success("Course acceptée ✅")
                st.experimental_rerun()
            st.markdown("---")

# =======================================================
#               PAGE ADMIN
# =======================================================
def admin_page():
    st.title("👑 Admin : Gestion des Drivers")
    logout_button()
    st.markdown("---")
    st.header("Statut des Drivers")
    df_users=fetch_data("Users")
    df_trips=fetch_data("Trips")
    drivers=df_users[df_users["Category"]=="Driver"]
    if drivers.empty:
        st.info("Aucun driver")
        return
    accepted_trips=df_trips[df_trips["Status"]=="Accepted"]
    driver_list=[]
    for _,d in drivers.iterrows():
        name=d["First Name"]
        trip_in_prog=accepted_trips[accepted_trips["Driver"]==name]
        status_online="🟢 En Ligne" if d["Is Online"] else "🔴 Hors Ligne"
        if not trip_in_prog.empty:
            trip_info=f"En Course: {trip_in_prog.iloc[0]['Start Point']} → {trip_in_prog.iloc[0]['End Point']} (Client: {trip_in_prog.iloc[0]['Client Name']})"
            status_race="🟡 EN COURSE"
        else:
            trip_info="En attente de course"
            status_race="✅ Disponible"
        driver_list.append({"Driver":name,"Statut Connexion":status_online,"Statut Course":status_race,"Course en Cours":trip_info})
    st.dataframe(pd.DataFrame(driver_list),use_container_width=True)

# =======================================================
#               MAIN
# =======================================================
load_data()

if "logged_in" not in st.session_state: st.session_state.logged_in=False
if "page" not in st.session_state: st.session_state.page="login"

if st.session_state.page=="login": login_page()
elif st.session_state.page=="register": register_page()
elif st.session_state.logged_in:
    if st.session_state.page=="client": client_page()
    elif st.session_state.page=="driver": driver_page()
    elif st.session_state.page=="admin": admin_page()
else:
    login_page()

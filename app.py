# app.py
import streamlit as st
import pandas as pd
import hashlib
import json
import base64
from copy import deepcopy
import requests

# =======================================================
# CONFIGURATION STREAMLIT
# =======================================================
st.set_page_config(page_title="AlloTaxi", layout="wide", initial_sidebar_state="collapsed")

# =======================================================
# LOGO
# =======================================================
def load_logo_base64():
    try:
        with open("allotaxi.ico", "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

LOGO_BASE64 = load_logo_base64()

# =======================================================
# CSS pour cartes et couleurs
# =======================================================
st.markdown("""
<style>
.trip-card { padding:15px; border-radius:12px; background:#f0f4f8; margin-bottom:15px; border:1px solid #dcdfe4; box-shadow:2px 2px 5px rgba(0,0,0,0.05);}
.trip-card h3 { color:#333; border-bottom:2px solid #ddd; padding-bottom:5px; margin-top:0;}
.status-available { color:#28a745; font-weight:bold;}
.status-accepted { color:#ffc107; font-weight:bold;}
.status-completed { color:#6c757d; font-weight:bold;}
.status-cancelled { color:#dc3545; font-weight:bold;}
</style>
""", unsafe_allow_html=True)

# =======================================================
# SCHEMAS
# =======================================================
SHEET_SCHEMAS = {
    "Users": ["Category", "First Name", "Phone", "Password", "Vehicle Brand", "Vehicle Type", "Engine Displacement", "Is Online"],
    "Trips": ["Client Name", "Client Phone", "Start Point", "End Point", "Budget", "Status", "Driver"]
}

# =======================================================
# DONNÉES INITIALES
# =======================================================
INITIAL_DATA = {
    "Users": [
        {"Category":"Admin","First Name":"admin","Phone":"000000000","Password":hashlib.sha256("admin".encode()).hexdigest(),"Vehicle Brand":"","Vehicle Type":"","Engine Displacement":"","Is Online":False},
        {"Category":"Client","First Name":"testclient","Phone":"032111111","Password":hashlib.sha256("password".encode()).hexdigest(),"Vehicle Brand":"","Vehicle Type":"","Engine Displacement":"","Is Online":False},
        {"Category":"Driver","First Name":"testdriver","Phone":"034222222","Password":hashlib.sha256("password".encode()).hexdigest(),"Vehicle Brand":"Peugeot","Vehicle Type":"Voiture","Engine Displacement":"1.0L","Is Online":False}
    ],
    "Trips": [
        {"Client Name":"admin","Client Phone":"000000000","Start Point":"Place de l'Indépendance","End Point":"Analakely","Budget":"5000","Status":"Available","Driver":""},
        {"Client Name":"testclient","Client Phone":"032111111","Start Point":"Antananarivo","End Point":"Imerina","Budget":"15000","Status":"Accepted","Driver":"testdriver"}
    ]
}

# =======================================================
# GESTION JSON LOCALE
# =======================================================
def load_data():
    if "data_store" in st.session_state:
        return st.session_state.data_store
    st.session_state.data_store = deepcopy(INITIAL_DATA)
    return st.session_state.data_store

def save_data():
    st.session_state.data_store = st.session_state.data_store  # pas de GitHub, juste session_state

def fetch_df(sheet_name):
    data = load_data()
    df = pd.DataFrame(data.get(sheet_name, []))
    for col in SHEET_SCHEMAS[sheet_name]:
        if col not in df.columns:
            df[col] = ""
    return df

def append_row(sheet_name, row_dict):
    data = load_data()
    if sheet_name not in data:
        data[sheet_name] = []
    data[sheet_name].append(row_dict)
    save_data()

def update_row(sheet_name, index, field, value):
    data = load_data()
    if sheet_name in data and 0 <= index < len(data[sheet_name]):
        data[sheet_name][index][field] = value
        save_data()
        return True
    return False

# =======================================================
# HASH MOT DE PASSE
# =======================================================
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# =======================================================
# LOGOUT
# =======================================================
def logout():
    if st.session_state.user_category in ["Driver", "Admin"]:
        df = fetch_df("Users")
        idx = df[df["First Name"]==st.session_state.user_name].index[0]
        update_row("Users", idx, "Is Online", False)
    st.session_state.logged_in=False
    st.session_state.page="login"
    st.session_state.user_name=None
    st.session_state.user_category=None
    st.session_state.user_phone=None
    st.experimental_rerun()

# =======================================================
# LOGIN PAGE
# =======================================================
def login_page():
    if LOGO_BASE64:
        st.markdown(f"""<div style='display:flex;align-items:center;justify-content:center;margin-bottom:20px;'>
        <img src="data:image/x-icon;base64,{LOGO_BASE64}" width="60" height="55"/>
        <h1 style="margin-left:10px;">AlloTaxi</h1></div>""", unsafe_allow_html=True)
    else:
        st.title("AlloTaxi")
    st.header("Connexion")
    with st.form("login_form"):
        name = st.text_input("Prénom")
        pw = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")
    if submitted:
        df = fetch_df("Users")
        row = df[df["First Name"]==name]
        if row.empty:
            st.error("Prénom introuvable")
            return
        if hash_pw(pw)!=row["Password"].iloc[0]:
            st.error("Mot de passe incorrect")
            return
        st.session_state.logged_in=True
        st.session_state.user_name=row["First Name"].iloc[0]
        st.session_state.user_category=row["Category"].iloc[0]
        st.session_state.user_phone=row["Phone"].iloc[0]
        if st.session_state.user_category in ["Driver", "Admin"]:
            idx = df[df["First Name"]==st.session_state.user_name].index[0]
            update_row("Users", idx, "Is Online", True)
        st.success(f"Bienvenue {st.session_state.user_name} 👋")
        st.experimental_rerun()
    if st.button("Créer un compte"):
        st.session_state.page="register"
        st.experimental_rerun()

# =======================================================
# REGISTER PAGE
# =======================================================
def register_page():
    st.title("Créer un compte AlloTaxi")
    with st.form("register_form"):
        cat = st.selectbox("Catégorie", ["Client","Driver"])
        name = st.text_input("Prénom")
        phone = st.text_input("Téléphone")
        pw = st.text_input("Mot de passe", type="password")
        driver_data={}
        if cat=="Driver":
            st.subheader("Informations Véhicule")
            driver_data["Vehicle Brand"]=st.text_input("Marque du véhicule")
            driver_data["Vehicle Type"]=st.selectbox("Type du véhicule", ["Voiture","Moto"])
            driver_data["Engine Displacement"]=st.text_input("Cylindrée")
        submitted=st.form_submit_button("Créer le compte")
    if submitted:
        if name.lower()=="admin":
            st.error("Prénom 'admin' réservé")
            return
        df = fetch_df("Users")
        if name in df["First Name"].values:
            st.error("Ce prénom existe déjà")
            return
        new_user={
            "Category":cat,
            "First Name":name,
            "Phone":phone,
            "Password":hash_pw(pw),
            "Vehicle Brand":driver_data.get("Vehicle Brand",""),
            "Vehicle Type":driver_data.get("Vehicle Type",""),
            "Engine Displacement":driver_data.get("Engine Displacement",""),
            "Is Online":False
        }
        append_row("Users", new_user)
        st.success("Compte créé avec succès !")
        if st.button("Retour à la connexion"):
            st.session_state.page="login"
            st.experimental_rerun()

# =======================================================
# ADMIN PAGE
# =======================================================
def admin_page():
    st.title(f"Admin : {st.session_state.user_name}")
    if st.button("Déconnexion"):
        logout()
    st.header("Statut des Drivers")
    df = fetch_df("Users")
    df_trips = fetch_df("Trips")
    drivers = df[df["Category"]=="Driver"]
    if drivers.empty:
        st.info("Aucun driver")
        return
    list_driver=[]
    for _, d in drivers.iterrows():
        driver_name=d["First Name"]
        in_course=df_trips[(df_trips["Driver"]==driver_name) & (df_trips["Status"]=="Accepted")]
        online="🟢 En ligne" if d["Is Online"] else "🔴 Hors ligne"
        course="En course" if not in_course.empty else "Disponible"
        list_driver.append({"Driver":driver_name,"Statut Connexion":online,"Statut Course":course})
    st.dataframe(pd.DataFrame(list_driver), use_container_width=True)

# =======================================================
# CLIENT PAGE
# =======================================================
def client_page():
    st.title(f"Client : {st.session_state.user_name}")
    if st.button("Déconnexion"):
        logout()
    st.header("Créer une nouvelle course")
    with st.form("trip_form"):
        start=st.text_input("Départ")
        end=st.text_input("Arrivée")
        budget=st.number_input("Budget (Ar)", min_value=1000)
        submitted=st.form_submit_button("Créer la course")
    if submitted:
        if not start or not end:
            st.error("Remplir tous les champs")
        else:
            new_trip={"Client Name":st.session_state.user_name,"Client Phone":st.session_state.user_phone,
                      "Start Point":start,"End Point":end,"Budget":str(budget),"Status":"Available","Driver":""}
            append_row("Trips", new_trip)
            st.success("Course ajoutée !")
    st.header("Mes courses")
    df=fetch_df("Trips")
    client_trips=df[df["Client Phone"]==st.session_state.user_phone]
    if client_trips.empty:
        st.info("Aucune course")
    else:
        for _, row in client_trips.iterrows():
            status_color={"Available":"status-available","Accepted":"status-accepted",
                          "Completed":"status-completed","Cancelled":"status-cancelled"}.get(row["Status"],"")
            st.markdown(f"""
            <div class="trip-card">
            <h3>{row['Start Point']} → {row['End Point']}</h3>
            <p>💰 {row['Budget']} Ar</p>
            <p>Statut: <span class="{status_color}">{row['Status']}</span></p>
            <p>Driver: {row['Driver'] if row['Driver'] else 'En attente'}</p>
            </div>
            """, unsafe_allow_html=True)

# =======================================================
# DRIVER PAGE
# =======================================================
def driver_page():
    st.title(f"Driver : {st.session_state.user_name}")
    if st.button("Déconnexion"):
        logout()
    df=fetch_df("Trips")
    accepted=df[(df["Status"]=="Accepted") & (df["Driver"]==st.session_state.user_name)]
    if not accepted.empty:
        idx=accepted.index[0]
        row=accepted.iloc[0]
        st.warning(f"Course en cours: {row['Start Point']} → {row['End Point']} (Client: {row['Client Name']})")
        col1,col2=st.columns(2)
        with col1:
            if st.button("Terminer la course"):
                update_row("Trips", idx,"Status","Completed")
                st.success("Course terminée")
                st.experimental_rerun()
        with col2:
            if st.button("Annuler la course"):
                update_row("Trips", idx,"Status","Available")
                update_row("Trips", idx,"Driver","")
                st.warning("Course annulée")
                st.experimental_rerun()
        return
    available=df[df["Status"]=="Available"]
    st.header(f"Courses disponibles ({len(available)})")
    if available.empty:
        st.info("Aucune course disponible")
        return
    for idx,row in available.iterrows():
        st.markdown(f"""
        <div class="trip-card">
        <h3>{row['Start Point']} → {row['End Point']}</h3>
        <p>💰 {row['Budget']} Ar</p>
        <p>Client: {row['Client Name']}</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"Accepter course #{idx}"):
            update_row("Trips", idx,"Driver",st.session_state.user_name)
            update_row("Trips", idx,"Status","Accepted")
            st.success("Course acceptée")
            st.experimental_rerun()

# =======================================================
# INITIALISATION SESSION
# =======================================================
if "logged_in" not in st.session_state: st.session_state.logged_in=False
if "page" not in st.session_state: st.session_state.page="login"
if "user_name" not in st.session_state: st.session_state.user_name=None
if "user_category" not in st.session_state: st.session_state.user_category=None
if "user_phone" not in st.session_state: st.session_state.user_phone=None

# =======================================================
# ROUTEUR
# =======================================================
if not st.session_state.logged_in:
    st.session_state.page="login"

if st.session_state.page=="login":
    login_page()
elif st.session_state.page=="register":
    register_page()
elif st.session_state.page=="admin":
    admin_page()
elif st.session_state.page=="client":
    client_page()
elif st.session_state.page=="driver":
    driver_page()
else:
    st.error("Page introuvable")

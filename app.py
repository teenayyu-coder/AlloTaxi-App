import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import hashlib
import re


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
#                CONNEXION GOOGLE SHEETS
# -------------------------------------------------------

GOOGLE_SHEET_ID = "1JUG3IuVPrIDkDqLxaRwfZh1ArWYarrS4pQIOSqDE1WY"
AUTO_RESET = True  # ⚙️ Option B — auto-reset destructif


@st.cache_resource
def get_google_sheet_client():
    try:
        creds_json = st.secrets["gcp_service_account"]
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Erreur connexion Google Sheets : {e}")
        return None


client = get_google_sheet_client()


# -------------------------------
#   DÉFINITION DES SCHEMAS
# -------------------------------

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


def ensure_sheet_exists(sheet_name):
    if not client:
        return None

    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    expected_cols = SHEET_SCHEMAS.get(sheet_name, [])

    try:
        ws = spreadsheet.worksheet(sheet_name)
        headers = ws.row_values(1)

        if headers != expected_cols:
            # Efface et recrée si structure incorrecte
            spreadsheet.del_worksheet(ws)
            ws = spreadsheet.add_worksheet(sheet_name, rows=100, cols=len(expected_cols))
            ws.append_row(expected_cols)
            st.warning(f"⚠️ Feuille '{sheet_name}' réinitialisée (structure incorrecte).")

        return ws

    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(sheet_name, rows=100, cols=len(expected_cols))
        ws.append_row(expected_cols)
        st.info(f"✅ Feuille '{sheet_name}' créée automatiquement.")
        return ws

    except Exception as e:
        st.error(f"Erreur accès feuille '{sheet_name}' : {e}")
        return None


def get_worksheet(sheet_name):
    return ensure_sheet_exists(sheet_name)


def fetch_data(sheet_name):
    ws = ensure_sheet_exists(sheet_name)
    if not ws:
        return pd.DataFrame(columns=SHEET_SCHEMAS.get(sheet_name, []))

    data = ws.get_all_records()
    if not data:
        return pd.DataFrame(columns=SHEET_SCHEMAS.get(sheet_name, []))

    df = pd.DataFrame(data)
    df.columns = df.columns.map(lambda x: str(x).strip())
    return df


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
#             BOUTON DÉCONNEXION GLOBAL
# -------------------------------------------------------

def logout_button():
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("Loggout"):
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

        if hash_password(login_pass) != row["Password"].iloc[0]:
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
            driver_data["Vehicle Type"] = st.selectbox(
                "Type du véhicule",
                ["Voiture", "Moto"]
            )
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

        ws = get_worksheet("Users")
        new_row = [
            category, first_name, phone,
            hash_password(password),
            driver_data.get("Vehicle Brand", ""),
            driver_data.get("Vehicle Type", ""),
            driver_data.get("Engine Displacement", "")
        ]
        ws.append_row(new_row)

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

        ws = get_worksheet("Trips")
        ws.append_row([
            st.session_state.user_name,
            st.session_state.user_phone,
            start_point,
            end_point,
            str(budget),
            "Available",
            ""
        ])
        st.success("Course ajoutée !")


# -------------------------------------------------------
#                   PAGE DRIVER
# -------------------------------------------------------

def show_driver_page():
    st.title(f"🏍️ Driver : Bonjour {st.session_state.user_name}")
    logout_button()

    df = fetch_data("Trips")

    accepted = df[(df["Status"] == "Accepted") &
                  (df["Driver"] == st.session_state.user_name)]

    if not accepted.empty:
        row = accepted.iloc[0]
        st.warning(f"🚨 Course en cours : {row['Start Point']} → {row['End Point']}")

        if st.button("Terminer la course"):
            ws = get_worksheet("Trips")
            gs_row = accepted.index[0] + 2
            ws.update_cell(gs_row, df.columns.get_loc("Status") + 1, "Completed")
            st.session_state.driver_accepted_trip = None
            st.success("Course terminée !")
            st.rerun()
        return

    avail = df[df["Status"] == "Available"]
    st.header(f"Courses disponibles ({len(avail)})")
    st.markdown("---")

    if avail.empty:
        st.info("Aucune course disponible.")
        return

    for index, row in avail.iterrows():
        gs_row = index + 2
        st.markdown(f"""
            <div class="trip-card">
                <h3>Course #{index + 1}</h3>
                <p>📍 Départ : <b>{row["Start Point"]}</b></p>
                <p>🏁 Arrivée : <b>{row["End Point"]}</b></p>
                <p>💰 Budget : <b>{row["Budget"]} Ar</b></p>
            </div>
        """, unsafe_allow_html=True)

        if st.button("Accepter cette course", key=f"acc_{index}"):
            ws = get_worksheet("Trips")
            ws.update_cell(gs_row, df.columns.get_loc("Status") + 1, "Accepted")
            ws.update_cell(gs_row, df.columns.get_loc("Driver") + 1, st.session_state.user_name)
            st.session_state.driver_accepted_trip = f"{row['Start Point']} → {row['End Point']}"
            st.success("Course acceptée !")
            st.rerun()
        st.markdown("---")


# -------------------------------------------------------
#                ROUTING PRINCIPAL
# -------------------------------------------------------

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "page" not in st.session_state:
    st.session_state.page = "login"


if not client:
    st.error("Impossible de se connecter à Google Sheets.")
elif st.session_state.page == "register":
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



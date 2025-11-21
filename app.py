import streamlit as st
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
ws.update_cell(gs_row, TRIPS_COLUMNS.index("Driver") + 1, st.session_state.user_name); st.rerun()

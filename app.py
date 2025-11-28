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
#               DONNÉES INITIALES JSON
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

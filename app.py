import streamlit as st
import pandas as pd
import google.generativeai as genai
import re

# --- 1. UI CONFIGURATION ---
st.set_page_config(page_title="Europe 2026", page_icon="🌍", layout="wide")

custom_css = """
<style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    
    /* 1. ABSOLUTE CENTERING */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 600px !important; 
        margin: 0 auto !important;   
    }
    
    /* 2. ANTI-STACKING: Force Streamlit to NEVER stack columns vertically on mobile */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        margin-bottom: 10px !important;
        gap: 6px !important;
    }

    /* =========================================================
       THE "INVISIBLE ANCHOR" #1: TARGETS EXACTLY 2 COLUMNS (Mode Toggle)
       ========================================================= */
    div[data-testid="column"]:first-child:nth-last-child(2),
    div[data-testid="column"]:first-child:nth-last-child(2) ~ div[data-testid="column"] {
        width: 50% !important;
        flex: 1 1 50% !important;
        min-width: 0 !important;
    }
    
    /* Sleek Horizontal Pill Buttons */
    div[data-testid="column"]:first-child:nth-last-child(2) div.stButton > button,
    div[data-testid="column"]:first-child:nth-last-child(2) ~ div[data-testid="column"] div.stButton > button {
        height: 40px !important; 
        border-radius: 20px !important; 
        font-weight: 700 !important;
        font-size: 14px !important;
        border: 1px solid #d1d5db !important;
        background-color: #ffffff !important;
        color: #1c1e21 !important;
        display: flex !important;
        flex-direction: row !important; /* Side-by-side text */
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s;
        width: 100% !important;
    }
    
    /* Active Toggle State */
    div[data-testid="column"]:first-child:nth-last-child(2) div.stButton > button[kind="primary"],
    div[data-testid="column"]:first-child:nth-last-child(2) ~ div[data-testid="column"] div.stButton > button[kind="primary"] {
        background-color: #007AFF !important;
        color: white !important;
        border-color: #007AFF !important;
        box-shadow: 0 2px 5px rgba(0,122,255,0.3) !important;
    }

    /* =========================================================
       THE "INVISIBLE ANCHOR" #2: TARGETS EXACTLY 7 COLUMNS (Calendar Grid)
       ========================================================= */
    div[data-testid="column"]:first-child:nth-last-child(7),
    div[data-testid="column"]:first-child:nth-last-child(7) ~ div[data-testid="column"] {
        width: 14.28% !important;
        flex: 1 1 14.28% !important;
        min-width: 0 !important;
    }
    
    /* Naked Vertical Calendar Buttons */
    div[data-testid="column"]:first-child:nth-last-child(7) div.stButton > button,
    div[data-testid="column"]:first-child:nth-last-child(7) ~ div[data-testid="column"] div.stButton > button {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #9ca3af; 
        height: 60px !important; 
        width: 100% !important;
        padding: 0px !important;
        font-size: 11px !important; 
        font-weight: 600; 
        white-space: pre-wrap !important;
        line-height: 1.2;
        display: flex !important;
        flex-direction: column !important; /* Stacked text and flag */
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
    }
    
    div[data-testid="column"]:first-child:nth-last-child(7) div.stButton > button:hover,
    div[data-testid="column"]:first-child:nth-last-child(7) ~ div[data-testid="column"] div.stButton > button:hover { 
        color: #1c1e21 !important; 
    }
    
    /* Active Calendar Day State */
    div[data-testid="column"]:first-child:nth-last-child(7) div.stButton > button[kind="primary"],
    div[data-testid="column"]:first-child:nth-last-child(7) ~ div[data-testid="column"] div.stButton > button[kind="primary"] { 
        color: #007AFF !important; 
        font-weight: 800 !important;
        background-color: #eff6ff !important;
        border-radius: 8px !important;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 2. DATA LOADING & FLAG SCANNER ---
@st.cache_data
def load_data():
    try:
        with open("itinerary.md", "r", encoding="utf-8") as file:
            return file.read().replace('\r', '') 
    except FileNotFoundError:
        return "Error: Itinerary file not found."

raw_text = load_data()

def get_country_flag(text_content):
    if any(city in text_content for city in ["Lisbon", "Porto", "Sintra", "Alfama", "Portugal"]):
        return "🇵🇹"
    elif any(city in text_content for city in ["San Sebastián", "Oviedo", "Spain", "Basque"]):
        return "🇪🇸"
    elif any(city in text_content for city in ["Munich", "Germany", "Bavaria"]):
        return "🇩🇪"
    elif any(city in text_content for city in ["London", "UK", "England"]):
        return "🇬🇧"
    return "🌍"

# --- 3. THE SCANNER ---
weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
days_db = {}
directories_db = {}
current_bucket = None

for line in raw_

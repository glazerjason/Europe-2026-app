import streamlit as st
import pandas as pd
import google.generativeai as genai
import re

# --- 1. UI CONFIGURATION & CSS GRID ---
st.set_page_config(page_title="Europe 2026", page_icon="🌍", layout="centered")

custom_css = """
<style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    
    /* 1. PERFECT CENTERING: Force balanced left/right padding so the app doesn't drift right */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }

    /* Make Tabs look like native iOS Segmented Controls */
    div[data-testid="stTabs"] > div {
        display: flex;
        justify-content: space-evenly;
        background-color: #f3f4f6;
        border-radius: 12px;
        padding: 4px;
        margin-bottom: 15px;
    }
    button[data-baseweb="tab"] {
        flex: 1;
        border-radius: 8px !important;
        padding: 10px 0px !important;
        font-weight: 700 !important;
    }
    button[aria-selected="true"] {
        background-color: white !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
        color: #007AFF !important;
    }
    
    /* THE CSS GRID: Rigid 7-column calendar */
    div[data-testid="stVerticalBlock"] > div > div[data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: repeat(7, 1fr) !important;
        gap: 4px !important;
        margin-bottom: 4px !important;
        width: 100% !important;
    }
    
    /* Naked Calendar Buttons - Now Forced Dead Center */
    div.stButton > button {
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
        
        /* Forces the text/flag to stay perfectly centered in the button */
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
    }
    
    div.stButton > button:hover { color: #1c1e21 !important; }
    
    /* Active Calendar Day */
    div.stButton > button[kind="primary"] { 
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

for line in raw_text.split('\n'):
    clean_line = line.strip()
    if clean_line.startswith('#'):
        header_text = re.sub(r'^#{1,2}\s+', '', clean_line).strip()
        if 'DIRECTORY' in header_text:
            current_bucket = header_text.replace('📚 DIRECTORY:', '').strip()
            directories_db[current_bucket] = ""
            continue
        elif any(day in header_text for day in weekdays):
            current_bucket = header_text
            days_db[current_bucket] = ""
            continue

    if current_bucket in directories_db:
        directories_db[current_bucket] += line + "\n"
    elif current_bucket in days_db:
        days_db[current_bucket] += line + "\n"

day_keys = list(days_db.keys())

if "selected_day" not in st.session_state:
    st.session_state.selected_day = day_keys[0]

day_map = {"Sunday": 0, "Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5, "Saturday": 6}
weeks = []
current_week = [None] * 7
last_idx = -1

for day in day_keys:
    idx = next((d_idx for d_name, d_idx in day_map.items() if d_name in day), None)
    if idx is None: continue
    if idx <= last_idx:
        weeks.append(current_week)
        current_week = [None] * 7
    current_week[idx] = day
    last_idx = idx
if any(current_week):
    weeks.append(current_week)

# --- 4. THE TWO-ROOM ARCHITECTURE (Tabs) ---
tab_cal, tab_ai = st.tabs(["🗓️ Timeline", "🤖 Co-Pilot"])

# ==========================================
# ROOM 1: THE CALENDAR (Tab 1)
# ==========================================
with tab_cal:
    for week in weeks:
        cols = st.columns(7)
        for i in range(7):
            day_title = week[i]
            with cols[i]:
                if day_title:
                    try:
                        day_name = next(d for d in weekdays if d in day_title)[:2].upper()
                        date_num = re.search(r'\d+', day_title).group()
                        flag = get_country_flag(days_db[day_title] + day_title)
                        button_label = f"{day_name}\n{date_num}\n{flag}"
                    except:
                        button_label = "Day\n?"
                        
                    btn_type = "primary" if day_title == st.session_state.selected_day else "secondary"
                    if st.button(button_label, key=f"btn_{day_title}", type=btn_type, use_container_width=True):
                        st.session_state.selected_day = day_title
                        st.rerun()
                else:
                    st.markdown("<div style='height: 60px;'></div>", unsafe_allow_html=True)

    st.divider()

    # The HUD
    selected = st.session_state.selected_day
    
    st.markdown(f"## 📱 EUROPE 2026")
    st.markdown(f"#### {get_country_flag(days_db[selected] + selected)} {selected}")
    st.markdown(days_db[selected])
    st.divider()

    # The Directories
    st.subheader("📂 Operations Vault")
    for dir_title, dir_content in directories_db.items():
        with st.expander(f"📁 {dir_title}", expanded=False):
            st.markdown(dir_content)

# ==========================================
# ROOM 2: THE AI AGENT (Tab 2)
# ==========================================
with tab_ai:
    st.subheader("🤖 Ask the Trip Director")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a logistics question..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            best_model = next((m for m in valid_models if 'flash' in m), valid_models[0])
            model = genai.GenerativeModel(best_model)
            
            system_prompt = f"Answer using ONLY this document:\n\n{raw_text}\n\nQuestion: {prompt}"
            response = model.generate_content(system_prompt)
            reply = response.text
        except Exception as e:
            reply = f"⚠️ System Error: {e}"

        with st.chat_message("assistant"):
            st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

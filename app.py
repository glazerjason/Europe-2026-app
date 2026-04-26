import streamlit as st
import pandas as pd
import google.generativeai as genai
import re

# --- 1. UI CONFIGURATION & "NAKED" CSS ---
st.set_page_config(page_title="Europe 2026", page_icon="🌍", layout="centered")

custom_css = """
<style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    
    /* 1. Tighten the Grid */
    div[data-testid="stHorizontalBlock"] {
        gap: 0px !important; 
        margin-bottom: 2px;
    }
    div[data-testid="column"] {
        padding: 0px !important; 
    }
    
    /* 2. NAKED BUTTONS: Strip the borders, backgrounds, and shadows */
    div.stButton > button {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #9ca3af; /* Subtle gray for unselected days */
        height: 50px !important;
        width: 100% !important;
        padding: 0px !important;
        font-size: 13px !important;
        font-weight: 600; 
        white-space: pre-wrap !important;
        line-height: 1.1;
        transition: all 0.2s;
    }
    
    /* Hover state */
    div.stButton > button:hover { 
        color: #1c1e21 !important; 
    }
    
    /* 3. HIGHLIGHT STATE: Blue text and a soft, borderless background */
    div.stButton > button[kind="primary"] { 
        color: #007AFF !important; 
        font-weight: 800 !important;
        background-color: #eff6ff !important;
        border-radius: 8px !important;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 2. BULLETPROOF DATA LOADING ---
@st.cache_data
def load_data():
    try:
        with open("itinerary.md", "r", encoding="utf-8") as file:
            return file.read().replace('\r', '') 
    except FileNotFoundError:
        return "Error: Itinerary file not found."

raw_text = load_data()

# --- 3. THE "LINE-BY-LINE" SCANNER ---
weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
days_db = {}
directories_db = {}
current_bucket = None

for line in raw_text.split('\n'):
    clean_line = line.strip()
    is_header = clean_line.startswith('#')
    
    if is_header:
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

if not day_keys:
    st.error("⚠️ No days found. Ensure your dates start with 'Monday', 'Tuesday', etc.")
    st.stop()

if "selected_day" not in st.session_state:
    st.session_state.selected_day = day_keys[0]

# --- 4. TRUE CALENDAR MATRIX GENERATOR ---
# Maps your days to specific columns (Sun=0, Sat=6)
day_map = {"Sunday": 0, "Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5, "Saturday": 6}

weeks = []
current_week = [None] * 7
last_idx = -1

for day in day_keys:
    # Find what day of the week this is
    idx = next((d_idx for d_name, d_idx in day_map.items() if d_name in day), None)
    
    if idx is None: continue
        
    # If the day index is less than or equal to the last one, it means we wrapped to a new week
    if idx <= last_idx:
        weeks.append(current_week)
        current_week = [None] * 7
        
    current_week[idx] = day
    last_idx = idx

if any(current_week):
    weeks.append(current_week)

# --- 5. HELPER FUNCTIONS ---
def get_weather(location_name):
    return "🌤️ 78°F (Avg)" if "Lisbon" in location_name or "Porto" in location_name else "🌦️ 74°F (Avg)"

map_data = {
    "Alfama": pd.DataFrame({'lat': [38.7126], 'lon': [-9.1300]}),
    "Munich": pd.DataFrame({'lat': [48.1351], 'lon': [11.5820]}),
    "San Sebastián": pd.DataFrame({'lat': [43.3183], 'lon': [-1.9812]}),
    "Porto": pd.DataFrame({'lat': [41.1579], 'lon': [-8.6291]})
}

# ==========================================
# UI BUILD OUT STARTS HERE
# ==========================================
st.title("📱 EUROPE 2026")
st.subheader("🗓️ Master Timeline")

# Render the dynamic grid
for week in weeks:
    cols = st.columns(7)
    for i in range(7):
        day_title = week[i]
        with cols[i]:
            if day_title:
                try:
                    day_name = next(d for d in weekdays if d in day_title)[:3].upper()
                    date_num = re.search(r'\d+', day_title).group()
                    button_label = f"{day_name}\n{date_num}"
                except:
                    button_label = "Day\n?"
                    
                btn_type = "primary" if day_title == st.session_state.selected_day else "secondary"
                if st.button(button_label, key=f"btn_{day_title}", type=btn_type, use_container_width=True):
                    st.session_state.selected_day = day_title
                    st.rerun()
            else:
                # Injects an invisible block for non-travel days to keep alignment perfect
                st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)

st.divider()

# --- 6. THE SELECTED DAY HUD ---
selected = st.session_state.selected_day
st.markdown(f"### {selected}")
st.info(f"Forecast: {get_weather(selected)}")

for city, coords in map_data.items():
    if city in selected or city in days_db[selected]:
        st.map(coords, zoom=12, height=150)
        break

st.markdown(days_db[selected])
st.divider()

# --- 7. DIRECTORIES ---
st.subheader("📂 Operations Vault")
for dir_title, dir_content in directories_db.items():
    with st.expander(f"📁 {dir_title}", expanded=False):
        st.markdown(dir_content)
st.divider()

# --- 8. AI AGENT ---
st.subheader("🤖 Agent Co-Pilot")
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

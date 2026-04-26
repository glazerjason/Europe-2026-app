import streamlit as st
import pandas as pd
import google.generativeai as genai
import re

# --- 1. UI CONFIGURATION & CSS ---
st.set_page_config(page_title="Europe 2026", page_icon="🌍", layout="centered")

custom_css = """
<style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    
    /* Force rows to align left and not stretch */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 8px !important;
        margin-bottom: 6px;
        justify-content: flex-start !important; 
    }
    
    /* 🛑 LOCK THE WIDTH: Force every column to be exactly 60px wide */
    div[data-testid="column"] {
        flex: 0 0 60px !important;
        width: 60px !important;
        min-width: 60px !important;
        padding: 0 !important;
    }
    
    /* 🛑 LOCK THE BUTTON: Perfect 60x60 squares */
    div.stButton > button {
        height: 60px !important;
        width: 60px !important;
        border-radius: 12px;
        border: 1px solid #d1d5db;
        padding: 0px !important;
        background-color: #ffffff;
        color: #1c1e21;
        font-size: 13px !important;
        font-weight: 800; /* Extra bold */
        white-space: pre-wrap !important;
        line-height: 1.2;
        transition: all 0.2s;
    }
    
    /* Active & Hover States */
    div.stButton > button:hover { border-color: #007AFF; color: #007AFF; }
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

# --- 3. THE SMART PARSER ---
days_db = {}
directories_db = {}
sections = re.split(r'\n(?=#{1,2} )', '\n' + raw_text)

weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

for section in sections:
    if not section.strip(): continue
    lines = section.strip().split('\n')
    clean_title = re.sub(r'^#{1,2}\s+', '', lines[0]).strip()
    content = '\n'.join(lines[1:]).strip()
    
    if 'DIRECTORY' in clean_title:
        directories_db[clean_title.replace('📚 DIRECTORY:', '').strip()] = content
    elif any(clean_title.startswith(day) for day in weekdays):
        days_db[clean_title] = content

day_keys = list(days_db.keys())
if not day_keys:
    st.error("⚠️ No days found. Ensure your dates start with 'Monday', 'Tuesday', etc.")
    st.stop()

if "selected_day" not in st.session_state:
    st.session_state.selected_day = day_keys[0]

# --- 4. HELPER FUNCTIONS ---
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

# --- 5. THE CALENDAR GRID GENERATOR ---
row1_days = day_keys[0:6]
row2_days = day_keys[6:13]
row3_days = day_keys[13:]

def render_row(days_array):
    if not days_array: return
    cols = st.columns(len(days_array))
    for i, day_title in enumerate(days_array):
        try:
            # Reformat to TUE (top) and 28 (bottom)
            day_name = day_title.split(',')[0][:3].upper() # Extracts 'TUE'
            date_num = re.search(r'\d+', day_title).group() # Extracts '28'
            button_label = f"{day_name}\n{date_num}"
        except:
            button_label = f"Day\n?"
            
        with cols[i]:
            btn_type = "primary" if day_title == st.session_state.selected_day else "secondary"
            if st.button(button_label, key=day_title, type=btn_type, use_container_width=True):
                st.session_state.selected_day = day_title
                st.rerun()

render_row(row1_days)
render_row(row2_days)
render_row(row3_days)

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

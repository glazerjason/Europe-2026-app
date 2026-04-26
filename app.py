import streamlit as st
import pandas as pd
import google.generativeai as genai
import re

# --- 1. UI CONFIGURATION & CUSTOM CSS ---
st.set_page_config(page_title="Europe 2026", page_icon="🌍", layout="centered")

custom_css = """
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Horizontal scroll container for the dates */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
        padding-bottom: 10px;
        gap: 0.4rem;
    }
    
    /* Lock width so the buttons don't crush together */
    div[data-testid="column"] {
        min-width: 80px !important;
        flex: 0 0 auto !important;
    }
    
    /* Style the calendar buttons */
    div.stButton > button {
        height: 65px;
        width: 100%;
        border-radius: 10px;
        border: 1px solid #d1d5db;
        font-weight: 700;
        font-size: 14px;
        white-space: pre-wrap !important; /* Allows the text to stack on two lines */
        line-height: 1.2;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 2. BULLETPROOF DATA LOADING ---
@st.cache_data
def load_data():
    try:
        with open("itinerary.md", "r", encoding="utf-8") as file:
            # Scrub hidden Windows carriage returns that break the parser
            return file.read().replace('\r', '') 
    except FileNotFoundError:
        return "Error: Itinerary file not found."

raw_text = load_data()

# --- 3. THE UNBREAKABLE PARSER ---
days_db = {}
directories_db = {}

# Split the document anytime it sees a new # or ##
sections = re.split(r'\n(?=#{1,2} )', '\n' + raw_text)

for section in sections:
    if not section.strip(): continue
    
    lines = section.strip().split('\n')
    title_line = lines[0]
    content = '\n'.join(lines[1:]).strip()
    
    # Clean the # symbols out of the title
    clean_title = re.sub(r'^#{1,2}\s+', '', title_line)
    
    # Sort into Databases
    if 'DIRECTORY' in clean_title:
        dir_name = clean_title.replace('📚 DIRECTORY:', '').strip()
        directories_db[dir_name] = content
    elif ',' in clean_title and ('–' in clean_title or '-' in clean_title or '—' in clean_title):
        # If it has a comma and a dash, it's a daily agenda!
        days_db[clean_title] = content

# --- 4. HELPER FUNCTIONS ---
def get_weather(location_name):
    averages = {
        "Lisbon": "🌤️ 82°F", "Porto": "🌤️ 78°F", 
        "San Sebastián": "🌦️ 74°F", "Munich": "☀️ 76°F",
        "London": "☁️ 73°F", "Oviedo": "⛅ 70°F"
    }
    for city, temp in averages.items():
        if city in location_name:
            return temp
    return "🌤️ 75°F (Avg)"

map_data = {
    "Alfama": pd.DataFrame({'lat': [38.7126], 'lon': [-9.1300]}),
    "Munich": pd.DataFrame({'lat': [48.1351], 'lon': [11.5820]}),
    "San Sebastián": pd.DataFrame({'lat': [43.3183], 'lon': [-1.9812]}),
    "Porto": pd.DataFrame({'lat': [41.1579], 'lon': [-8.6291]}),
    "London": pd.DataFrame({'lat': [51.5072], 'lon': [-0.1276]})
}

# --- 5. INITIALIZE STATE MEMORY ---
day_keys = list(days_db.keys())

# Fallback in case the document is completely empty or corrupted
if not day_keys:
    st.error("⚠️ Document parsed, but no daily agendas found. Check the formatting in itinerary.md.")
    st.stop()

if "selected_day" not in st.session_state:
    st.session_state.selected_day = day_keys[0]

# ==========================================
# UI BUILD OUT STARTS HERE
# ==========================================
st.title("📱 EUROPE 2026")
st.subheader("🗓️ Master Timeline")

# --- 6. THE HORIZONTAL CALENDAR STRIP ---
cols = st.columns(len(day_keys))

for i, day_title in enumerate(day_keys):
    try:
        # Extract the exact text for the button (e.g., "JUL 28 \n TUE")
        date_part = re.split(r'[-–—]', day_title)[0].strip() 
        day_name, month_date = date_part.split(', ')
        
        day_abbr = day_name[:3].upper()
        month_abbr = month_date.split(' ')[0][:3].upper()
        day_num = month_date.split(' ')[1]
        
        button_label = f"{month_abbr} {day_num}\n{day_abbr}"
    except:
        button_label = f"Day\n{i+1}"
        
    with cols[i]:
        # Logic to turn the selected button solid blue
        is_active = (day_title == st.session_state.selected_day)
        btn_type = "primary" if is_active else "secondary"
        
        if st.button(button_label, key=f"btn_{i}", type=btn_type, use_container_width=True):
            st.session_state.selected_day = day_title
            st.rerun() # Forces the screen to instantly swap content

st.divider()

# --- 7. THE SELECTED DAY HUD (Detail View) ---
selected = st.session_state.selected_day
st.markdown(f"### {selected}")
st.info(f"Forecast: {get_weather(selected)}")

# Map Injection
for city, coords in map_data.items():
    if city in selected or city in days_db[selected]:
        st.map(coords, zoom=12, height=150)
        break

# Day Itinerary
st.markdown(days_db[selected])
st.divider()

# --- 8. THE DIRECTORIES ---
st.subheader("📂 Operations Vault")
for dir_title, dir_content in directories_db.items():
    with st.expander(f"📁 {dir_title}", expanded=False):
        st.markdown(dir_content)
st.divider()

# --- 9. THE AI AGENT ---
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
        
        system_prompt = f"You are the trip logistics director. Answer using ONLY this document:\n\n{raw_text}\n\nQuestion: {prompt}"
        response = model.generate_content(system_prompt)
        reply = response.text
    except Exception as e:
        reply = f"⚠️ System Error: {e}"

    with st.chat_message("assistant"):
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})

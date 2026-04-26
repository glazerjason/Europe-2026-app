import streamlit as st
import requests
import pandas as pd
import google.generativeai as genai

# --- 1. UI CONFIGURATION & CUSTOM CSS ---
st.set_page_config(page_title="Europe 2026", page_icon="🌍", layout="centered")

custom_css = """
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 1. Force the columns into a horizontal, swipeable row on mobile */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch; /* Smooth iOS scrolling */
        padding-bottom: 15px; /* Space for the invisible scrollbar */
        gap: 0.5rem;
    }
    
    /* 2. Lock the width of the calendar boxes so they don't squish */
    div[data-testid="column"] {
        min-width: 85px !important;
        flex: 0 0 auto !important;
    }
    
    /* 3. Style the calendar boxes (Buttons) */
    div.stButton > button {
        height: 70px;
        width: 100%;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        background-color: #ffffff;
        color: #1c1e21;
        font-weight: 700;
        font-size: 14px;
        white-space: pre-wrap !important; /* Forces the newline (\n) to work */
        line-height: 1.3;
        transition: all 0.2s;
    }
    
    /* 4. Active/Hover states for the boxes */
    div.stButton > button:hover, div.stButton > button:active, div.stButton > button:focus {
        border-color: #007AFF;
        color: #007AFF;
        background-color: #f0f8ff;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 2. LOAD DATA ---
@st.cache_data
def load_data():
    try:
        with open("itinerary.md", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "Error: Itinerary file not found."

raw_text = load_data()

# --- 3. HELPER FUNCTIONS ---
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

# --- 4. PARSE THE DOCUMENT INTO A DATABASE ---
sections = raw_text.split('\n# ')
days_db = {}
directories_db = {}

for section in sections:
    if not section.strip(): continue
    
    lines = section.split('\n')
    title = lines[0].strip()
    content = '\n'.join(lines[1:])
    
    if title.startswith('📚 DIRECTORY'):
        directories_db[title.replace('📚 DIRECTORY:', '').strip()] = content
    else:
        days_db[title] = content

# --- 5. INITIALIZE STATE MEMORY ---
day_keys = list(days_db.keys())
if "selected_day" not in st.session_state and len(day_keys) > 0:
    st.session_state.selected_day = day_keys[0] 

# ==========================================
# UI BUILD OUT STARTS HERE
# ==========================================
st.title("📱 EUROPE 2026")

# --- 6. THE CALENDAR GRID (Horizontal Strip) ---
st.subheader("🗓️ Master Timeline")

# Create a dynamic number of columns based on how many days are in the document
cols = st.columns(len(day_keys))

for i, day_title in enumerate(day_keys):
    # Text Processing: Turn "Sunday, August 9 – The Alfama Reset" into "Aug 9 \n SUN"
    try:
        parts = day_title.split(' – ')[0].split(', ')
        day_word = parts[0][:3].upper() # "SUN"
        
        date_parts = parts[1].split(' ')
        month_word = date_parts[0][:3] # "Aug"
        day_num = date_parts[1] # "9"
        
        button_label = f"{month_word} {day_num}\n{day_word}"
    except:
        # Fallback if the formatting in the doc is slightly off
        button_label = f"Day\n{i+1}"
    
    with cols[i]:
        if st.button(button_label, key=f"btn_{i}"):
            st.session_state.selected_day = day_title

st.divider()

# --- 7. THE SELECTED DAY HUD (The Detail View) ---
selected = st.session_state.selected_day
st.markdown(f"### {selected}")
st.info(f"Forecast: {get_weather(selected)}")

# Render Map
for city, coords in map_data.items():
    if city in selected or city in days_db[selected]:
        st.map(coords, zoom=12, height=150)
        break

# Render the Agenda
st.markdown(days_db[selected])

st.divider()

# --- 8. THE DIRECTORIES (Collapsible) ---
st.subheader("📂 Operations Vault")
for dir_title, dir_content in directories_db.items():
    with st.expander(f"📁 {dir_title}", expanded=False):
        st.markdown(dir_content)

st.divider()

# --- 9. THE AI AGENT (Bottom Pinned) ---
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

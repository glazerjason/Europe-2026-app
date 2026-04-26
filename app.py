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
    
    /* Make the calendar buttons look like thick, touch-friendly boxes */
    div.stButton > button {
        height: 60px;
        border-radius: 10px;
        border: 1px solid #d1d5db;
        background-color: #ffffff;
        font-weight: 600;
        color: #1c1e21;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        border-color: #007AFF;
        color: #007AFF;
    }
    div.stButton > button:active {
        background-color: #007AFF;
        color: white;
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
# This allows the app to remember which day box you clicked
day_keys = list(days_db.keys())
if "selected_day" not in st.session_state and len(day_keys) > 0:
    st.session_state.selected_day = day_keys[0] # Default to the first day

# ==========================================
# UI BUILD OUT STARTS HERE
# ==========================================
st.title("📱 EUROPE 2026")

# --- 6. THE CALENDAR GRID ---
st.subheader("🗓️ Master Timeline")

# Create a 3-column grid for the calendar boxes
cols = st.columns(3)
for i, day_title in enumerate(day_keys):
    # Extract just the "Sun, Aug 9" part for the tiny buttons to keep it clean
    short_date = day_title.split(' – ')[0].replace('day', '') 
    
    with cols[i % 3]:
        # If a button is clicked, update the session memory
        if st.button(short_date, key=f"btn_{i}", use_container_width=True):
            st.session_state.selected_day = day_title

st.divider()

# --- 7. THE SELECTED DAY HUD (The Detail View) ---
selected = st.session_state.selected_day
st.markdown(f"### {selected}")
st.info(f"Forecast: {get_weather(selected)}")

# Render Map if coordinates exist
for city, coords in map_data.items():
    if city in selected or city in days_db[selected]:
        st.map(coords, zoom=12, height=150)
        break

# Render the Markdown text for that day
st.markdown(days_db[selected])

st.divider()

# --- 8. THE DIRECTORIES (Still Collapsed) ---
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


import streamlit as st
import pandas as pd
import google.generativeai as genai
import re

# --- 1. UI CONFIGURATION & CSS ---
st.set_page_config(page_title="Europe 2026", page_icon="🌍", layout="centered")

custom_css = """
<style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    
    /* 1. Force columns to stay horizontal on mobile (no stacking) */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        margin-bottom: 5px;
    }
    
    /* 2. Tighten the gap between the columns to make them touch closely */
    div[data-testid="column"] {
        padding: 0px 3px !important; 
    }
    
    /* 3. Style the square buttons */
    div.stButton > button {
        height: 60px !important;
        width: 100% !important;
        border-radius: 8px;
        border: 1px solid #d1d5db;
        padding: 0px !important;
        background-color: #ffffff;
        color: #1c1e21;
        font-size: 13px !important;
        font-weight: 800; 
        white-space: pre-wrap !important;
        line-height: 1.2;
        transition: all 0.2s;
    }
    
    /* 4. Highlight State */
    div.stButton > button:hover, div.stButton > button:active, div.stButton > button:focus { 
        border-color: #007AFF !important; 
        color: #007AFF !important; 
        background-color: #f0f8ff !important;
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

# --- 3. THE "LINE-BY-LINE" SCANNER (Guarantees no lost text) ---
weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
days_db = {}
directories_db = {}
current_bucket = None

# Read the document one single line at a time
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

    # If it's not a header, drop the text into whatever bucket is currently open
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

# --- 5. THE CALENDAR GRID GENERATOR (The Ghost Column Fix) ---
# Break the trip into 7-day rows
rows = [day_keys[x:x+7] for x in range(0, len(day_keys), 7)]

def render_row(days_array):
    if not days_array: return
    # ALWAYS generate exactly 7 columns so Streamlit never stretches them
    cols = st.columns(7) 
    
    for i in range(7):
        with cols[i]:
            if i < len(days_array):
                day_title = days_array[i]
                try:
                    # Safely extract TUE and 28
                    day_name = next(d for d in weekdays if d in day_title)[:3].upper()
                    date_num = re.search(r'\d+', day_title).group()
                    button_label = f"{day_name}\n{date_num}"
                except:
                    button_label = f"Day\n{i+1}"
                
                # Button Logic
                btn_type = "primary" if day_title == st.session_state.selected_day else "secondary"
                if st.button(button_label, key=f"btn_{day_title}", type=btn_type, use_container_width=True):
                    st.session_state.selected_day = day_title
                    st.rerun()
            else:
                # If there is no day for this column, inject an invisible ghost block
                st.empty()

# Render all generated rows
for row in rows:
    render_row(row)

st.divider()

# --- 6. THE SELECTED DAY HUD ---
selected = st.session_state.selected_day
st.markdown(f"### {selected}")
st.info(f"Forecast: {get_weather(selected)}")

for city, coords in map_data.items():
    if city in selected or city in days_db[selected]:
        st.map(coords, zoom=12, height=150)
        break

# Safely output the captured text
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

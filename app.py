import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import re
import os

# --- 1. UI CONFIGURATION & SCOPED CSS ---
st.set_page_config(page_title="Europe 2026", page_icon="🌍", layout="wide")

custom_css = """
<style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    
    /* 1. ABSOLUTE CENTERING: Mobile viewport layout */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 600px !important; /* Phone-sized container on desktop */
        margin: 0 auto !important;   /* Dead-center alignment */
    }
    
    /* 2. TOP MODE TOGGLE BUTTONS (Horizontal Tab Style) */
    div[data-testid="stKey-mode_toggle_container"] div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        gap: 8px !important;
        margin-bottom: 10px !important;
    }
    
    div[data-testid="stKey-mode_toggle_container"] div.stButton > button,
    div[data-testid="nav_timeline"] > button,
    div[data-testid="nav_brixby"] > button,
    div[class*="st-key-nav_"] > button {
        height: 44px !important;
        width: 100% !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        border-radius: 12px !important;
        white-space: nowrap !important;
        padding: 8px 16px !important;
        box-shadow: none !important;
    }
    
    div[data-testid="stKey-mode_toggle_container"] div.stButton > button:hover,
    div[class*="st-key-nav_"] > button:hover {
        border-color: #007AFF !important;
        color: #007AFF !important;
    }

    /* 3. CALENDAR MATRIX (Rigid 7-column grid) */
    div[data-testid="stKey-calendar_matrix"] div[data-testid="stHorizontalBlock"],
    div.st-key-calendar_matrix div[data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: repeat(7, 1fr) !important;
        gap: 4px !important;
        margin-bottom: 4px !important;
    }
    
    /* Calendar Matrix Buttons Outer Container */
    div[data-testid="stKey-calendar_matrix"] div.stButton > button,
    div.st-key-calendar_matrix div.stButton > button,
    div[data-testid*="btn_"] > button,
    div[class*="st-key-btn_"] > button {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #9ca3af !important; 
        height: 42px !important; 
        width: 100% !important;
        padding: 2px 2px !important;
        font-size: 11px !important; 
        font-weight: 600 !important; 
        line-height: 1.2 !important;
    }
    
    /* Target inner <p> tag inside Streamlit 1.30+ button markdown wrapper */
    div[data-testid="stKey-calendar_matrix"] button p,
    div.st-key-calendar_matrix button p,
    div[class*="st-key-btn_"] button p {
        white-space: nowrap !important;
        display: inline-flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 2px !important;
        margin: 0 !important;
    }
    
    div[data-testid="stKey-calendar_matrix"] div.stButton > button:hover,
    div[data-testid*="btn_"] > button:hover { 
        color: #1c1e21 !important; 
    }
    
    /* Active Calendar Day Button */
    div[data-testid="stKey-calendar_matrix"] div.stButton > button[kind="primary"],
    div[data-testid*="btn_"] > button[kind="primary"] { 
        color: #007AFF !important; 
        font-weight: 800 !important;
        background-color: #eff6ff !important;
        border-radius: 8px !important;
    }
</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

# --- 2. DATA LOADING & FLAG SCANNER ---
# --- 2. DATA LOADING & FLAG SCANNER ---
def load_data():
    try:
        with open("itinerary.md", "r", encoding="utf-8") as file:
            return file.read().replace('\r', '')

raw_text = load_data()

def get_country_flag(text_content):
    if any(city in text_content for city in ["Lisbon", "Porto", "Sintra", "Alfama", "Portugal"]):
        return "🇵🇹"
    elif any(city in text_content for city in ["San Sebastián", "Oviedo", "Spain", "Basque", "Getaria", "Zumaia"]):
        return "🇪🇸"
    elif any(city in text_content for city in ["Munich", "Germany", "Bavaria", "Füssen"]):
        return "🇩🇪"
    elif any(city in text_content for city in ["Salzburg", "Vienna", "Austria", "Hallstatt", "Fuschlsee"]):
        return "🇦🇹"
    elif any(city in text_content for city in ["London", "UK", "England"]):
        return "🇬🇧"
    return "🌍"

# --- 3. THE ITINERARY PARSER ---
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

# --- INITIALIZE SESSION STATE ---
if "selected_day" not in st.session_state:
    st.session_state.selected_day = day_keys[0] if day_keys else None

if "app_mode" not in st.session_state or st.session_state.app_mode not in ["Timeline", "Brixby"]:
    st.session_state.app_mode = "Timeline"

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

# --- 4. BRIXBY AI RESPONSE GENERATOR WITH GOOGLE SEARCH & CONTEXT ANCHOR ---
def get_brixby_response(prompt, messages_history, raw_itinerary):
    # 1. Safely retrieve the API Key
    api_key = None
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        pass
        
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        return "⚠️ Brixby Notice: API key not found. Please set `GEMINI_API_KEY` in Streamlit secrets or as an environment variable."
    
    try:
        # 2. Initialize the new SDK client
        client = genai.Client(api_key=api_key)
        
        system_instruction = (
            "You are Brixby, an expert AI travel assistant for Europe 2026.\n"
            "Your objective is to assist with trip logistics, itinerary details, travel recommendations, weather, transit, and local knowledge.\n\n"
            "CONTEXT ANCHOR (MASTER ITINERARY & OPERATIONS VAULT):\n"
            "------------------------------------\n"
            f"{raw_itinerary}\n"
            "------------------------------------\n\n"
            "GUIDELINES:\n"
            "1. Treat the Master Itinerary above as your primary source of truth and foundational context anchor.\n"
            "2. Actively perform Google Search grounding to retrieve real-time web information (e.g., weather forecasts, live transit schedules, venue hours, flight statuses, or local suggestions) to enrich your answers.\n"
            "3. Be friendly, conversational, concise, and highly practical for on-the-go travel."
        )

        # 3. Format the chat history for the new SDK
        formatted_history = []
        for msg in messages_history:
            role = "user" if msg["role"] == "user" else "model"
            formatted_history.append({"role": role, "parts": [{"text": msg["content"]}]})

        # 4. Configure Google Search Tool
        search_tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[search_tool],
            temperature=0.7
        )

        # 5. Call the correct model
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=formatted_history,
            config=config
        )
        
        return response.text

    except Exception as e:
        return f"⚠️ Brixby Notice: Unable to generate a response at this time. Exception Details: {str(e)}"

# --- UI LAYOUT ---
with st.container(key="mode_toggle_container"):
    toggle_cols = st.columns(2)
    with toggle_cols[0]:
        if st.button("🗓️ Timeline", key="nav_timeline", use_container_width=True, type="primary" if st.session_state.app_mode == "Timeline" else "secondary"):
            st.session_state.app_mode = "Timeline"
            st.rerun()
    with toggle_cols[1]:
        if st.button("🤖 Brixby", key="nav_brixby", use_container_width=True, type="primary" if st.session_state.app_mode == "Brixby" else "secondary"):
            st.session_state.app_mode = "Brixby"
            st.rerun()

st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

if st.session_state.app_mode == "Timeline":
    selected = st.session_state.selected_day
    st.markdown("## 📱 EUROPE 2026")
    if selected and selected in days_db:
        st.markdown(f"#### {get_country_flag(days_db[selected] + selected)} {selected}")
    
    with st.container(key="calendar_matrix"):
        for week in weeks:
            cols = st.columns(7)
            for i in range(7):
                day_title = week[i]
                with cols[i]:
                    if day_title:
                        try:
                            day_name = next(d for d in weekdays if d in day_title)[:2].upper()
                            date_num = re.search(r'\d+', day_title).group()
                            flag = get_country_flag(days_db.get(day_title, "") + day_title)
                            button_label = f"{day_name} {date_num} {flag}"
                        except Exception:
                            button_label = "Day ?"
                            
                        btn_type = "primary" if day_title == st.session_state.selected_day else "secondary"
                        if st.button(button_label, key=f"btn_{day_title}", type=btn_type, use_container_width=True):
                            st.session_state.selected_day = day_title
                            st.rerun()
                    else:
                        st.markdown("<div style='height: 42px;'></div>", unsafe_allow_html=True)

    st.divider()

    if selected and selected in days_db:
        st.markdown(days_db[selected])
    st.divider()

    st.subheader("📚 Operations Vault")
    for dir_title, dir_content in directories_db.items():
        with st.expander(f"📁 {dir_title}", expanded=False):
            st.markdown(dir_content)

elif st.session_state.app_mode == "Brixby":
    st.markdown("## 🤖 Brixby")
    st.caption("AI travel assistant anchored to your itinerary with live web search.")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask Brixby about logistics, weather, transit, or recommendations..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            with st.spinner("Brixby is searching and analyzing..."):
                reply = get_brixby_response(prompt, st.session_state.messages, raw_text)
            st.markdown(reply)
            
        st.session_state.messages.append({"role": "assistant", "content": reply})

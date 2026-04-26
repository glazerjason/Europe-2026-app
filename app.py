import streamlit as st
import requests
import pandas as pd
import google.generativeai as genai
import datetime

# --- 1. UI CONFIGURATION & CUSTOM CSS ---
st.set_page_config(page_title="Europe 2026 Co-Pilot", page_icon="🌍", layout="centered")

custom_css = """
<style>
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Native App Styling for Expanders */
    .streamlit-expanderHeader {
        background-color: #f7f9fa;
        border-radius: 10px;
        font-weight: 600;
        font-size: 16px;
        color: #1c1e21;
        border: none !important;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
    }
    div[data-testid="stExpander"] {
        border: none !important;
        margin-bottom: 10px;
    }
    
    /* Button Styling */
    div.stButton > button:first-child {
        background-color: #007AFF;
        color: white;
        border-radius: 12px;
        border: none;
        font-weight: bold;
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

# --- 3. DYNAMIC WEATHER LOGIC ---
def get_weather(location_name):
    # If trip is far away, return historical averages.
    # When trip is < 14 days away, this function can be upgraded to hit the Open-Meteo API.
    averages = {
        "Lisbon": "🌤️ 82°F (Historical Avg)",
        "Porto": "🌤️ 78°F (Historical Avg)",
        "San Sebastián": "🌦️ 74°F (Historical Avg)",
        "Munich": "☀️ 76°F (Historical Avg)"
    }
    for city, temp in averages.items():
        if city in location_name:
            return temp
    return "🌤️ 75°F (Historical Avg)"

# --- 4. MAP COORDINATE DATABASE ---
# Streamlit st.map requires latitude/longitude points
map_data = {
    "Alfama": pd.DataFrame({'lat': [38.7126], 'lon': [-9.1300]}),
    "Munich": pd.DataFrame({'lat': [48.1351], 'lon': [11.5820]}),
    "San Sebastián": pd.DataFrame({'lat': [43.3183], 'lon': [-1.9812]}),
    "Porto": pd.DataFrame({'lat': [41.1579], 'lon': [-8.6291]})
}

# --- 5. THE HEADER ---
st.title("📱 EUROPE 2026")

# --- 6. THE AI AGENT (GEMINI INTEGRATION) ---
st.subheader("🤖 Agent Co-Pilot")
if "messages" not in st.session_state:
    st.session_state.messages = []

# Show past chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input
if prompt := st.chat_input("Ask about the itinerary, GF food, or logistics..."):
    # Show user message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Call the LLM
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # We inject your actual markdown document into the system prompt!
        system_prompt = f"You are the trip logistics director. Answer the user's question using ONLY this document:\n\n{raw_text}\n\nQuestion: {prompt}"
        
        response = model.generate_content(system_prompt)
        reply = response.text
    except Exception as e:
        reply = "⚠️ I need my API key setup in Streamlit Secrets to answer that!"

    # Show AI reply
    with st.chat_message("assistant"):
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})

st.divider()

# --- 7. THE DASHBOARD BUILDER ---
sections = raw_text.split('\n# ')

for section in sections:
    if not section.strip():
        continue
    
    # DIRECTORIES (Always Collapsed)
    if section.startswith('📚 DIRECTORY'):
        title = section.split('\n')[0].replace('📚 DIRECTORY:', '').strip()
        content = '\n'.join(section.split('\n')[1:])
        with st.expander(f"📁 {title}", expanded=False):
            st.markdown(content)
            
    # DAILY AGENDAS (Logic for dynamic features)
    else:
        lines = section.split('\n')
        title = lines[0]
        content = '\n'.join(lines[1:])
        
        # Mock logic to expand "Sunday, August 9" by default
        is_today = "Sunday, August 9" in title 
        
        with st.expander(f"▼ {title}" if is_today else f"▶ {title}", expanded=is_today):
            # 1. Inject Weather
            st.info(f"Weather Forecast: {get_weather(title)}")
            
            # 2. Inject The Text
            st.markdown(content)
            
            # 3. Inject The Map (If we have coordinates for the city)
            for city, coords in map_data.items():
                if city in title or city in content:
                    st.caption(f"📍 GPS Pin: {city}")
                    st.map(coords, zoom=12, height=150)
                    break # Only show one map per day

st.divider()
st.button("📤 UPLOAD TO MEDIA VAULT", use_container_width=True)

import streamlit as st

# 1. UI Configuration (Mobile-First)
st.set_page_config(page_title="Europe 2026 Co-Pilot", page_icon="🌍", layout="centered")

# Hide the default Streamlit menu for a cleaner "app" look
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# 2. Top Widgets (Weather & Agent Placeholder)
st.title("📱 EUROPE 2026")
st.info("🌤️ **Today's Weather:** 78°F | Sunny in Alfama") # Placeholder for live API later
st.text_input("🤖 Agent Co-Pilot", placeholder="Ask a question about the trip...")

st.divider()

# 3. Read the Data
# In V1, we read the adjacent markdown file. 
try:
    with open("itinerary.md", "r", encoding="utf-8") as file:
        raw_text = file.read()
except FileNotFoundError:
    st.error("Master itinerary file not found.")
    st.stop()

# 4. The Parser Logic (Turning text into UI)
# We split the document into major sections based on the Markdown headers
sections = raw_text.split('\n# ')

for section in sections:
    if not section.strip():
        continue
    
    # If it's a Directory, make it a collapsed group
    if section.startswith('# 📚 DIRECTORY'):
        title = section.split('\n')[0].replace('# ', '')
        content = '\n'.join(section.split('\n')[1:])
        with st.expander(f"▶ {title}", expanded=False):
            st.markdown(content)
            
    # If it's a Daily Agenda, make it an expander (Keep the first day open)
    else:
        lines = section.split('\n')
        title = lines[0]
        content = '\n'.join(lines[1:])
        
        # Expand only if it's the current day (Hardcoded to Sunday for this example)
        is_today = "Sunday, August 9" in title 
        
        with st.expander(f"▼ {title}" if is_today else f"▶ {title}", expanded=is_today):
            st.markdown(content)

st.divider()
st.button("📤 UPLOAD B-ROLL TO MEDIA VAULT", use_container_width=True)

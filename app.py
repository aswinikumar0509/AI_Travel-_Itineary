import re
import streamlit as st
from src.core.planner import TravelPlanner
from dotenv import load_dotenv

st.set_page_config(page_title="AI Travel Planner")

# --- CSS: force long words/links to wrap inside the box ---
st.markdown("""
<style>
/* Make paragraphs and list items wrap long links/words */
p, li, a { overflow-wrap: anywhere; word-break: break-word; }
/* Optional: avoid horizontal scroll from code blocks if any */
code, pre { white-space: pre-wrap; word-break: break-word; }
</style>
""", unsafe_allow_html=True)

st.title("AI Travel Itinerary Planner")
st.write("Plan your day trip itinerary by entering your city and interests.")

load_dotenv()

def shorten_bare_urls(md: str) -> str:
    """
    Replace bare (https://...) in parentheses with readable Markdown links
    e.g., '(https://maps.google.com/very-long...)' -> '([Open in Maps](https://...))'
    """
    return re.sub(r'\((https?://[^\s)]+)\)', r'([Open in Maps](\1))', md)

with st.form("planner_form"):
    city = st.text_input("Enter the city name for your trip")
    interests = st.text_input("Enter your interests (comma-separated)")
    submitted = st.form_submit_button("Generate itinerary")

    if submitted:
        if city and interests:
            planner = TravelPlanner()
            planner.set_city(city)
            planner.set_interests(interests)
            itinerary = planner.create_itineary()

            # Make links short & readable, then render
            itinerary = shorten_bare_urls(itinerary)

            st.subheader("📄 Your Itinerary")
            st.markdown(itinerary, unsafe_allow_html=True)
        else:
            st.warning("Please fill City and Interests to move forward")

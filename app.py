# app.py (Streamlit)
import streamlit as st
from dotenv import load_dotenv
from src.core.planner import TravelPlanner

st.set_page_config(page_title="AI Travel Planner")

# Keep long links from overflowing
st.markdown("""
<style>
p, li, a { overflow-wrap:anywhere; word-break:break-word; }
code, pre { white-space:pre-wrap; word-break:break-word; }
</style>
""", unsafe_allow_html=True)

st.title("AI Travel Itinerary Planner")
st.write("Pick a city, choose one or more interests, set trip length, and generate!")

load_dotenv()

DEFAULT_INTERESTS = [
    "food", "history", "culture", "museums", "architecture",
    "shopping", "nightlife", "nature", "photography", "markets",
]

with st.form("planner_form"):
    city = st.text_input("City")
    chosen = st.multiselect("Select your interests", DEFAULT_INTERESTS, default=["food", "history"])
    extra = st.text_input("Add extra interests (comma-separated)", placeholder="street food, temples")
    days = st.number_input("Number of days", min_value=1, max_value=30, value=2, step=1)

    submitted = st.form_submit_button("Generate itinerary")

    if submitted:
        # merge multiselect + extra free-text
        extras = [i.strip() for i in extra.split(",") if i.strip()]
        interests = chosen + extras

        if city and interests:
            planner = TravelPlanner()
            planner.set_city(city)
            planner.set_interests(interests)   # list works fine
            itinerary_md = planner.create_itinerary(days=days)

            st.subheader("📄 Your Itinerary")
            st.markdown(itinerary_md, unsafe_allow_html=True)
        else:
            st.warning("Please enter a City and at least one Interest.")

# src/chains/itinery_chain.py
from typing import List, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from src.config.config import groq_api_key


# Initialize the model
llm = ChatGroq(
    groq_api_key=groq_api_key,
    model_name="llama-3.3-70b-versatile",
    temperature=0.3
)


# --- Improved itinerary prompt ---
itinerary_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a helpful travel assistant.

You are creating **Day {day_index}** of a **{total_days}-day trip** in **{city}**.

Traveler interests: {interests}.
Previously used places (do NOT repeat): {exclude_pois}.

Generate a **detailed Markdown itinerary** with these sections:
- Morning
- Lunch
- Afternoon
- Dinner
- Evening

Guidelines:
- Make **each day unique** — do not repeat any POI or restaurant names from earlier days.
- Keep each bullet **brief (1–2 lines)**, focus on fun, interest-specific activities,.
- For each stop, include a short Google Maps link using Markdown like `[Open in Maps](https://...)`.
- Tailor activities to match the traveler’s interests.
- Avoid long URLs; shorten display text to `[Open in Maps]`.
- Return results in **Markdown**, formatted for Streamlit display.

At the end, list all POIs mentioned today inside a code block:

```pois
- <poi name 1>
- <poi name 2>
- ...
```"""
    ),
    ("human", "Create the itinerary for Day {day_index}.")
])


def generate_itinerary(
    city: str,
    interests: List[str],
    day_index: int = 1,
    total_days: int = 1,
    exclude_pois: Optional[List[str]] = None
) -> str:
    """
    Generates a single day's itinerary for a given city and interests.
    Use exclude_pois to prevent repeating previously suggested locations.
    """
    exclude_pois = exclude_pois or ["None"]

    response = llm.invoke(
        itinerary_prompt.format_messages(
            city=city,
            interests=", ".join(interests),
            day_index=day_index,
            total_days=total_days,
            exclude_pois=", ".join(exclude_pois),
        )
    )

    content = response.content.strip()
    map_url = f"https://www.google.com/maps/place/{city.replace(' ', '+')}"

    return f"{content}\n\n📍 [Map of {city}]({map_url})"


# ✅ Backward compatibility alias so old imports still work
generate_itineary = generate_itinerary

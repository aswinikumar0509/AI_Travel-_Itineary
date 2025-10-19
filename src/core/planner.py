# src/core/planner.py
from typing import List, Union
from collections.abc import Sequence
import re

from langchain_core.messages import HumanMessage, AIMessage
from src.chains.itinery_chain import generate_itineary  # your itinerary generator
from src.utils.logger import get_logger
from src.utils.custom_exception import CustomException

logger = get_logger(__name__)

# Regex to shorten Google Maps links in Markdown
_LINK_PAREN_RE = re.compile(r'\((https?://[^\s)]+)\)')

def _shorten_bare_urls(md: str) -> str:
    """Replace raw URLs with '[Open in Maps](url)' links."""
    return _LINK_PAREN_RE.sub(r'([Open in Maps](\1))', md)


def _normalize_interests(interests: Union[str, Sequence[str]]) -> List[str]:
    """
    Accepts either:
      - a list/tuple of strings (recommended)
      - a single comma-separated string
    Returns a cleaned, lowercase, de-duplicated list of interests.
    """
    try:
        if interests is None:
            raise ValueError("interests must not be None")

        # Handle string input like "food, culture, hiking"
        if isinstance(interests, (str, bytes)):
            raw_items = [s.strip() for s in str(interests).split(",")]

        # Handle list / tuple / set input
        elif isinstance(interests, Sequence):
            raw_items = []
            for i in interests:
                if i is None:
                    continue
                s = str(i).strip()
                if s:
                    raw_items.append(s)

        else:
            raise TypeError(
                f"interests must be a list/tuple/set of strings or a comma-separated string, got {type(interests).__name__}"
            )

        # Lowercase, dedupe while preserving order
        seen = set()
        cleaned: List[str] = []
        for s in raw_items:
            t = s.lower()
            if t and t not in seen:
                seen.add(t)
                cleaned.append(t)

        if not cleaned:
            raise ValueError("Provide at least one non-empty interest")

        return cleaned

    except Exception as e:
        logger.exception("Error while normalizing interests")
        raise


class TravelPlanner:
    def __init__(self):
        self.messages: List[HumanMessage | AIMessage] = []
        self.city: str = ""
        self.interests: List[str] = []
        self.days: int = 1
        self.itinerary: str = ""
        logger.info("Initialized TravelPlanner instance")

    def set_city(self, city: str):
        try:
            self.city = (city or "").strip()
            self.messages.append(HumanMessage(content=f"City: {self.city}"))
            logger.info("City set successfully")
        except Exception as e:
            logger.exception("Error while setting city")
            raise CustomException("Failed to set city") from e

    def set_interests(self, interests: Union[str, Sequence[str]]):
        try:
            logger.info("set_interests received type=%s value=%r", type(interests).__name__, interests)
            self.interests = _normalize_interests(interests)
            self.messages.append(
                HumanMessage(content=f"Interests: {', '.join(self.interests)}")
            )
            logger.info("Interests set successfully: %s", self.interests)
        except Exception as e:
            logger.exception("Error while setting interests")
            raise CustomException("Failed to set interests") from e

    def set_days(self, days: int):
        try:
            self.days = max(1, int(days))
            self.messages.append(
                HumanMessage(content=f"Trip length: {self.days} day(s)")
            )
            logger.info("Days set successfully")
        except Exception as e:
            logger.exception("Error while setting days")
            raise CustomException("Failed to set days") from e

    def _call_chain_for_day(self, day_idx: int, focus: str) -> str:
        """
        Ask the chain for one day, emphasizing a specific interest (focus),
        while still mixing the others.
        """
        try:
            try:
                # Preferred signature if chain supports it
                return generate_itineary(
                    self.city,
                    self.interests,
                    days=1,
                    day_index=day_idx,
                    primary_interest=focus,
                )
            except TypeError:
                # Fallback for simpler chains
                steer = (
                    f"Create a detailed itinerary for **Day {day_idx}** in {self.city}.\n"
                    f"Primary focus: **{focus}**. Also weave in: "
                    f"{', '.join([i for i in self.interests if i != focus])}.\n"
                    "Include breakfast/lunch/dinner and activity blocks with short Google Maps links."
                )
                self.messages.append(HumanMessage(content=steer))
                raw = generate_itineary(self.city, self.interests)
                return f"### Day {day_idx} — Focus: {focus}\n\n{raw}"

        except Exception as e:
            logger.exception(f"Error generating itinerary for Day {day_idx}")
            raise CustomException(f"Failed to generate day {day_idx}") from e

    def create_itinerary(self, days: int | None = None) -> str:
        try:
            if days is not None:
                self.set_days(days)

            if not self.interests:
                self.interests = ["food"]  # default

            logger.info(
                f"Generating itinerary | city={self.city} | interests={self.interests} | days={self.days}"
            )

            if self.days == 1:
                try:
                    md = generate_itineary(self.city, self.interests, days=1)
                except TypeError:
                    md = generate_itineary(self.city, self.interests)
                final_md = _shorten_bare_urls(md)
            else:
                sections = []
                for d in range(1, self.days + 1):
                    focus = self.interests[(d - 1) % len(self.interests)]
                    md = self._call_chain_for_day(d, focus)
                    sections.append(_shorten_bare_urls(md))

                header = f"# {self.city} — {self.days}-Day Itinerary\n"
                intro = (
                    f"_Tailored to interests: {', '.join(self.interests)}._\n\n"
                    "Times & venues are suggestions—verify hours and availability."
                )
                final_md = header + intro + "\n\n" + "\n\n---\n\n".join(sections)

            self.itinerary = final_md
            self.messages.append(AIMessage(content=final_md))
            logger.info("Itinerary generated successfully")
            return final_md

        except Exception as e:
            logger.exception("Error while creating itinerary")
            raise CustomException("Failed to create itinerary") from e

# src/core/planner.py
from typing import List, Union
from collections.abc import Sequence
import re

from langchain_core.messages import HumanMessage, AIMessage
from src.chains.itinery_chain import generate_itinerary  # ✅ updated import
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
            raise CustomException("Failed to set city", e)

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
            raise CustomException("Failed to set interests", e)

    def set_days(self, days: int):
        try:
            self.days = max(1, int(days))
            self.messages.append(HumanMessage(content=f"Trip length: {self.days} day(s)"))
            logger.info("Days set successfully")
        except Exception as e:
            logger.exception("Error while setting days")
            raise CustomException("Failed to set days", e)

    def _call_chain_for_day(self, day_idx: int, exclude_pois: List[str]) -> str:
        """Generate one day's plan using the itinerary chain."""
        try:
            logger.info(f"Generating itinerary for Day {day_idx}")
            return generate_itinerary(
                city=self.city,
                interests=self.interests,
                day_index=day_idx,
                total_days=self.days,
                exclude_pois=exclude_pois,
            )
        except Exception as e:
            logger.exception(f"Error generating itinerary for Day {day_idx}")
            raise CustomException(f"Failed to generate day {day_idx}", e)

    def create_itinerary(self, days: int | None = None) -> str:
        try:
            if days is not None:
                self.set_days(days)

            if not self.city:
                raise CustomException("City not set", Exception("Missing city"))
            if not self.interests:
                self.interests = ["food"]

            logger.info(
                f"Generating itinerary | city={self.city} | interests={self.interests} | days={self.days}"
            )

            # Track used POIs to avoid duplicates
            all_pois: List[str] = []
            sections: List[str] = []

            for d in range(1, self.days + 1):
                md = self._call_chain_for_day(d, all_pois)
                sections.append(_shorten_bare_urls(md))

                # Extract POIs from fenced block
                import re
                m = re.search(r"```pois\s*(.*?)\s*```", md, flags=re.S)
                if m:
                    todays = [x.strip("- ").strip() for x in m.group(1).splitlines() if x.strip()]
                    all_pois.extend(todays)

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
            raise CustomException("Failed to create itinerary", e)

# src/core/planner.py
from typing import List, Sequence, Union
import re

from langchain_core.messages import HumanMessage, AIMessage
from src.chains.itinery_chain import generate_itineary  # keep your chain
from src.utils.logger import get_logger
from src.utils.custom_exception import CustomException

logger = get_logger(__name__)
_LINK_PAREN_RE = re.compile(r'\((https?://[^\s)]+)\)')

def _shorten_bare_urls(md: str) -> str:
    return _LINK_PAREN_RE.sub(r'([Open in Maps](\1))', md)

def _normalize_interests(interests: Union[str, Sequence[str]]) -> List[str]:
    if isinstance(interests, str):
        items = [i.strip() for i in interests.split(",")]
    else:
        items = [str(i).strip() for i in interests]
    return [i for i in items if i]

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
            self.city = city.strip()
            self.messages.append(HumanMessage(content=f"City: {self.city}"))
            logger.info("City set successfully")
        except Exception as e:
            logger.error(f"Error while setting city: {e}")
            raise CustomException("Failed to set city", e)

    def set_interests(self, interests: Union[str, Sequence[str]]):
        try:
            self.interests = _normalize_interests(interests)
            self.messages.append(HumanMessage(content=f"Interests: {', '.join(self.interests)}"))
            logger.info("Interests set successfully")
        except Exception as e:
            logger.error(f"Error while setting interests: {e}")
            raise CustomException("Failed to set interests", e)

    def set_days(self, days: int):
        try:
            self.days = max(1, int(days))
            self.messages.append(HumanMessage(content=f"Trip length: {self.days} day(s)"))
            logger.info("Days set successfully")
        except Exception as e:
            logger.error(f"Error while setting days: {e}")
            raise CustomException("Failed to set days", e)

    def _call_chain_for_day(self, day_idx: int, focus: str) -> str:
        """
        Ask the chain for one day, emphasizing a specific interest (focus),
        while still mixing the others.
        """
        try:
            # Try richer signature if your chain supports it
            try:
                return generate_itineary(
                    self.city,
                    self.interests,
                    days=1,
                    day_index=day_idx,
                    primary_interest=focus
                )
            except TypeError:
                # Fallback prompt steering
                steer = (
                    f"Create a detailed itinerary for **Day {day_idx}** in {self.city}.\n"
                    f"Primary focus: **{focus}**. Also weave in: {', '.join([i for i in self.interests if i != focus])}.\n"
                    "Include breakfast/lunch/dinner and activity blocks with short Google Maps links."
                )
                self.messages.append(HumanMessage(content=steer))
                raw = generate_itineary(self.city, self.interests)
                return f"### Day {day_idx} — Focus: {focus}\n\n{raw}"
        except Exception as e:
            logger.error(f"Error generating Day {day_idx}: {e}")
            raise

    def create_itinerary(self, days: int | None = None) -> str:
        try:
            if days is not None:
                self.set_days(days)

            if not self.interests:
                self.interests = ["food"]  # sane default

            logger.info(f"Generating itinerary | city={self.city} | interests={self.interests} | days={self.days}")

            # Round-robin focus so each day spotlights a different interest
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
            logger.error(f"Error while creating itinerary: {e}")
            raise CustomException("Failed to create itinerary", e)

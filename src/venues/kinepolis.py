"""
Scraper voor Kinepolis Hoofddorp - bioscoop.
"""

import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

from .base import Venue, VenueType, Evenement, VenueScraper


class KinepolisScraper(VenueScraper):
    """Scraper voor Kinepolis bioscoop in Hoofddorp."""

    VENUE = Venue(
        naam="Kinepolis Hoofddorp",
        adres="Polaplein 450",
        plaats="Hoofddorp",
        website="https://kinepolis.nl",
        venue_type=VenueType.BIOSCOOP,
    )

    AGENDA_URL = "https://kinepolis.nl/bioscopen/kinepolis-hoofddorp"

    def __init__(self):
        super().__init__(self.VENUE)

    def scrape(self) -> list[Evenement]:
        """Scrape de Kinepolis Hoofddorp agenda."""
        evenementen = []

        html = self._maak_request(self.AGENDA_URL)
        if not html:
            return evenementen

        soup = BeautifulSoup(html, "lxml")

        # Zoek naar film items
        film_items = soup.select(
            ".movie-item, .film-card, .movie, "
            "[data-film], article, .schedule-item"
        )

        for item in film_items:
            evenement = self._parse_film(item)
            if evenement:
                evenementen.append(evenement)

        return evenementen

    def _parse_film(self, item) -> Optional[Evenement]:
        """Parse een film item."""
        try:
            # Titel
            titel_elem = item.select_one("h2, h3, h4, .title, .movie-title")
            if not titel_elem:
                return None
            titel = titel_elem.get_text(strip=True)

            if len(titel) < 2:
                return None

            # URL
            link = item.select_one("a[href]")
            url = link["href"] if link else self.AGENDA_URL
            if url and not url.startswith("http"):
                url = f"{self.VENUE.website}{url}"

            # Datum
            datum = datetime.now().replace(hour=20, minute=0, second=0, microsecond=0)

            # Probeer specifieke tijd te vinden
            tijd_elem = item.select_one(".time, .showtime, time, .session-time")
            if tijd_elem:
                tijd_str = tijd_elem.get_text(strip=True)
                tijd_match = re.search(r"(\d{1,2}):(\d{2})", tijd_str)
                if tijd_match:
                    datum = datum.replace(
                        hour=int(tijd_match.group(1)),
                        minute=int(tijd_match.group(2))
                    )

            # Genre
            genre_elem = item.select_one(".genre, .category, .film-genre")
            genre = genre_elem.get_text(strip=True) if genre_elem else "film"

            return Evenement(
                titel=titel,
                venue=self.venue,
                datum=datum,
                url=url,
                genre=genre,
            )

        except Exception:
            return None

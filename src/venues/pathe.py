"""
Scraper voor Pathé Haarlem - bioscoop.
"""

import re
from datetime import datetime, timedelta
from typing import Optional

from bs4 import BeautifulSoup

from .base import Venue, VenueType, Evenement, VenueScraper


class PatheScraper(VenueScraper):
    """Scraper voor Pathé bioscoop in Haarlem."""

    VENUE = Venue(
        naam="Pathé Haarlem",
        adres="Schalkwijkerstraat 9",
        plaats="Haarlem",
        website="https://www.pathe.nl",
        venue_type=VenueType.BIOSCOOP,
    )

    # Pathé API endpoint voor films
    THEATER_ID = "haarlem"
    API_URL = f"https://www.pathe.nl/bioscoop/{THEATER_ID}"

    def __init__(self):
        super().__init__(self.VENUE)

    def scrape(self) -> list[Evenement]:
        """Scrape de Pathé Haarlem agenda."""
        evenementen = []

        html = self._maak_request(self.API_URL)
        if not html:
            return evenementen

        soup = BeautifulSoup(html, "lxml")

        # Zoek naar film items
        film_items = soup.select(
            ".movie-card, .schedule-movie, .film-item, "
            "[data-movie], article.movie"
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
            titel_elem = item.select_one("h2, h3, .movie-title, .title, [data-title]")
            if not titel_elem:
                return None
            titel = titel_elem.get("data-title") or titel_elem.get_text(strip=True)

            if len(titel) < 2:
                return None

            # URL
            link = item.select_one("a[href]")
            url = link["href"] if link else self.API_URL
            if url and not url.startswith("http"):
                url = f"{self.VENUE.website}{url}"

            # Datum - films draaien doorgaans meerdere dagen
            # We gebruiken vandaag als startdatum
            datum = datetime.now().replace(hour=20, minute=0, second=0, microsecond=0)

            # Probeer specifieke tijd te vinden
            tijd_elem = item.select_one(".time, .showtime, time")
            if tijd_elem:
                tijd_str = tijd_elem.get_text(strip=True)
                tijd_match = re.search(r"(\d{1,2}):(\d{2})", tijd_str)
                if tijd_match:
                    datum = datum.replace(
                        hour=int(tijd_match.group(1)),
                        minute=int(tijd_match.group(2))
                    )

            # Genre
            genre_elem = item.select_one(".genre, .movie-genre, .category")
            genre = genre_elem.get_text(strip=True) if genre_elem else "film"

            # Regisseur als "artiest"
            regisseur_elem = item.select_one(".director, .regisseur")
            artiesten = []
            if regisseur_elem:
                artiesten = [regisseur_elem.get_text(strip=True)]

            return Evenement(
                titel=titel,
                venue=self.venue,
                datum=datum,
                url=url,
                genre=genre,
                artiesten=artiesten,
            )

        except Exception:
            return None

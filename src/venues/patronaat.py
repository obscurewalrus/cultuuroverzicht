"""
Scraper voor Patronaat Haarlem - concertzaal.
"""

import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

from .base import Venue, VenueType, Evenement, VenueScraper


class PatronaatScraper(VenueScraper):
    """Scraper voor Patronaat concertpodium in Haarlem."""

    VENUE = Venue(
        naam="Patronaat",
        adres="Zijlsingel 2",
        plaats="Haarlem",
        website="https://www.patronaat.nl",
        venue_type=VenueType.CONCERTZAAL,
    )

    AGENDA_URL = "https://www.patronaat.nl/agenda/"

    def __init__(self):
        super().__init__(self.VENUE)

    def scrape(self) -> list[Evenement]:
        """Scrape de Patronaat agenda."""
        evenementen = []

        html = self._maak_request(self.AGENDA_URL)
        if not html:
            return evenementen

        soup = BeautifulSoup(html, "lxml")

        # Patronaat gebruikt event cards in hun agenda
        event_cards = soup.select(".event-card, .agenda-item, article.event")

        for card in event_cards:
            evenement = self._parse_event_card(card)
            if evenement:
                evenementen.append(evenement)

        return evenementen

    def _parse_event_card(self, card) -> Optional[Evenement]:
        """Parse een event card naar een Evenement."""
        try:
            # Titel
            titel_elem = card.select_one("h2, h3, .event-title, .title")
            if not titel_elem:
                return None
            titel = titel_elem.get_text(strip=True)

            # URL
            link = card.select_one("a[href]")
            url = link["href"] if link else self.AGENDA_URL
            if not url.startswith("http"):
                url = f"{self.VENUE.website}{url}"

            # Datum
            datum_elem = card.select_one(".date, .event-date, time")
            datum = None
            if datum_elem:
                datum_str = datum_elem.get("datetime") or datum_elem.get_text(strip=True)
                datum = self._parse_datum(datum_str)

            if not datum:
                # Probeer datum uit de tekst te halen
                tekst = card.get_text()
                datum_match = re.search(
                    r"(\d{1,2})\s*(jan|feb|mrt|apr|mei|jun|jul|aug|sep|okt|nov|dec)[a-z]*\s*(\d{4})?",
                    tekst,
                    re.IGNORECASE,
                )
                if datum_match:
                    dag = datum_match.group(1)
                    maand = datum_match.group(2).lower()[:3]
                    jaar = datum_match.group(3) or str(datetime.now().year)
                    maand_map = {
                        "jan": 1, "feb": 2, "mrt": 3, "apr": 4,
                        "mei": 5, "jun": 6, "jul": 7, "aug": 8,
                        "sep": 9, "okt": 10, "nov": 11, "dec": 12,
                    }
                    try:
                        datum = datetime(int(jaar), maand_map.get(maand, 1), int(dag))
                    except ValueError:
                        datum = datetime.now()

            if not datum:
                datum = datetime.now()

            # Genre
            genre_elem = card.select_one(".genre, .category, .tag")
            genre = genre_elem.get_text(strip=True) if genre_elem else ""

            # Uitverkocht status
            uitverkocht = bool(card.select_one(".sold-out, .uitverkocht"))
            tekst_lower = card.get_text().lower()
            if "uitverkocht" in tekst_lower or "sold out" in tekst_lower:
                uitverkocht = True

            # Artiesten (vaak gelijk aan titel bij concerten)
            artiesten = [titel] if titel else []

            return Evenement(
                titel=titel,
                venue=self.venue,
                datum=datum,
                url=url,
                artiesten=artiesten,
                genre=genre,
                uitverkocht=uitverkocht,
            )

        except Exception:
            return None

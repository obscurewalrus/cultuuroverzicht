"""
Scraper voor Philharmonie Haarlem - klassieke muziek.
"""

import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

from .base import Venue, VenueType, Evenement, VenueScraper


class PhilharmonieScraper(VenueScraper):
    """Scraper voor Philharmonie Haarlem (klassieke muziek)."""

    VENUE = Venue(
        naam="Philharmonie Haarlem",
        adres="Lange Begijnestraat 11",
        plaats="Haarlem",
        website="https://www.philharmoniehaarlem.nl",
        venue_type=VenueType.CONCERTZAAL,
    )

    AGENDA_URL = "https://www.philharmoniehaarlem.nl/agenda/"

    def __init__(self):
        super().__init__(self.VENUE)

    def scrape(self) -> list[Evenement]:
        """Scrape de Philharmonie agenda."""
        evenementen = []

        html = self._maak_request(self.AGENDA_URL)
        if not html:
            return evenementen

        soup = BeautifulSoup(html, "lxml")

        # Zoek naar concert items
        items = soup.select(".concert-item, .event-item, .agenda-item, article")

        for item in items:
            evenement = self._parse_item(item)
            if evenement:
                evenementen.append(evenement)

        return evenementen

    def _parse_item(self, item) -> Optional[Evenement]:
        """Parse een agenda item."""
        try:
            # Titel
            titel_elem = item.select_one("h2, h3, .title, .concert-title")
            if not titel_elem:
                return None
            titel = titel_elem.get_text(strip=True)

            # Skip non-event items
            if len(titel) < 3:
                return None

            # URL
            link = item.select_one("a[href]")
            url = link["href"] if link else self.AGENDA_URL
            if not url.startswith("http"):
                url = f"{self.VENUE.website}{url}"

            # Datum
            datum = self._extract_datum(item)
            if not datum:
                return None

            # Beschrijving
            beschr_elem = item.select_one(".description, .excerpt, p")
            beschrijving = beschr_elem.get_text(strip=True) if beschr_elem else ""

            # Artiesten (vaak in subtitel of beschrijving)
            artiesten = self._extract_artiesten(item, titel)

            return Evenement(
                titel=titel,
                venue=self.venue,
                datum=datum,
                url=url,
                beschrijving=beschrijving,
                artiesten=artiesten,
                genre="klassiek",
            )

        except Exception:
            return None

    def _extract_datum(self, item) -> Optional[datetime]:
        """Extraheer datum uit een item."""
        datum_elem = item.select_one(".date, time, .datum")
        if datum_elem:
            datum_str = datum_elem.get("datetime") or datum_elem.get_text(strip=True)
            datum = self._parse_datum(datum_str)
            if datum:
                return datum

        # Fallback: zoek in tekst
        tekst = item.get_text()
        maand_map = {
            "januari": 1, "februari": 2, "maart": 3, "april": 4,
            "mei": 5, "juni": 6, "juli": 7, "augustus": 8,
            "september": 9, "oktober": 10, "november": 11, "december": 12,
        }

        for maand_naam, maand_num in maand_map.items():
            pattern = rf"(\d{{1,2}})\s+{maand_naam}\s*(\d{{4}})?"
            match = re.search(pattern, tekst, re.IGNORECASE)
            if match:
                dag = int(match.group(1))
                jaar = int(match.group(2)) if match.group(2) else datetime.now().year
                try:
                    return datetime(jaar, maand_num, dag, 20, 0)  # Default 20:00
                except ValueError:
                    continue

        return None

    def _extract_artiesten(self, item, titel: str) -> list[str]:
        """Extraheer artiesten uit een item."""
        artiesten = []

        # Check voor artiest element
        artiest_elem = item.select_one(".artist, .performer, .uitvoerenden")
        if artiest_elem:
            tekst = artiest_elem.get_text(strip=True)
            # Split op komma of 'en'
            for deel in re.split(r",|(?:\s+en\s+)", tekst):
                deel = deel.strip()
                if deel and len(deel) > 2:
                    artiesten.append(deel)

        # Fallback: gebruik titel
        if not artiesten:
            artiesten = [titel]

        return artiesten

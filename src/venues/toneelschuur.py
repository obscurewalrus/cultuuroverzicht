"""
Scraper voor De Schuur Haarlem - theater en film.
(Voorheen Toneelschuur, hernoemd in 2021)
"""

import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

from .base import Venue, VenueType, Evenement, VenueScraper


class ToneelschuurScraper(VenueScraper):
    """Scraper voor De Schuur Haarlem (theater en film)."""

    VENUE = Venue(
        naam="De Schuur",
        adres="Lange Begijnestraat 9",
        plaats="Haarlem",
        website="https://www.schuur.nl",
        venue_type=VenueType.THEATER,
    )

    # De Schuur combineert theater en film op één agenda
    AGENDA_URL = "https://www.schuur.nl/agenda/"
    THEATER_URL = "https://www.schuur.nl/agenda/"
    FILM_URL = "https://www.schuur.nl/agenda/"

    def __init__(self, include_film: bool = True):
        super().__init__(self.VENUE)
        self.include_film = include_film

    def scrape(self) -> list[Evenement]:
        """Scrape de Toneelschuur theater en film agenda."""
        evenementen = []

        # Theater agenda
        theater_events = self._scrape_agenda(self.THEATER_URL, "theater")
        evenementen.extend(theater_events)

        # Film agenda (Filmschuur)
        if self.include_film:
            film_events = self._scrape_agenda(self.FILM_URL, "film")
            evenementen.extend(film_events)

        return evenementen

    def _scrape_agenda(self, url: str, categorie: str) -> list[Evenement]:
        """Scrape een specifieke agenda pagina."""
        evenementen = []

        html = self._maak_request(url)
        if not html:
            return evenementen

        soup = BeautifulSoup(html, "lxml")

        # Zoek naar event items
        items = soup.select(
            ".show, .film, .event, .agenda-item, article, .program-item"
        )

        for item in items:
            evenement = self._parse_item(item, categorie)
            if evenement:
                evenementen.append(evenement)

        return evenementen

    def _parse_item(self, item, categorie: str) -> Optional[Evenement]:
        """Parse een agenda item."""
        try:
            # Titel
            titel_elem = item.select_one("h2, h3, h4, .title, .show-title, .film-title")
            if not titel_elem:
                return None
            titel = titel_elem.get_text(strip=True)

            if len(titel) < 2:
                return None

            # URL
            link = item.select_one("a[href]")
            url = link["href"] if link else self.THEATER_URL
            if not url.startswith("http"):
                url = f"{self.VENUE.website}{url}"

            # Datum
            datum = self._extract_datum(item)
            if not datum:
                return None

            # Beschrijving
            beschr_elem = item.select_one(".description, .excerpt, .intro, p")
            beschrijving = beschr_elem.get_text(strip=True) if beschr_elem else ""

            # Artiesten/makers
            artiesten = self._extract_makers(item, titel)

            return Evenement(
                titel=titel,
                venue=self.venue,
                datum=datum,
                url=url,
                beschrijving=beschrijving,
                artiesten=artiesten,
                genre=categorie,
            )

        except Exception:
            return None

    def _extract_datum(self, item) -> Optional[datetime]:
        """Extraheer datum uit een item."""
        # Probeer time element
        datum_elem = item.select_one("time, .date, .datum, .time")
        if datum_elem:
            datum_str = datum_elem.get("datetime") or datum_elem.get_text(strip=True)
            datum = self._parse_datum(datum_str)
            if datum:
                return datum

        # Fallback: zoek in tekst
        tekst = item.get_text()

        # Nederlandse maanden
        maanden = {
            "jan": 1, "feb": 2, "mrt": 3, "maart": 3, "apr": 4,
            "mei": 5, "jun": 6, "jul": 7, "aug": 8,
            "sep": 9, "okt": 10, "nov": 11, "dec": 12,
        }

        for maand_naam, maand_num in maanden.items():
            pattern = rf"(\d{{1,2}})\s*{maand_naam}[a-z]*\.?\s*(\d{{4}})?"
            match = re.search(pattern, tekst, re.IGNORECASE)
            if match:
                dag = int(match.group(1))
                jaar = int(match.group(2)) if match.group(2) else datetime.now().year
                try:
                    return datetime(jaar, maand_num, dag, 20, 30)
                except ValueError:
                    continue

        return None

    def _extract_makers(self, item, titel: str) -> list[str]:
        """Extraheer makers/artiesten uit een item."""
        makers = []

        # Check voor maker/regisseur element
        for selector in [".maker", ".director", ".regisseur", ".cast", ".by"]:
            elem = item.select_one(selector)
            if elem:
                tekst = elem.get_text(strip=True)
                # Verwijder labels
                tekst = re.sub(r"^(door|regie|van|met)[:\s]*", "", tekst, flags=re.I)
                for deel in re.split(r",|&|(?:\s+en\s+)", tekst):
                    deel = deel.strip()
                    if deel and len(deel) > 2:
                        makers.append(deel)

        if not makers:
            makers = [titel]

        return makers

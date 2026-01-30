"""
Scraper voor De Meerse Hoofddorp - theater en cultuurhuis.
"""

import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

from .base import Venue, VenueType, Evenement, VenueScraper


class DeMeerseScraper(VenueScraper):
    """Scraper voor De Meerse in Hoofddorp (theater/cultuurhuis)."""

    VENUE = Venue(
        naam="De Meerse",
        adres="Raadhuisplein 1",
        plaats="Hoofddorp",
        website="https://www.demeerse.nl",
        venue_type=VenueType.THEATER,
    )

    AGENDA_URL = "https://www.demeerse.nl/agenda/"

    def __init__(self):
        super().__init__(self.VENUE)

    def scrape(self) -> list[Evenement]:
        """Scrape de De Meerse agenda."""
        evenementen = []

        html = self._maak_request(self.AGENDA_URL)
        if not html:
            return evenementen

        soup = BeautifulSoup(html, "lxml")

        # Zoek naar event items
        items = soup.select(
            ".event, .agenda-item, .show, article, .voorstelling, .program-item"
        )

        for item in items:
            evenement = self._parse_item(item)
            if evenement:
                evenementen.append(evenement)

        return evenementen

    def _parse_item(self, item) -> Optional[Evenement]:
        """Parse een agenda item."""
        try:
            # Titel
            titel_elem = item.select_one("h2, h3, h4, .title, .event-title")
            if not titel_elem:
                return None
            titel = titel_elem.get_text(strip=True)

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

            # Genre
            genre_elem = item.select_one(".genre, .category, .type, .tag")
            genre = genre_elem.get_text(strip=True) if genre_elem else ""

            # Beschrijving
            beschr_elem = item.select_one(".description, .excerpt, .intro, p")
            beschrijving = beschr_elem.get_text(strip=True) if beschr_elem else ""

            # Prijs
            prijs_elem = item.select_one(".price, .prijs")
            prijs = prijs_elem.get_text(strip=True) if prijs_elem else None

            # Uitverkocht
            uitverkocht = "uitverkocht" in item.get_text().lower()

            return Evenement(
                titel=titel,
                venue=self.venue,
                datum=datum,
                url=url,
                beschrijving=beschrijving,
                genre=genre,
                prijs=prijs,
                uitverkocht=uitverkocht,
            )

        except Exception:
            return None

    def _extract_datum(self, item) -> Optional[datetime]:
        """Extraheer datum uit een item."""
        # Probeer time element
        datum_elem = item.select_one("time, .date, .datum")
        if datum_elem:
            datum_str = datum_elem.get("datetime") or datum_elem.get_text(strip=True)
            datum = self._parse_datum(datum_str)
            if datum:
                return datum

        # Fallback: zoek in tekst
        tekst = item.get_text()

        # Probeer diverse formaten
        # "za 15 feb", "15 februari 2026", etc.
        maanden = {
            "jan": 1, "januari": 1,
            "feb": 2, "februari": 2,
            "mrt": 3, "maart": 3,
            "apr": 4, "april": 4,
            "mei": 5,
            "jun": 6, "juni": 6,
            "jul": 7, "juli": 7,
            "aug": 8, "augustus": 8,
            "sep": 9, "september": 9,
            "okt": 10, "oktober": 10,
            "nov": 11, "november": 11,
            "dec": 12, "december": 12,
        }

        pattern = r"(\d{1,2})\s*([a-z]+)\.?\s*(\d{4})?"
        match = re.search(pattern, tekst, re.IGNORECASE)
        if match:
            dag = int(match.group(1))
            maand_str = match.group(2).lower()
            jaar = int(match.group(3)) if match.group(3) else datetime.now().year

            maand = maanden.get(maand_str)
            if maand:
                try:
                    return datetime(jaar, maand, dag, 20, 0)
                except ValueError:
                    pass

        return None

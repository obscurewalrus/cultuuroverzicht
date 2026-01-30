"""
Scrapers voor boekhandels in Haarlem - lezingen en signeersessies.
"""

import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

from .base import Venue, VenueType, Evenement, VenueScraper


class AthenaeumscraPer(VenueScraper):
    """Scraper voor Athenaeum Boekhandel Haarlem."""

    VENUE = Venue(
        naam="Athenaeum Haarlem",
        adres="Gedempte Oude Gracht 70",
        plaats="Haarlem",
        website="https://www.athenaeum.nl",
        venue_type=VenueType.BOEKHANDEL,
    )

    AGENDA_URL = "https://www.athenaeum.nl/agenda"

    def __init__(self):
        super().__init__(self.VENUE)

    def scrape(self) -> list[Evenement]:
        """Scrape Athenaeum agenda."""
        evenementen = []

        html = self._maak_request(self.AGENDA_URL)
        if not html:
            return evenementen

        soup = BeautifulSoup(html, "lxml")

        # Zoek naar event items
        items = soup.select(
            ".event, .agenda-item, article, .event-item, "
            ".activity, .lezing"
        )

        for item in items:
            evenement = self._parse_event(item)
            if evenement:
                # Filter op Haarlem locatie
                if self._is_haarlem_event(item):
                    evenementen.append(evenement)

        return evenementen

    def _is_haarlem_event(self, item) -> bool:
        """Check of event in Haarlem plaatsvindt."""
        tekst = item.get_text().lower()
        return "haarlem" in tekst or "athenaeum haarlem" in tekst

    def _parse_event(self, item) -> Optional[Evenement]:
        """Parse een event."""
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
            if url and not url.startswith("http"):
                url = f"{self.VENUE.website}{url}"

            # Datum
            datum = self._extract_datum(item)
            if not datum:
                return None

            # Beschrijving
            beschr_elem = item.select_one(".description, .excerpt, p, .intro")
            beschrijving = beschr_elem.get_text(strip=True) if beschr_elem else ""

            # Auteur (vaak in titel of beschrijving)
            artiesten = self._extract_auteur(titel, beschrijving)

            return Evenement(
                titel=titel,
                venue=self.venue,
                datum=datum,
                url=url,
                beschrijving=beschrijving,
                artiesten=artiesten,
                genre="literatuur",
            )

        except Exception:
            return None

    def _extract_datum(self, item) -> Optional[datetime]:
        """Extraheer datum uit item."""
        datum_elem = item.select_one("time, .date, .datum, .event-date")
        if datum_elem:
            datum_str = datum_elem.get("datetime") or datum_elem.get_text(strip=True)
            datum = self._parse_datum(datum_str)
            if datum:
                return datum

        # Fallback: zoek in tekst
        tekst = item.get_text()
        return self._parse_nl_datum(tekst)

    def _parse_nl_datum(self, tekst: str) -> Optional[datetime]:
        """Parse Nederlandse datum uit tekst."""
        maanden = {
            "jan": 1, "feb": 2, "mrt": 3, "maart": 3, "apr": 4,
            "mei": 5, "jun": 6, "jul": 7, "aug": 8,
            "sep": 9, "okt": 10, "nov": 11, "dec": 12,
        }

        pattern = r"(\d{1,2})\s*([a-z]+)\.?\s*(\d{4})?"
        match = re.search(pattern, tekst, re.IGNORECASE)
        if match:
            dag = int(match.group(1))
            maand_str = match.group(2).lower()[:3]
            jaar = int(match.group(3)) if match.group(3) else datetime.now().year
            maand = maanden.get(maand_str)
            if maand:
                try:
                    return datetime(jaar, maand, dag, 20, 0)
                except ValueError:
                    pass
        return None

    def _extract_auteur(self, titel: str, beschrijving: str) -> list[str]:
        """Probeer auteursnaam te extraheren."""
        tekst = f"{titel} {beschrijving}"
        auteurs = []

        # Patronen voor auteurs
        patronen = [
            r"(?:lezing|gesprek|avond)\s+(?:met|door)\s+([A-Z][a-zéèêëïîôûù]+(?:\s+[A-Z][a-zéèêëïîôûù]+)+)",
            r"([A-Z][a-zéèêëïîôûù]+(?:\s+[A-Z][a-zéèêëïîôûù]+)+)\s+(?:over|presenteert|signeert)",
            r"(?:auteur|schrijver)\s+([A-Z][a-zéèêëïîôûù]+(?:\s+[A-Z][a-zéèêëïîôûù]+)+)",
        ]

        for patroon in patronen:
            matches = re.findall(patroon, tekst)
            for match in matches:
                if len(match) > 3:
                    auteurs.append(match)

        return auteurs


class VrijeDenkerScraper(VenueScraper):
    """Scraper voor De Vrije Denker boekhandel Haarlem."""

    VENUE = Venue(
        naam="De Vrije Denker",
        adres="Zijlstraat 93",
        plaats="Haarlem",
        website="https://www.vrijdenker.nl",
        venue_type=VenueType.BOEKHANDEL,
    )

    AGENDA_URL = "https://www.vrijdenker.nl/agenda/"

    def __init__(self):
        super().__init__(self.VENUE)

    def scrape(self) -> list[Evenement]:
        """Scrape De Vrije Denker agenda."""
        evenementen = []

        html = self._maak_request(self.AGENDA_URL)
        if not html:
            return evenementen

        soup = BeautifulSoup(html, "lxml")

        items = soup.select(
            ".event, .agenda-item, article, .event-item, "
            ".tribe-events-event, .activiteit"
        )

        for item in items:
            evenement = self._parse_event(item)
            if evenement:
                evenementen.append(evenement)

        return evenementen

    def _parse_event(self, item) -> Optional[Evenement]:
        """Parse een event."""
        try:
            # Titel
            titel_elem = item.select_one("h2, h3, h4, .title, .tribe-events-title")
            if not titel_elem:
                return None
            titel = titel_elem.get_text(strip=True)

            if len(titel) < 3:
                return None

            # URL
            link = item.select_one("a[href]")
            url = link["href"] if link else self.AGENDA_URL
            if url and not url.startswith("http"):
                url = f"{self.VENUE.website}{url}"

            # Datum
            datum = self._extract_datum(item)
            if not datum:
                return None

            # Beschrijving
            beschr_elem = item.select_one(".description, .excerpt, p")
            beschrijving = beschr_elem.get_text(strip=True) if beschr_elem else ""

            return Evenement(
                titel=titel,
                venue=self.venue,
                datum=datum,
                url=url,
                beschrijving=beschrijving,
                genre="literatuur",
            )

        except Exception:
            return None

    def _extract_datum(self, item) -> Optional[datetime]:
        """Extraheer datum uit item."""
        datum_elem = item.select_one("time, .date, .tribe-events-start-date")
        if datum_elem:
            datum_str = datum_elem.get("datetime") or datum_elem.get_text(strip=True)
            datum = self._parse_datum(datum_str)
            if datum:
                return datum
        return None

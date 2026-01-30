"""
Scraper voor Frans Hals Museum - kunst en exposities.
"""

import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

from .base import Venue, VenueType, Evenement, VenueScraper


class FransHalsMuseumScraper(VenueScraper):
    """Scraper voor Frans Hals Museum in Haarlem."""

    VENUE = Venue(
        naam="Frans Hals Museum",
        adres="Groot Heiligland 62",
        plaats="Haarlem",
        website="https://www.franshalsmuseum.nl",
        venue_type=VenueType.MUSEUM,
    )

    AGENDA_URL = "https://www.franshalsmuseum.nl/nl/te-zien-te-doen/"
    EXPOSITIES_URL = "https://www.franshalsmuseum.nl/nl/tentoonstellingen/"

    def __init__(self):
        super().__init__(self.VENUE)

    def scrape(self) -> list[Evenement]:
        """Scrape Frans Hals Museum tentoonstellingen en events."""
        evenementen = []

        # Tentoonstellingen
        exposities = self._scrape_exposities()
        evenementen.extend(exposities)

        # Activiteiten/events
        events = self._scrape_events()
        evenementen.extend(events)

        return evenementen

    def _scrape_exposities(self) -> list[Evenement]:
        """Scrape tentoonstellingen."""
        evenementen = []

        html = self._maak_request(self.EXPOSITIES_URL)
        if not html:
            return evenementen

        soup = BeautifulSoup(html, "lxml")

        items = soup.select(
            ".exhibition, .tentoonstelling, article, "
            ".exhibition-item, .expo-card"
        )

        for item in items:
            evenement = self._parse_expositie(item)
            if evenement:
                evenementen.append(evenement)

        return evenementen

    def _scrape_events(self) -> list[Evenement]:
        """Scrape events en activiteiten."""
        evenementen = []

        html = self._maak_request(self.AGENDA_URL)
        if not html:
            return evenementen

        soup = BeautifulSoup(html, "lxml")

        items = soup.select(
            ".event, .activity, .agenda-item, article, "
            ".event-card, .activiteit"
        )

        for item in items:
            evenement = self._parse_event(item)
            if evenement:
                evenementen.append(evenement)

        return evenementen

    def _parse_expositie(self, item) -> Optional[Evenement]:
        """Parse een tentoonstelling."""
        try:
            # Titel
            titel_elem = item.select_one("h2, h3, .title, .exhibition-title")
            if not titel_elem:
                return None
            titel = titel_elem.get_text(strip=True)

            if len(titel) < 3:
                return None

            # URL
            link = item.select_one("a[href]")
            url = link["href"] if link else self.EXPOSITIES_URL
            if url and not url.startswith("http"):
                url = f"{self.VENUE.website}{url}"

            # Datum bereik
            datum, einddatum = self._extract_datumbereik(item)

            # Beschrijving
            beschr_elem = item.select_one(".description, .excerpt, p, .intro")
            beschrijving = beschr_elem.get_text(strip=True) if beschr_elem else ""

            # Kunstenaars
            kunstenaar_elem = item.select_one(".artist, .kunstenaar, .maker")
            artiesten = []
            if kunstenaar_elem:
                artiesten = [kunstenaar_elem.get_text(strip=True)]

            return Evenement(
                titel=titel,
                venue=self.venue,
                datum=datum,
                einddatum=einddatum,
                url=url,
                beschrijving=beschrijving,
                artiesten=artiesten,
                genre="kunst",
            )

        except Exception:
            return None

    def _parse_event(self, item) -> Optional[Evenement]:
        """Parse een event/activiteit."""
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
            beschr_elem = item.select_one(".description, .excerpt, p")
            beschrijving = beschr_elem.get_text(strip=True) if beschr_elem else ""

            return Evenement(
                titel=titel,
                venue=self.venue,
                datum=datum,
                url=url,
                beschrijving=beschrijving,
                genre="kunst",
            )

        except Exception:
            return None

    def _extract_datum(self, item) -> Optional[datetime]:
        """Extraheer datum uit een item."""
        datum_elem = item.select_one("time, .date, .datum")
        if datum_elem:
            datum_str = datum_elem.get("datetime") or datum_elem.get_text(strip=True)
            datum = self._parse_datum(datum_str)
            if datum:
                return datum

        # Fallback: zoek in tekst
        tekst = item.get_text()
        return self._parse_nl_datum(tekst)

    def _extract_datumbereik(self, item) -> tuple[datetime, Optional[datetime]]:
        """Extraheer start en einddatum voor tentoonstellingen."""
        tekst = item.get_text()

        # Zoek naar "t/m" of "-" patroon
        bereik_match = re.search(
            r"(\d{1,2})\s*(\w+)\s*(\d{4})?\s*(?:t/m|[-–])\s*(\d{1,2})\s*(\w+)\s*(\d{4})?",
            tekst,
            re.IGNORECASE
        )

        if bereik_match:
            start_dag = int(bereik_match.group(1))
            start_maand = self._maand_naar_nummer(bereik_match.group(2))
            start_jaar = int(bereik_match.group(3)) if bereik_match.group(3) else datetime.now().year

            eind_dag = int(bereik_match.group(4))
            eind_maand = self._maand_naar_nummer(bereik_match.group(5))
            eind_jaar = int(bereik_match.group(6)) if bereik_match.group(6) else start_jaar

            try:
                start = datetime(start_jaar, start_maand, start_dag, 10, 0)
                eind = datetime(eind_jaar, eind_maand, eind_dag, 17, 0)
                return start, eind
            except ValueError:
                pass

        # Fallback: gebruik vandaag
        return datetime.now(), None

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
                    return datetime(jaar, maand, dag, 10, 0)
                except ValueError:
                    pass
        return None

    def _maand_naar_nummer(self, maand_str: str) -> int:
        """Converteer maandnaam naar nummer."""
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
        return maanden.get(maand_str.lower(), 1)

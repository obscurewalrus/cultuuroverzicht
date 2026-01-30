"""
Basis classes voor venue scrapers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class VenueType(Enum):
    CONCERTZAAL = "concertzaal"
    THEATER = "theater"
    BIOSCOOP = "bioscoop"
    MUSEUM = "museum"
    BOEKHANDEL = "boekhandel"


@dataclass
class Venue:
    """Een locatie waar evenementen plaatsvinden."""

    naam: str
    adres: str
    plaats: str
    website: str
    venue_type: VenueType

    def __str__(self) -> str:
        return f"{self.naam} ({self.plaats})"


@dataclass
class Evenement:
    """Een evenement in een venue."""

    titel: str
    venue: Venue
    datum: datetime
    url: str

    # Optionele velden
    einddatum: Optional[datetime] = None
    beschrijving: str = ""
    artiesten: list[str] = field(default_factory=list)
    genre: str = ""
    prijs: Optional[str] = None
    uitverkocht: bool = False

    def __str__(self) -> str:
        datum_str = self.datum.strftime("%d-%m-%Y %H:%M")
        status = " [UITVERKOCHT]" if self.uitverkocht else ""
        return f"{self.titel} @ {self.venue.naam} - {datum_str}{status}"

    @property
    def zoektermen(self) -> list[str]:
        """Genereer zoektermen voor matching met NRC tips."""
        termen = [self.titel.lower()]
        termen.extend(a.lower() for a in self.artiesten)
        if self.genre:
            termen.append(self.genre.lower())
        return termen


class VenueScraper(ABC):
    """Abstracte basis class voor venue scrapers."""

    def __init__(self, venue: Venue):
        self.venue = venue
        self._evenementen: list[Evenement] = []

    @abstractmethod
    def scrape(self) -> list[Evenement]:
        """Haal evenementen op van de venue website."""
        pass

    @property
    def evenementen(self) -> list[Evenement]:
        """Geef gecachede evenementen terug."""
        if not self._evenementen:
            self._evenementen = self.scrape()
        return self._evenementen

    def ververs(self) -> list[Evenement]:
        """Ververs de evenementen cache."""
        self._evenementen = self.scrape()
        return self._evenementen

    def _maak_request(self, url: str, timeout: int = 15, verify_ssl: bool = True) -> Optional[str]:
        """Maak een HTTP request met foutafhandeling."""
        import requests
        import urllib3

        # Onderdruk SSL warnings als we SSL verificatie uitschakelen
        if not verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=timeout,
                verify=verify_ssl,
                allow_redirects=True,
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.SSLError:
            # Probeer opnieuw zonder SSL verificatie
            if verify_ssl:
                return self._maak_request(url, timeout, verify_ssl=False)
            print(f"SSL fout bij ophalen {url}")
            return None
        except requests.RequestException as e:
            print(f"Fout bij ophalen {url}: {e}")
            return None

    def _parse_datum(self, datum_str: str) -> Optional[datetime]:
        """Parse diverse datumformaten naar datetime."""
        from dateutil import parser as date_parser

        try:
            return date_parser.parse(datum_str, dayfirst=True)
        except (ValueError, TypeError):
            return None

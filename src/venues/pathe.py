"""
Scraper voor Pathé Haarlem - bioscoop.
"""

import json
import re
from datetime import datetime
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

    THEATER_ID = "haarlem"
    AGENDA_URL = f"https://www.pathe.nl/bioscoop/{THEATER_ID}"

    def __init__(self):
        super().__init__(self.VENUE)

    def scrape(self) -> list[Evenement]:
        """Scrape de Pathé Haarlem agenda."""
        evenementen = []

        html = self._maak_request(self.AGENDA_URL)
        if not html:
            return evenementen

        # Strategie 1: Zoek naar JSON data in script tags
        evenementen.extend(self._parse_json_data(html))

        # Strategie 2: Parse HTML als fallback
        if not evenementen:
            evenementen.extend(self._parse_html(html))

        return evenementen

    def _parse_json_data(self, html: str) -> list[Evenement]:
        """Extraheer films uit JSON data in de pagina."""
        evenementen = []
        seen_slugs = set()

        # Methode 1: Zoek inline JSON objecten met slug en title
        # Pathé gebruikt inline JSON in de vorm: {"slug":"film-naam","title":"Film Naam",...}
        pattern = r'\{"slug":"([^"]+)","title":"([^"]+)"[^}]*?"releaseAt":\["([^"]+)"\]'
        for match in re.finditer(pattern, html):
            slug = match.group(1)
            title = match.group(2)
            release_date = match.group(3)

            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            try:
                datum = datetime.strptime(release_date, "%Y-%m-%d").replace(hour=20, minute=0)
            except ValueError:
                datum = datetime.now().replace(hour=20, minute=0)

            evenementen.append(Evenement(
                titel=title,
                venue=self.venue,
                datum=datum,
                url=f"{self.VENUE.website}/film/{slug}",
                genre="film",
            ))

        # Methode 2: Alternatief patroon zonder releaseAt
        if not evenementen:
            pattern2 = r'\{"slug":"([^"]+)","title":"([^"]+)"'
            for match in re.finditer(pattern2, html):
                slug = match.group(1)
                title = match.group(2)

                if slug in seen_slugs:
                    continue
                seen_slugs.add(slug)

                evenementen.append(Evenement(
                    titel=title,
                    venue=self.venue,
                    datum=datetime.now().replace(hour=20, minute=0),
                    url=f"{self.VENUE.website}/film/{slug}",
                    genre="film",
                ))

        # Methode 3: JSON-LD als fallback
        if not evenementen:
            soup = BeautifulSoup(html, "lxml")
            for script in soup.select('script[type="application/ld+json"]'):
                try:
                    data = json.loads(script.string)
                    events = self._extract_from_jsonld(data)
                    evenementen.extend(events)
                except (json.JSONDecodeError, TypeError):
                    continue

        return evenementen

    def _extract_from_jsonld(self, data) -> list[Evenement]:
        """Extraheer events uit JSON-LD data."""
        evenementen = []

        if isinstance(data, list):
            for item in data:
                evenementen.extend(self._extract_from_jsonld(item))
        elif isinstance(data, dict):
            item_type = data.get("@type", "")
            if item_type in ("Movie", "ScreeningEvent", "Event"):
                ev = self._parse_jsonld_movie(data)
                if ev:
                    evenementen.append(ev)

        return evenementen

    def _parse_jsonld_movie(self, data: dict) -> Optional[Evenement]:
        """Parse een movie uit JSON-LD."""
        try:
            titel = data.get("name", data.get("title", ""))
            if not titel:
                return None

            url = data.get("url", self.AGENDA_URL)
            if url and not url.startswith("http"):
                url = f"{self.VENUE.website}{url}"

            datum_str = data.get("startDate", "")
            datum = self._parse_datum(datum_str) if datum_str else datetime.now().replace(hour=20, minute=0)

            return Evenement(
                titel=titel,
                venue=self.venue,
                datum=datum,
                url=url,
                genre="film",
            )
        except Exception:
            return None

    def _extract_from_state(self, data: dict) -> list[Evenement]:
        """Extraheer films uit Next.js state data."""
        evenementen = []

        def find_movies(obj):
            if isinstance(obj, dict):
                if "title" in obj and ("slug" in obj or "id" in obj):
                    ev = self._parse_json_movie(obj)
                    if ev:
                        evenementen.append(ev)
                for value in obj.values():
                    find_movies(value)
            elif isinstance(obj, list):
                for item in obj:
                    find_movies(item)

        find_movies(data)
        return evenementen

    def _parse_json_movie(self, data: dict) -> Optional[Evenement]:
        """Parse een film uit JSON data."""
        try:
            titel = data.get("title") or data.get("name", "")
            if not titel or len(titel) < 2:
                return None

            slug = data.get("slug", data.get("id", ""))
            url = f"{self.VENUE.website}/film/{slug}" if slug else self.AGENDA_URL

            # Parse release date als aanwezig
            datum = datetime.now().replace(hour=20, minute=0)
            release_at = data.get("releaseAt", [])
            if release_at and isinstance(release_at, list) and release_at[0]:
                try:
                    datum = datetime.strptime(release_at[0], "%Y-%m-%d").replace(hour=20, minute=0)
                except ValueError:
                    pass

            return Evenement(
                titel=titel,
                venue=self.venue,
                datum=datum,
                url=url,
                genre="film",
            )
        except Exception:
            return None

    def _parse_html(self, html: str) -> list[Evenement]:
        """Parse films uit HTML."""
        evenementen = []
        soup = BeautifulSoup(html, "lxml")
        seen_titles = set()

        # Brede set van selectors
        selectors = [
            "[class*='MovieCard']", "[class*='movie-card']",
            "[class*='MoviePoster']", "[class*='movie-poster']",
            "[data-testid*='movie']", "[data-movie-id]",
            ".movie", ".film", "article",
        ]

        for selector in selectors:
            for item in soup.select(selector):
                ev = self._parse_html_item(item)
                if ev and ev.titel.lower() not in seen_titles:
                    evenementen.append(ev)
                    seen_titles.add(ev.titel.lower())

        # Fallback: zoek alle links naar /film/
        if not evenementen:
            for link in soup.select("a[href*='/film/']"):
                titel = link.get_text(strip=True)
                # Filter navigatie-links
                if titel and len(titel) > 2 and titel.lower() not in seen_titles:
                    if titel.lower() not in ["films", "alle films", "meer films"]:
                        href = link.get("href", "")
                        url = href if href.startswith("http") else f"{self.VENUE.website}{href}"
                        evenementen.append(Evenement(
                            titel=titel,
                            venue=self.venue,
                            datum=datetime.now().replace(hour=20, minute=0),
                            url=url,
                            genre="film",
                        ))
                        seen_titles.add(titel.lower())

        return evenementen

    def _parse_html_item(self, item) -> Optional[Evenement]:
        """Parse een film uit HTML element."""
        try:
            titel = None
            for sel in ["h1", "h2", "h3", "h4", ".title", "[class*='title']", "[class*='Title']"]:
                elem = item.select_one(sel)
                if elem:
                    titel = elem.get_text(strip=True)
                    break

            if not titel or len(titel) < 2:
                return None

            link = item.select_one("a[href*='/film/']") or item.select_one("a[href]")
            url = self.AGENDA_URL
            if link:
                href = link.get("href", "")
                url = href if href.startswith("http") else f"{self.VENUE.website}{href}"

            return Evenement(
                titel=titel,
                venue=self.venue,
                datum=datetime.now().replace(hour=20, minute=0),
                url=url,
                genre="film",
            )
        except Exception:
            return None

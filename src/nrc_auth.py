"""
NRC authenticatie module voor het ophalen van artikelen met abonnement.

Configuratie via environment variables of .env bestand:
    NRC_EMAIL=jouw@email.nl
    NRC_PASSWORD=jouwwachtwoord
"""

import os
import re
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv


@dataclass
class NRCCredentials:
    """NRC inloggegevens."""
    email: str
    password: str


class NRCSession:
    """
    Authenticated session voor NRC.nl.

    Gebruik:
        session = NRCSession()
        if session.login():
            html = session.get_article("https://www.nrc.nl/nieuws/...")
            # Parse artikel...
    """

    LOGIN_URL = "https://login.nrc.nl/login"
    BASE_URL = "https://www.nrc.nl"

    def __init__(self, credentials: Optional[NRCCredentials] = None):
        self.credentials = credentials or self._load_credentials()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
        })
        self._logged_in = False

    def _load_credentials(self) -> Optional[NRCCredentials]:
        """Laad credentials uit environment of .env bestand."""
        # Probeer .env bestand te laden
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)

        email = os.getenv("NRC_EMAIL")
        password = os.getenv("NRC_PASSWORD")

        if email and password:
            return NRCCredentials(email=email, password=password)
        return None

    @property
    def is_configured(self) -> bool:
        """Check of credentials zijn geconfigureerd."""
        return self.credentials is not None

    @property
    def is_logged_in(self) -> bool:
        """Check of sessie is ingelogd."""
        return self._logged_in

    def login(self) -> bool:
        """
        Log in op NRC.nl.

        Returns:
            True als login succesvol, False anders.
        """
        if not self.credentials:
            print("Geen NRC credentials geconfigureerd.")
            print("Stel in via environment variables of .env bestand:")
            print("  NRC_EMAIL=jouw@email.nl")
            print("  NRC_PASSWORD=jouwwachtwoord")
            return False

        try:
            # Haal login pagina op voor CSRF token
            login_page = self.session.get(self.LOGIN_URL)
            soup = BeautifulSoup(login_page.text, "lxml")

            # Zoek CSRF token
            csrf_token = None
            csrf_input = soup.find("input", {"name": "_token"})
            if csrf_input:
                csrf_token = csrf_input.get("value")

            # Login data
            login_data = {
                "email": self.credentials.email,
                "password": self.credentials.password,
            }
            if csrf_token:
                login_data["_token"] = csrf_token

            # Verstuur login
            response = self.session.post(
                self.LOGIN_URL,
                data=login_data,
                allow_redirects=True,
            )

            # Check of login succesvol was
            if "uitloggen" in response.text.lower() or "account" in response.text.lower():
                self._logged_in = True
                return True

            # Check voor foutmelding
            if "wachtwoord" in response.text.lower() and "onjuist" in response.text.lower():
                print("NRC login mislukt: onjuist wachtwoord")
                return False

            print("NRC login status onbekend - probeer artikelen op te halen")
            self._logged_in = True  # Probeer toch
            return True

        except Exception as e:
            print(f"NRC login fout: {e}")
            return False

    def get_article(self, url: str) -> Optional[str]:
        """
        Haal een NRC artikel op.

        Args:
            url: URL van het artikel

        Returns:
            HTML content van het artikel, of None bij fout.
        """
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Fout bij ophalen artikel {url}: {e}")
            return None

    def extract_article_content(self, html: str) -> dict:
        """
        Extraheer content uit een NRC artikel.

        Returns:
            Dict met titel, tekst, auteur, datum, waardering, etc.
        """
        soup = BeautifulSoup(html, "lxml")

        result = {
            "titel": "",
            "tekst": "",
            "auteur": "",
            "datum": "",
            "waardering": None,
            "categorie": "",
        }

        # Titel
        titel_elem = soup.select_one("h1, .article-title, [itemprop='headline']")
        if titel_elem:
            result["titel"] = titel_elem.get_text(strip=True)

        # Artikel tekst
        article_body = soup.select_one(
            "article, .article-body, .article__body, "
            "[itemprop='articleBody'], .story-body"
        )
        if article_body:
            # Verwijder scripts, ads, etc.
            for unwanted in article_body.select("script, style, aside, .ad, .related"):
                unwanted.decompose()
            result["tekst"] = article_body.get_text(separator="\n", strip=True)

        # Auteur
        auteur_elem = soup.select_one(
            ".author, .article-author, [itemprop='author'], "
            ".byline, .article__author"
        )
        if auteur_elem:
            result["auteur"] = auteur_elem.get_text(strip=True)

        # Waardering (ballen)
        result["waardering"] = self._extract_waardering(html)

        # Categorie
        cat_elem = soup.select_one(".category, .section-name, [itemprop='articleSection']")
        if cat_elem:
            result["categorie"] = cat_elem.get_text(strip=True)

        return result

    def _extract_waardering(self, html: str) -> Optional[int]:
        """Extraheer NRC waardering uit artikel HTML."""
        # Zoek naar ballen/sterren in de HTML
        patronen = [
            # Unicode ballen
            (r"([●⬤]{1,5})[○◯]{0,4}", lambda m: len(m.group(1))),
            # Sterren
            (r"([★]{1,5})[☆]{0,4}", lambda m: len(m.group(1))),
            # Rating class of data attribute
            (r'rating["\s:]+(\d)', lambda m: int(m.group(1))),
            (r'score["\s:]+(\d)', lambda m: int(m.group(1))),
            # Tekst
            (r"(\d)\s*/\s*5\s*(?:ballen|sterren)?", lambda m: int(m.group(1))),
        ]

        for patroon, extractor in patronen:
            match = re.search(patroon, html)
            if match:
                try:
                    waarde = extractor(match)
                    if 1 <= waarde <= 5:
                        return waarde
                except (ValueError, IndexError):
                    continue

        return None


def create_session() -> Optional[NRCSession]:
    """
    Maak een NRC sessie aan en log in indien geconfigureerd.

    Returns:
        Ingelogde NRCSession of None als niet geconfigureerd.
    """
    session = NRCSession()

    if not session.is_configured:
        return None

    if session.login():
        return session

    return None

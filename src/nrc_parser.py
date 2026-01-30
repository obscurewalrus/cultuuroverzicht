"""
NRC RSS Feed Parser voor cultuur- en boekentips.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import feedparser
from dateutil import parser as date_parser


@dataclass
class NRCTip:
    """Een cultuur- of boekentip uit NRC."""

    titel: str
    url: str
    beschrijving: str
    publicatiedatum: datetime
    categorie: str  # 'cultuur' of 'boeken'

    # Geëxtraheerde metadata
    artiesten: list[str] = field(default_factory=list)
    auteurs: list[str] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        datum = self.publicatiedatum.strftime("%d-%m-%Y")
        return f"[{self.categorie}] {self.titel} ({datum})"


class NRCParser:
    """Parser voor NRC cultuur en boeken RSS feeds."""

    CULTUUR_FEED = "http://www.nrc.nl/nieuws/categorie/cultuur/rss.php"
    BOEKEN_FEED = "http://www.nrc.nl/boeken/rss.php"

    # Patronen voor het extraheren van namen uit titels/beschrijvingen
    ARTIEST_PATRONEN = [
        r"(?:concert|optreden|show|tour)\s+(?:van\s+)?([A-Z][a-zéèêëïîôûù]+(?:\s+[A-Z][a-zéèêëïîôûù]+)*)",
        r"([A-Z][a-zéèêëïîôûù]+(?:\s+[A-Z][a-zéèêëïîôûù]+)*)\s+(?:speelt|treedt op|geeft concert)",
        r"(?:zangeres?|muzikant|artiest|band)\s+([A-Z][a-zéèêëïîôûù]+(?:\s+[A-Z][a-zéèêëïîôûù]+)*)",
    ]

    AUTEUR_PATRONEN = [
        r"(?:boek|roman|bundel|debuut)\s+(?:van\s+)?([A-Z][a-zéèêëïîôûù]+(?:\s+[A-Z][a-zéèêëïîôûù]+)*)",
        r"([A-Z][a-zéèêëïîôûù]+(?:\s+[A-Z][a-zéèêëïîôûù]+)*)\s+(?:schrijft|schreef|debuteert)",
        r"(?:schrijver|auteur|dichter)\s+([A-Z][a-zéèêëïîôûù]+(?:\s+[A-Z][a-zéèêëïîôûù]+)*)",
    ]

    GENRE_KEYWORDS = {
        "jazz": ["jazz", "swing", "bebop", "blues"],
        "klassiek": ["klassiek", "orkest", "symfonie", "opera", "koor", "philharmonie"],
        "pop": ["pop", "indie", "rock", "electronic"],
        "theater": ["theater", "toneel", "voorstelling", "musical", "cabaret"],
        "dans": ["dans", "ballet", "choreografie"],
        "film": ["film", "cinema", "bioscoop", "documentaire"],
        "literatuur": ["boek", "roman", "bundel", "dichter", "poëzie", "lezing"],
        "kunst": ["expositie", "tentoonstelling", "museum", "galerie"],
    }

    def __init__(self):
        self.tips: list[NRCTip] = []

    def parse_feed(self, url: str, categorie: str) -> list[NRCTip]:
        """Parse een NRC RSS feed en extraheer tips."""
        tips = []

        feed = feedparser.parse(url)

        if feed.bozo and not feed.entries:
            raise ValueError(f"Kon feed niet laden: {url}")

        for entry in feed.entries:
            tip = self._parse_entry(entry, categorie)
            if tip:
                tips.append(tip)

        return tips

    def _parse_entry(self, entry: dict, categorie: str) -> Optional[NRCTip]:
        """Parse een enkele RSS entry naar een NRCTip."""
        try:
            titel = entry.get("title", "").strip()
            url = entry.get("link", "").strip()
            beschrijving = entry.get("summary", entry.get("description", "")).strip()

            # Parse publicatiedatum
            pub_date_str = entry.get("published", entry.get("updated", ""))
            try:
                publicatiedatum = date_parser.parse(pub_date_str)
            except (ValueError, TypeError):
                publicatiedatum = datetime.now()

            # Verwijder HTML tags uit beschrijving
            beschrijving = re.sub(r"<[^>]+>", "", beschrijving)

            tip = NRCTip(
                titel=titel,
                url=url,
                beschrijving=beschrijving,
                publicatiedatum=publicatiedatum,
                categorie=categorie,
            )

            # Extraheer metadata
            tekst = f"{titel} {beschrijving}"
            tip.artiesten = self._extract_names(tekst, self.ARTIEST_PATRONEN)
            tip.auteurs = self._extract_names(tekst, self.AUTEUR_PATRONEN)
            tip.genres = self._extract_genres(tekst)

            return tip

        except Exception:
            return None

    def _extract_names(self, tekst: str, patronen: list[str]) -> list[str]:
        """Extraheer namen uit tekst met regex patronen."""
        namen = set()
        for patroon in patronen:
            matches = re.findall(patroon, tekst, re.IGNORECASE)
            for match in matches:
                naam = match.strip()
                if len(naam) > 2 and naam[0].isupper():
                    namen.add(naam)
        return list(namen)

    def _extract_genres(self, tekst: str) -> list[str]:
        """Extraheer genres gebaseerd op keywords in tekst."""
        tekst_lower = tekst.lower()
        gevonden = []
        for genre, keywords in self.GENRE_KEYWORDS.items():
            if any(kw in tekst_lower for kw in keywords):
                gevonden.append(genre)
        return gevonden

    def laad_alle_tips(self) -> list[NRCTip]:
        """Laad tips van beide NRC feeds."""
        self.tips = []

        try:
            cultuur_tips = self.parse_feed(self.CULTUUR_FEED, "cultuur")
            self.tips.extend(cultuur_tips)
        except Exception as e:
            print(f"Waarschuwing: Kon cultuur feed niet laden: {e}")

        try:
            boeken_tips = self.parse_feed(self.BOEKEN_FEED, "boeken")
            self.tips.extend(boeken_tips)
        except Exception as e:
            print(f"Waarschuwing: Kon boeken feed niet laden: {e}")

        # Sorteer op datum (nieuwste eerst)
        self.tips.sort(key=lambda t: t.publicatiedatum, reverse=True)

        return self.tips

    def zoek_tips(
        self,
        zoekterm: Optional[str] = None,
        categorie: Optional[str] = None,
        genre: Optional[str] = None,
    ) -> list[NRCTip]:
        """Filter tips op zoekterm, categorie of genre."""
        resultaten = self.tips

        if categorie:
            resultaten = [t for t in resultaten if t.categorie == categorie]

        if genre:
            resultaten = [t for t in resultaten if genre in t.genres]

        if zoekterm:
            zoekterm_lower = zoekterm.lower()
            resultaten = [
                t for t in resultaten
                if zoekterm_lower in t.titel.lower()
                or zoekterm_lower in t.beschrijving.lower()
                or any(zoekterm_lower in a.lower() for a in t.artiesten)
                or any(zoekterm_lower in a.lower() for a in t.auteurs)
            ]

        return resultaten


if __name__ == "__main__":
    # Test de parser
    parser = NRCParser()
    tips = parser.laad_alle_tips()

    print(f"Geladen: {len(tips)} tips\n")
    for tip in tips[:5]:
        print(f"{tip}")
        if tip.artiesten:
            print(f"  Artiesten: {', '.join(tip.artiesten)}")
        if tip.auteurs:
            print(f"  Auteurs: {', '.join(tip.auteurs)}")
        if tip.genres:
            print(f"  Genres: {', '.join(tip.genres)}")
        print()

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

    # NRC waardering (0-5 ballen, None als onbekend)
    waardering: Optional[int] = None
    waardering_type: str = ""  # 'film', 'album', 'boek', 'theater', etc.

    def __str__(self) -> str:
        datum = self.publicatiedatum.strftime("%d-%m-%Y")
        ballen = self.ballen_weergave if self.waardering else ""
        return f"[{self.categorie}] {self.titel} {ballen}({datum})"

    @property
    def ballen_weergave(self) -> str:
        """Geef waardering weer als ballen (●○)."""
        if self.waardering is None:
            return ""
        vol = "●" * self.waardering
        leeg = "○" * (5 - self.waardering)
        return f"{vol}{leeg} "

    @property
    def is_aanrader(self) -> bool:
        """True als dit een aanrader is (4+ ballen of expliciet aanbevolen)."""
        if self.waardering and self.waardering >= 4:
            return True
        # Check voor expliciete aanbevelingen in tekst
        tekst = f"{self.titel} {self.beschrijving}".lower()
        return any(term in tekst for term in [
            "aanrader", "must-see", "meesterwerk", "topfilm",
            "niet missen", "absolute must", "briljant"
        ])


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

    # Patronen voor NRC waardering (ballen)
    # NRC gebruikt diverse notaties: "●●●●○", "4/5", "vier ballen", "★★★★☆"
    WAARDERING_PATRONEN = [
        # Unicode ballen: ●●●●○ of ⬤⬤⬤○○
        (r"([●⬤]{1,5})[○◯]{0,4}", "ballen"),
        # Sterren: ★★★★☆
        (r"([★]{1,5})[☆]{0,4}", "sterren"),
        # Fractie notatie: 4/5, 3/5
        (r"(\d)\s*/\s*5\s*(?:ballen|sterren)?", "fractie"),
        # Tekstueel: "vier ballen", "3 ballen", "vijf sterren"
        (r"(een|twee|drie|vier|vijf|\d)\s*(?:ballen?|sterren?)", "tekst"),
        # Recensie score indicatie
        (r"score[:\s]+(\d)[/\s]*5", "score"),
    ]

    TEKST_NAAR_NUMMER = {
        "een": 1, "twee": 2, "drie": 3, "vier": 4, "vijf": 5,
        "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
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

            # Extraheer waardering (ballen)
            waardering, waardering_type = self._extract_waardering(tekst)
            tip.waardering = waardering
            tip.waardering_type = waardering_type

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

    def _extract_waardering(self, tekst: str) -> tuple[Optional[int], str]:
        """
        Extraheer NRC waardering (ballen/sterren) uit tekst.

        Returns:
            Tuple van (waardering 1-5, type waardering)
        """
        for patroon, notatie_type in self.WAARDERING_PATRONEN:
            match = re.search(patroon, tekst, re.IGNORECASE)
            if match:
                waarde = match.group(1)

                if notatie_type == "ballen" or notatie_type == "sterren":
                    # Tel het aantal gevulde symbolen
                    return len(waarde), self._bepaal_waardering_type(tekst)

                elif notatie_type == "fractie" or notatie_type == "score":
                    # Direct nummer
                    nummer = int(waarde)
                    if 1 <= nummer <= 5:
                        return nummer, self._bepaal_waardering_type(tekst)

                elif notatie_type == "tekst":
                    # Converteer tekst naar nummer
                    nummer = self.TEKST_NAAR_NUMMER.get(waarde.lower())
                    if nummer:
                        return nummer, self._bepaal_waardering_type(tekst)

        return None, ""

    def _bepaal_waardering_type(self, tekst: str) -> str:
        """Bepaal het type waardering (film, album, boek, etc.)."""
        tekst_lower = tekst.lower()

        type_keywords = {
            "film": ["film", "bioscoop", "cinema", "regisseur"],
            "album": ["album", "plaat", "cd", "lp", "muziek"],
            "boek": ["boek", "roman", "debuut", "bundel", "schrijver"],
            "theater": ["theater", "toneel", "voorstelling", "musical"],
            "serie": ["serie", "seizoen", "aflevering", "netflix", "streaming"],
            "concert": ["concert", "optreden", "tour", "live"],
            "expositie": ["expositie", "tentoonstelling", "museum"],
        }

        for wtype, keywords in type_keywords.items():
            if any(kw in tekst_lower for kw in keywords):
                return wtype

        return "algemeen"

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

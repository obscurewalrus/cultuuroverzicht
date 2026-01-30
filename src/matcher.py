"""
Matching engine om NRC tips te koppelen aan lokale evenementen.
"""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional

from .nrc_parser import NRCTip
from .venues.base import Evenement


@dataclass
class Match:
    """Een match tussen een NRC tip en een lokaal evenement."""

    tip: NRCTip
    evenement: Evenement
    score: float  # 0.0 - 1.0
    match_type: str  # 'exact', 'artiest', 'titel', 'fuzzy'

    def __str__(self) -> str:
        waardering = self.tip.ballen_weergave if self.tip.waardering else ""
        return (
            f"[{self.score:.0%}] {waardering}{self.tip.titel}\n"
            f"    → {self.evenement}"
        )

    @property
    def prioriteit(self) -> float:
        """
        Gecombineerde prioriteit score voor sortering.
        Combineert match score met NRC waardering.
        """
        # Basis: match score (0-1)
        basis = self.score

        # Bonus voor hoge NRC waardering
        if self.tip.waardering:
            # 4 ballen = +20%, 5 ballen = +30%
            waardering_bonus = (self.tip.waardering - 3) * 0.1 if self.tip.waardering >= 4 else 0
            basis += waardering_bonus

        # Bonus als het een expliciete aanrader is
        if self.tip.is_aanrader:
            basis += 0.05

        return min(basis, 1.0)

    @property
    def is_topkeuze(self) -> bool:
        """True als dit een topkeuze is (goede match + hoge waardering)."""
        return self.score >= 0.7 and self.tip.waardering is not None and self.tip.waardering >= 4


@dataclass
class MatchResult:
    """Resultaat van de matching operatie."""

    matches: list[Match] = field(default_factory=list)
    ongematchte_tips: list[NRCTip] = field(default_factory=list)
    ongematchte_evenementen: list[Evenement] = field(default_factory=list)

    @property
    def match_percentage(self) -> float:
        """Bereken het percentage gematchte tips."""
        totaal = len(self.matches) + len(self.ongematchte_tips)
        if totaal == 0:
            return 0.0
        return len(self.matches) / totaal

    @property
    def topkeuzes(self) -> list[Match]:
        """Geef alleen de topkeuzes terug (hoge match + hoge waardering)."""
        return [m for m in self.matches if m.is_topkeuze]

    @property
    def aanraders(self) -> list[Match]:
        """Geef matches terug van NRC-aanraders (4+ ballen)."""
        return [m for m in self.matches if m.tip.is_aanrader]

    def sorteer_op_prioriteit(self) -> None:
        """Sorteer matches op gecombineerde prioriteit (score + waardering)."""
        self.matches.sort(key=lambda m: m.prioriteit, reverse=True)

    def sorteer_op_datum(self) -> None:
        """Sorteer matches op evenement datum."""
        self.matches.sort(key=lambda m: m.evenement.datum)

    def sorteer_op_waardering(self) -> None:
        """Sorteer matches op NRC waardering (hoogste eerst)."""
        self.matches.sort(
            key=lambda m: (m.tip.waardering or 0, m.score),
            reverse=True
        )


class Matcher:
    """
    Match NRC cultuur/boeken tips met lokale evenementen.

    Matching strategie:
    1. Exact match op artiest/auteursnaam
    2. Fuzzy match op titel
    3. Genre + keyword matching
    4. NRC waardering als bonus factor
    """

    # Minimum scores voor verschillende match types
    EXACT_THRESHOLD = 0.95
    ARTIEST_THRESHOLD = 0.85
    TITEL_THRESHOLD = 0.70
    FUZZY_THRESHOLD = 0.55

    def __init__(
        self,
        min_score: float = 0.5,
        alleen_aanraders: bool = False,
        min_waardering: Optional[int] = None,
    ):
        self.min_score = min_score
        self.alleen_aanraders = alleen_aanraders
        self.min_waardering = min_waardering
        self._stopwoorden = self._laad_stopwoorden()

    def match(
        self,
        tips: list[NRCTip],
        evenementen: list[Evenement],
    ) -> MatchResult:
        """Match NRC tips met lokale evenementen."""
        result = MatchResult()
        gematchte_evenementen = set()

        # Filter tips indien nodig
        gefilterde_tips = tips
        if self.alleen_aanraders:
            gefilterde_tips = [t for t in tips if t.is_aanrader]
        if self.min_waardering:
            gefilterde_tips = [
                t for t in gefilterde_tips
                if t.waardering and t.waardering >= self.min_waardering
            ]

        for tip in gefilterde_tips:
            beste_match = self._vind_beste_match(tip, evenementen)

            if beste_match and beste_match.score >= self.min_score:
                result.matches.append(beste_match)
                gematchte_evenementen.add(id(beste_match.evenement))
            else:
                result.ongematchte_tips.append(tip)

        # Vind ongematchte evenementen
        for ev in evenementen:
            if id(ev) not in gematchte_evenementen:
                result.ongematchte_evenementen.append(ev)

        # Sorteer matches op prioriteit (score + waardering)
        result.sorteer_op_prioriteit()

        return result

    def _vind_beste_match(
        self,
        tip: NRCTip,
        evenementen: list[Evenement],
    ) -> Optional[Match]:
        """Vind de beste match voor een NRC tip."""
        beste: Optional[Match] = None
        beste_score = 0.0

        for evenement in evenementen:
            match = self._bereken_match(tip, evenement)
            if match and match.score > beste_score:
                beste = match
                beste_score = match.score

        return beste

    def _bereken_match(self, tip: NRCTip, evenement: Evenement) -> Optional[Match]:
        """Bereken de match score tussen een tip en evenement."""
        scores = []

        # 1. Exacte artiest/auteur match
        artiest_score = self._match_artiesten(tip, evenement)
        if artiest_score >= self.EXACT_THRESHOLD:
            return Match(tip, evenement, artiest_score, "exact")
        if artiest_score > 0:
            scores.append(("artiest", artiest_score))

        # 2. Titel similarity
        titel_score = self._match_titel(tip.titel, evenement.titel)
        if titel_score >= self.EXACT_THRESHOLD:
            return Match(tip, evenement, titel_score, "exact")
        if titel_score > 0:
            scores.append(("titel", titel_score))

        # 3. Genre matching
        genre_score = self._match_genre(tip, evenement)
        if genre_score > 0:
            scores.append(("genre", genre_score * 0.3))  # Genre weegt minder

        # 4. Beschrijving fuzzy match
        if tip.beschrijving and evenement.beschrijving:
            fuzzy_score = self._fuzzy_match(tip.beschrijving, evenement.beschrijving)
            if fuzzy_score > self.FUZZY_THRESHOLD:
                scores.append(("fuzzy", fuzzy_score * 0.5))

        # Combineer scores
        if not scores:
            return None

        # Gewogen gemiddelde, met voorkeur voor artiest/titel matches
        weights = {"artiest": 1.5, "titel": 1.2, "genre": 0.5, "fuzzy": 0.3}
        total_weight = sum(weights.get(t, 1.0) for t, _ in scores)
        final_score = sum(weights.get(t, 1.0) * s for t, s in scores) / total_weight

        if final_score < self.min_score:
            return None

        match_type = max(scores, key=lambda x: x[1])[0]
        return Match(tip, evenement, min(final_score, 1.0), match_type)

    def _match_artiesten(self, tip: NRCTip, evenement: Evenement) -> float:
        """Match artiesten/auteurs uit tip met evenement."""
        tip_namen = set(self._normaliseer(n) for n in tip.artiesten + tip.auteurs)
        event_namen = set(self._normaliseer(n) for n in evenement.artiesten)

        if not tip_namen or not event_namen:
            return 0.0

        # Check voor exacte overlap
        overlap = tip_namen & event_namen
        if overlap:
            return 1.0

        # Check voor fuzzy naam matches
        beste_score = 0.0
        for tip_naam in tip_namen:
            for event_naam in event_namen:
                score = self._fuzzy_match(tip_naam, event_naam)
                beste_score = max(beste_score, score)

        return beste_score

    def _match_titel(self, titel1: str, titel2: str) -> float:
        """Match twee titels."""
        t1 = self._normaliseer(titel1)
        t2 = self._normaliseer(titel2)

        # Exacte match
        if t1 == t2:
            return 1.0

        # Één titel bevat de andere
        if t1 in t2 or t2 in t1:
            return 0.9

        # Fuzzy match
        return self._fuzzy_match(t1, t2)

    def _match_genre(self, tip: NRCTip, evenement: Evenement) -> float:
        """Match genres."""
        if not tip.genres or not evenement.genre:
            return 0.0

        event_genre = self._normaliseer(evenement.genre)

        for tip_genre in tip.genres:
            if self._normaliseer(tip_genre) == event_genre:
                return 1.0
            if tip_genre.lower() in event_genre or event_genre in tip_genre.lower():
                return 0.8

        return 0.0

    def _fuzzy_match(self, s1: str, s2: str) -> float:
        """Bereken fuzzy similarity tussen twee strings."""
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def _normaliseer(self, tekst: str) -> str:
        """Normaliseer tekst voor matching."""
        # Lowercase
        tekst = tekst.lower()

        # Verwijder leestekens
        tekst = re.sub(r"[^\w\s]", " ", tekst)

        # Verwijder stopwoorden
        woorden = tekst.split()
        woorden = [w for w in woorden if w not in self._stopwoorden]

        # Normaliseer whitespace
        return " ".join(woorden)

    def _laad_stopwoorden(self) -> set[str]:
        """Laad Nederlandse stopwoorden."""
        return {
            "de", "het", "een", "en", "van", "in", "op", "aan", "met",
            "voor", "door", "over", "bij", "uit", "naar", "te", "tot",
            "als", "ook", "maar", "dan", "nog", "wel", "niet", "geen",
            "die", "dat", "deze", "dit", "zijn", "was", "worden", "wordt",
            "the", "a", "an", "and", "or", "of", "in", "on", "at", "to",
        }


def match_tips_met_evenementen(
    tips: list[NRCTip],
    evenementen: list[Evenement],
    min_score: float = 0.5,
    alleen_aanraders: bool = False,
    min_waardering: Optional[int] = None,
) -> MatchResult:
    """Convenience functie voor matching."""
    matcher = Matcher(
        min_score=min_score,
        alleen_aanraders=alleen_aanraders,
        min_waardering=min_waardering,
    )
    return matcher.match(tips, evenementen)

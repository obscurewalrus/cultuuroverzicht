"""
Venue scrapers voor theaters, concertzalen, bioscopen, musea en boekhandels
in regio Haarlem/Hoofddorp.
"""

from .base import Venue, Evenement, VenueScraper, VenueType
from .patronaat import PatronaatScraper
from .philharmonie import PhilharmonieScraper
from .stadsschouwburg import StadsschouwburgScraper
from .toneelschuur import ToneelschuurScraper
from .de_meerse import DeMeerseScraper
from .pathe import PatheScraper
from .kinepolis import KinepolisScraper
from .frans_hals import FransHalsMuseumScraper
from .boekhandels import AthenaeumscraPer, VrijeDenkerScraper

__all__ = [
    "Venue",
    "Evenement",
    "VenueScraper",
    "VenueType",
    # Concertzalen
    "PatronaatScraper",
    "PhilharmonieScraper",
    # Theaters
    "StadsschouwburgScraper",
    "ToneelschuurScraper",
    "DeMeerseScraper",
    # Bioscopen
    "PatheScraper",
    "KinepolisScraper",
    # Musea
    "FransHalsMuseumScraper",
    # Boekhandels
    "AthenaeumscraPer",
    "VrijeDenkerScraper",
]

"""
Venue scrapers voor theaters, concertzalen en bioscopen in regio Haarlem/Hoofddorp.
"""

from .base import Venue, Evenement, VenueScraper
from .patronaat import PatronaatScraper
from .philharmonie import PhilharmonieScraper
from .stadsschouwburg import StadsschouwburgScraper
from .toneelschuur import ToneelschuurScraper
from .de_meerse import DeMeerseScraper

__all__ = [
    "Venue",
    "Evenement",
    "VenueScraper",
    "PatronaatScraper",
    "PhilharmonieScraper",
    "StadsschouwburgScraper",
    "ToneelschuurScraper",
    "DeMeerseScraper",
]

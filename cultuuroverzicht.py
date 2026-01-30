#!/usr/bin/env python3
"""
Cultuuroverzicht - NRC tips matcher voor regio Haarlem/Hoofddorp

Gebruik:
    python cultuuroverzicht.py                  # Toon gematchte NRC tips
    python cultuuroverzicht.py --agenda         # Toon lokale agenda
    python cultuuroverzicht.py --tips           # Toon NRC tips
    python cultuuroverzicht.py --zoek "jazz"    # Zoek
"""

from src.cli import main

if __name__ == "__main__":
    main()

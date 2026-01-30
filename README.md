# Cultuuroverzicht

NRC cultuur- en boekentips matcher voor regio Haarlem/Hoofddorp.

Deze tool combineert NRC-aanbevelingen met de agenda's van lokale theaters, concertzalen en bioscopen, zodat je eenvoudig kunt zien welke aangeraden voorstellingen, concerten en auteurs in jouw regio te zien zijn.

## Features

- **NRC RSS feeds**: Haalt automatisch cultuur- en boekentips op van NRC
- **Lokale venues**: Scrapt agenda's van:
  - Patronaat (concerten, Haarlem)
  - Philharmonie Haarlem (klassiek)
  - Stadsschouwburg Haarlem (theater)
  - Toneelschuur + Filmschuur (theater/film, Haarlem)
  - De Meerse (theater, Hoofddorp)
- **Slimme matching**: Koppelt NRC-tips aan lokale evenementen op basis van artiesten, titels en genres
- **Mooie CLI output**: Overzichtelijke tabellen met Rich

## Installatie

```bash
# Clone of download de repository
cd cultuuroverzicht

# Maak een virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# of: venv\Scripts\activate  # Windows

# Installeer dependencies
pip install -r requirements.txt
```

## Gebruik

```bash
# Toon gematchte NRC tips met lokale evenementen
python cultuuroverzicht.py

# Toon alleen de lokale agenda
python cultuuroverzicht.py --agenda

# Toon alleen NRC tips
python cultuuroverzicht.py --tips

# Zoek op een specifieke term
python cultuuroverzicht.py --zoek "jazz"
python cultuuroverzicht.py --zoek "cabaret"

# Bekijk alleen de komende 2 weken
python cultuuroverzicht.py --dagen 14

# Verberg uitverkochte evenementen
python cultuuroverzicht.py --alleen-beschikbaar

# Combineer opties
python cultuuroverzicht.py --zoek "theater" --dagen 7 --alleen-beschikbaar
```

## Opties

| Optie | Kort | Beschrijving |
|-------|------|--------------|
| `--agenda` | `-a` | Toon volledige lokale agenda |
| `--tips` | `-t` | Toon alleen NRC tips |
| `--zoek` | `-z` | Filter op zoekterm |
| `--dagen` | `-d` | Aantal dagen vooruit (default: 30) |
| `--min-score` | `-m` | Minimum match score 0.0-1.0 (default: 0.5) |
| `--alleen-beschikbaar` | | Verberg uitverkochte evenementen |
| `--max` | `-n` | Maximum aantal items (default: 25) |

## Hoe het werkt

1. **NRC Parser**: Haalt RSS feeds op en extraheert:
   - Titel, URL, beschrijving
   - Publicatiedatum
   - Artiesten/auteurs (via regex patronen)
   - Genres (via keyword matching)

2. **Venue Scrapers**: Bezoeken de agenda pagina's van lokale venues en extraheren:
   - Evenement titel en URL
   - Datum en tijd
   - Genre/categorie
   - Uitverkocht status

3. **Matcher**: Vergelijkt tips met evenementen:
   - Exacte artiest/auteur matches (hoogste score)
   - Titel similarity (fuzzy matching)
   - Genre overlap
   - Beschrijving keywords

## Venues toevoegen

Om een nieuw venue toe te voegen:

1. Maak een nieuw bestand in `src/venues/` (bijv. `nieuw_venue.py`)
2. Extend de `VenueScraper` class
3. Implementeer de `scrape()` methode
4. Voeg toe aan `src/venues/__init__.py`
5. Voeg toe aan de scrapers lijst in `src/cli.py`

Voorbeeld:
```python
from .base import Venue, VenueType, Evenement, VenueScraper

class NieuwVenueScraper(VenueScraper):
    VENUE = Venue(
        naam="Nieuw Venue",
        adres="Straat 1",
        plaats="Stad",
        website="https://www.nieuwvenue.nl",
        venue_type=VenueType.THEATER,
    )

    def __init__(self):
        super().__init__(self.VENUE)

    def scrape(self) -> list[Evenement]:
        # Implementeer scraping logica
        pass
```

## Beperkingen

- De venue scrapers zijn afhankelijk van de huidige structuur van de websites. Als een venue hun website aanpast, moet de scraper mogelijk worden bijgewerkt.
- NRC RSS feeds kunnen beperkt zijn in het aantal items dat ze bevatten.
- Matching is gebaseerd op tekstuele overeenkomsten en kan niet-perfecte resultaten opleveren.

## Licentie

MIT

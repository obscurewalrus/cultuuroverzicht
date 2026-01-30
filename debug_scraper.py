#!/usr/bin/env python3
"""
Debug script om venue HTML structuur te analyseren.

Gebruik:
    python debug_scraper.py              # Debug Pathé
    python debug_scraper.py --all        # Debug alle venues
    python debug_scraper.py --search "Dust Bunny"  # Zoek specifieke film
"""

import argparse
import json
import requests
from bs4 import BeautifulSoup


def fetch_page(url: str) -> tuple[str, int]:
    """Haal pagina op."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "nl-NL,nl;q=0.9",
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        return response.text, response.status_code
    except Exception as e:
        return str(e), 0


def debug_venue(name: str, url: str, search_term: str = None):
    """Analyseer een venue pagina."""
    print(f"\n{'='*60}")
    print(f"VENUE: {name}")
    print(f"URL: {url}")
    print('='*60)

    html, status = fetch_page(url)
    print(f"Status: {status}")
    print(f"Content length: {len(html)}")

    if status != 200:
        print(f"FOUT: Kon pagina niet ophalen")
        return

    soup = BeautifulSoup(html, "lxml")

    # Zoek naar film/event links
    print("\n--- Links naar /film/ of evenementen ---")
    film_links = soup.select("a[href*='/film/'], a[href*='/event/'], a[href*='/voorstelling/']")
    print(f"Gevonden: {len(film_links)} links")
    seen = set()
    for link in film_links[:20]:
        titel = link.get_text(strip=True)
        href = link.get('href', '')
        if titel and len(titel) > 2 and titel not in seen:
            print(f"  • {titel[:50]}")
            print(f"    → {href[:80]}")
            seen.add(titel)

    # Zoek naar JSON-LD
    print("\n--- JSON-LD data ---")
    jsonld_scripts = soup.select('script[type="application/ld+json"]')
    print(f"Gevonden: {len(jsonld_scripts)} JSON-LD scripts")
    for script in jsonld_scripts[:3]:
        try:
            data = json.loads(script.string)
            print(f"  Type: {data.get('@type', 'unknown')}")
            if isinstance(data, dict) and 'name' in data:
                print(f"  Name: {data.get('name', '')[:50]}")
        except:
            pass

    # Zoek naar Next.js data
    print("\n--- Next.js / React data ---")
    next_data = soup.select_one('script#__NEXT_DATA__')
    if next_data:
        print("  __NEXT_DATA__ gevonden!")
        try:
            data = json.loads(next_data.string)
            # Zoek naar movies in de data structuur
            def find_titles(obj, path="", found=[]):
                if isinstance(obj, dict):
                    if 'title' in obj:
                        found.append(f"{path}: {obj['title'][:50]}")
                    for k, v in obj.items():
                        find_titles(v, f"{path}.{k}", found)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj[:5]):
                        find_titles(item, f"{path}[{i}]", found)
                return found
            titles = find_titles(data, "root", [])
            for t in titles[:10]:
                print(f"  {t}")
        except Exception as e:
            print(f"  Parse error: {e}")
    else:
        print("  Geen __NEXT_DATA__ gevonden")

    # Zoek specifieke term
    if search_term:
        print(f"\n--- Zoeken naar '{search_term}' ---")
        if search_term.lower() in html.lower():
            print(f"✓ '{search_term}' GEVONDEN in HTML!")
            idx = html.lower().find(search_term.lower())
            context = html[max(0, idx-100):idx+len(search_term)+100]
            # Clean up context
            context = ' '.join(context.split())
            print(f"  Context: ...{context}...")
        else:
            print(f"✗ '{search_term}' NIET gevonden in HTML")


def main():
    parser = argparse.ArgumentParser(description="Debug venue scrapers")
    parser.add_argument("--all", action="store_true", help="Debug alle venues")
    parser.add_argument("--search", type=str, help="Zoek specifieke term (bijv. 'Dust Bunny')")
    parser.add_argument("--venue", type=str, help="Specifieke venue (pathe, schuur, patronaat, etc.)")
    args = parser.parse_args()

    venues = {
        "pathe": ("Pathé Haarlem", "https://www.pathe.nl/bioscoop/haarlem"),
        "schuur": ("De Schuur", "https://www.schuur.nl/agenda/"),
        "patronaat": ("Patronaat", "https://patronaat.nl/programma/"),
        "philharmonie": ("Philharmonie", "https://www.philharmoniehaarlem.nl/agenda/"),
        "stadsschouwburg": ("Stadsschouwburg", "https://www.theater-haarlem.nl/agenda/"),
        "meerse": ("De Meerse", "https://www.demeerse.nl/agenda/"),
        "franshals": ("Frans Hals Museum", "https://franshalsmuseum.nl/nl/zien-en-doen"),
    }

    search_term = args.search or "Dust Bunny"

    if args.venue:
        if args.venue in venues:
            name, url = venues[args.venue]
            debug_venue(name, url, search_term)
        else:
            print(f"Onbekende venue: {args.venue}")
            print(f"Opties: {', '.join(venues.keys())}")
    elif args.all:
        for name, url in venues.values():
            debug_venue(name, url, search_term)
    else:
        # Default: alleen Pathé
        debug_venue("Pathé Haarlem", "https://www.pathe.nl/bioscoop/haarlem", search_term)


if __name__ == "__main__":
    main()

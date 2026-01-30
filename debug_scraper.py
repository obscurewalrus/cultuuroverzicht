#!/usr/bin/env python3
"""Debug script om venue HTML structuur te analyseren."""

import requests
from bs4 import BeautifulSoup

def debug_pathe():
    """Analyseer Pathé Haarlem HTML structuur."""
    url = "https://www.pathe.nl/bioscoop/haarlem"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "nl-NL,nl;q=0.9",
    }

    print(f"Ophalen: {url}")
    response = requests.get(url, headers=headers, timeout=15)
    print(f"Status: {response.status_code}")
    print(f"Content length: {len(response.text)}")

    soup = BeautifulSoup(response.text, "lxml")

    # Zoek alle mogelijke film containers
    print("\n--- Zoeken naar film elementen ---")

    selectors = [
        "article", ".movie", ".film", "[data-movie]",
        ".card", ".poster", ".schedule", ".showing",
        "a[href*='/film/']", "div[class*='movie']", "div[class*='film']",
        "section", ".content", "main"
    ]

    for sel in selectors:
        items = soup.select(sel)
        if items:
            print(f"\n{sel}: {len(items)} gevonden")
            if len(items) <= 3:
                for item in items[:3]:
                    classes = item.get('class', [])
                    text = item.get_text(strip=True)[:100]
                    print(f"  - classes: {classes}")
                    print(f"    text: {text}...")

    # Zoek specifiek naar "Dust Bunny"
    print("\n--- Zoeken naar 'Dust Bunny' ---")
    if "dust bunny" in response.text.lower():
        print("✓ 'Dust Bunny' gevonden in HTML!")
        # Vind de context
        idx = response.text.lower().find("dust bunny")
        context = response.text[max(0, idx-200):idx+200]
        print(f"Context: ...{context}...")
    else:
        print("✗ 'Dust Bunny' niet gevonden in HTML")

    # Toon eerste 5000 chars van de HTML
    print("\n--- Eerste deel van HTML ---")
    print(response.text[:5000])

    # Zoek naar JSON data
    print("\n--- Zoeken naar JSON/Script data ---")
    scripts = soup.select("script")
    for script in scripts:
        text = script.get_text()
        if "movie" in text.lower() or "film" in text.lower():
            print(f"Script met film data gevonden: {text[:500]}...")
            break

if __name__ == "__main__":
    debug_pathe()

"""
CLI interface voor Cultuuroverzicht.
"""

import argparse
from datetime import datetime, timedelta
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from .nrc_parser import NRCParser, NRCTip
from .matcher import Matcher, MatchResult
from .venues import (
    PatronaatScraper,
    PhilharmonieScraper,
    StadsschouwburgScraper,
    ToneelschuurScraper,
    DeMeerseScraper,
    PatheScraper,
    KinepolisScraper,
    FransHalsMuseumScraper,
    AthenaeumscraPer,
    VrijeDenkerScraper,
)
from .venues.base import Evenement

console = Console()


def laad_nrc_tips() -> list[NRCTip]:
    """Laad NRC cultuur en boeken tips."""
    console.print("[bold blue]NRC tips laden...[/bold blue]")

    parser = NRCParser()
    tips = parser.laad_alle_tips()

    console.print(f"  Geladen: {len(tips)} tips")
    return tips


def laad_lokale_evenementen(
    dagen_vooruit: int = 30,
    alleen_beschikbaar: bool = False,
) -> list[Evenement]:
    """Laad evenementen van alle lokale venues."""
    console.print("[bold blue]Lokale agenda's laden...[/bold blue]")

    scrapers = [
        # Concertzalen
        PatronaatScraper(),
        PhilharmonieScraper(),
        # Theaters
        StadsschouwburgScraper(),
        ToneelschuurScraper(),
        DeMeerseScraper(),
        # Bioscopen
        PatheScraper(),
        KinepolisScraper(),
        # Musea
        FransHalsMuseumScraper(),
        # Boekhandels
        AthenaeumscraPer(),
        VrijeDenkerScraper(),
    ]

    alle_evenementen = []
    vandaag = datetime.now()
    eindatum = vandaag + timedelta(days=dagen_vooruit)

    for scraper in scrapers:
        try:
            evenementen = scraper.scrape()
            console.print(f"  {scraper.venue.naam}: {len(evenementen)} evenementen")

            # Filter op datum
            for ev in evenementen:
                if vandaag <= ev.datum <= eindatum:
                    if alleen_beschikbaar and ev.uitverkocht:
                        continue
                    alle_evenementen.append(ev)

        except Exception as e:
            console.print(f"  [yellow]Waarschuwing: {scraper.venue.naam} - {e}[/yellow]")

    # Sorteer op datum
    alle_evenementen.sort(key=lambda e: e.datum)

    console.print(f"  Totaal: {len(alle_evenementen)} evenementen in komende {dagen_vooruit} dagen")
    return alle_evenementen


def toon_matches(result: MatchResult, max_items: int = 20, toon_topkeuzes: bool = False):
    """Toon gematchte NRC tips met lokale evenementen."""
    if not result.matches:
        console.print("\n[yellow]Geen matches gevonden.[/yellow]")
        return

    # Optioneel: toon eerst topkeuzes apart
    if toon_topkeuzes and result.topkeuzes:
        console.print(f"\n[bold yellow]Topkeuzes ({len(result.topkeuzes)})[/bold yellow]")
        console.print("[dim]Hoge NRC-waardering + goede match[/dim]\n")
        for match in result.topkeuzes[:5]:
            ballen = match.tip.ballen_weergave
            console.print(f"  {ballen}[bold]{match.tip.titel}[/bold]")
            console.print(f"    → {match.evenement.titel} @ {match.evenement.venue.naam}")
            console.print(f"    → {match.evenement.datum.strftime('%a %d %b %H:%M')}")
            console.print()

    console.print(f"\n[bold green]Gevonden: {len(result.matches)} matches[/bold green]")

    # Toon aantal aanraders
    aanraders = [m for m in result.matches if m.tip.waardering and m.tip.waardering >= 4]
    if aanraders:
        console.print(f"[dim]Waarvan {len(aanraders)} met 4+ ballen[/dim]")

    table = Table(
        title="NRC Tips in jouw regio",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )

    table.add_column("Score", style="cyan", width=7)
    table.add_column("NRC", style="yellow", width=7)
    table.add_column("Tip", style="white", width=28)
    table.add_column("Evenement", style="green", width=23)
    table.add_column("Venue", style="blue", width=18)
    table.add_column("Datum", style="yellow", width=12)

    for match in result.matches[:max_items]:
        score = f"{match.score:.0%}"

        # NRC waardering als ballen
        if match.tip.waardering:
            ballen = "●" * match.tip.waardering + "○" * (5 - match.tip.waardering)
        else:
            ballen = "[dim]-[/dim]"

        tip_titel = match.tip.titel[:26] + "..." if len(match.tip.titel) > 28 else match.tip.titel
        event_titel = match.evenement.titel[:21] + "..." if len(match.evenement.titel) > 23 else match.evenement.titel
        venue = match.evenement.venue.naam[:16] + "..." if len(match.evenement.venue.naam) > 18 else match.evenement.venue.naam
        datum = match.evenement.datum.strftime("%d %b %H:%M")

        # Highlight topkeuzes
        if match.is_topkeuze:
            tip_titel = f"[bold]{tip_titel}[/bold]"

        if match.evenement.uitverkocht:
            event_titel = f"[strike]{event_titel}[/strike]"

        table.add_row(score, ballen, tip_titel, event_titel, venue, datum)

    console.print(table)


def toon_agenda(evenementen: list[Evenement], max_items: int = 30):
    """Toon alle aankomende evenementen."""
    if not evenementen:
        console.print("\n[yellow]Geen evenementen gevonden.[/yellow]")
        return

    table = Table(
        title="Agenda Haarlem/Hoofddorp",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )

    table.add_column("Datum", style="yellow", width=15)
    table.add_column("Evenement", style="white", width=35)
    table.add_column("Venue", style="blue", width=22)
    table.add_column("Genre", style="cyan", width=12)

    huidige_datum = None
    for ev in evenementen[:max_items]:
        datum_str = ev.datum.strftime("%a %d %b")
        tijd_str = ev.datum.strftime("%H:%M")

        # Groepeer per dag
        if datum_str != huidige_datum:
            if huidige_datum is not None:
                table.add_row("", "", "", "")  # Lege rij
            huidige_datum = datum_str
            datum_display = f"{datum_str} {tijd_str}"
        else:
            datum_display = f"        {tijd_str}"

        titel = ev.titel[:33] + "..." if len(ev.titel) > 35 else ev.titel
        if ev.uitverkocht:
            titel = f"[strike dim]{titel}[/strike dim]"

        venue = ev.venue.naam[:20] + "..." if len(ev.venue.naam) > 22 else ev.venue.naam
        genre = ev.genre[:10] if ev.genre else ""

        table.add_row(datum_display, titel, venue, genre)

    console.print(table)


def toon_tips(tips: list[NRCTip], max_items: int = 15):
    """Toon NRC tips."""
    # Toon statistieken over waarderingen
    met_waardering = [t for t in tips if t.waardering is not None]
    aanraders = [t for t in tips if t.is_aanrader]

    if met_waardering:
        console.print(f"\n[dim]{len(met_waardering)} tips met waardering, {len(aanraders)} aanraders (4+ ballen)[/dim]")

    table = Table(
        title="Recente NRC Cultuur & Boeken Tips",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )

    table.add_column("Cat", style="cyan", width=8)
    table.add_column("NRC", style="yellow", width=7)
    table.add_column("Titel", style="white", width=40)
    table.add_column("Genres", style="green", width=18)
    table.add_column("Datum", style="yellow", width=10)

    for tip in tips[:max_items]:
        cat = tip.categorie[:7]

        # NRC waardering als ballen
        if tip.waardering:
            ballen = "●" * tip.waardering + "○" * (5 - tip.waardering)
        else:
            ballen = "[dim]-[/dim]"

        titel = tip.titel[:38] + "..." if len(tip.titel) > 40 else tip.titel

        # Highlight aanraders
        if tip.is_aanrader:
            titel = f"[bold]{titel}[/bold]"

        genres = ", ".join(tip.genres[:2]) if tip.genres else "-"
        datum = tip.publicatiedatum.strftime("%d %b")

        table.add_row(cat, ballen, titel, genres, datum)

    console.print(table)


def main():
    """Hoofdfunctie voor de CLI."""
    parser = argparse.ArgumentParser(
        description="Cultuuroverzicht - NRC tips matcher voor regio Haarlem/Hoofddorp",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voorbeelden:
  cultuuroverzicht                    # Toon gematchte NRC tips
  cultuuroverzicht --aanraders        # Alleen 4+ ballen tips
  cultuuroverzicht --topkeuzes        # Highlight beste matches
  cultuuroverzicht --agenda           # Toon volledige lokale agenda
  cultuuroverzicht --tips             # Toon alleen NRC tips
  cultuuroverzicht --zoek "jazz"      # Zoek in tips en evenementen
  cultuuroverzicht --dagen 14         # Bekijk komende 2 weken
  cultuuroverzicht --min-ballen 4     # Alleen tips met 4+ ballen
        """,
    )

    parser.add_argument(
        "--agenda", "-a",
        action="store_true",
        help="Toon volledige lokale agenda",
    )
    parser.add_argument(
        "--tips", "-t",
        action="store_true",
        help="Toon alleen NRC tips",
    )
    parser.add_argument(
        "--aanraders",
        action="store_true",
        help="Toon alleen NRC aanraders (4+ ballen)",
    )
    parser.add_argument(
        "--topkeuzes",
        action="store_true",
        help="Highlight topkeuzes (hoge match + hoge waardering)",
    )
    parser.add_argument(
        "--min-ballen",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Minimum NRC waardering (1-5 ballen)",
    )
    parser.add_argument(
        "--zoek", "-z",
        type=str,
        help="Zoekterm voor filteren",
    )
    parser.add_argument(
        "--dagen", "-d",
        type=int,
        default=30,
        help="Aantal dagen vooruit (default: 30)",
    )
    parser.add_argument(
        "--min-score", "-m",
        type=float,
        default=0.5,
        help="Minimum match score (0.0-1.0, default: 0.5)",
    )
    parser.add_argument(
        "--alleen-beschikbaar",
        action="store_true",
        help="Verberg uitverkochte evenementen",
    )
    parser.add_argument(
        "--sorteer",
        choices=["prioriteit", "datum", "waardering"],
        default="prioriteit",
        help="Sorteer matches op: prioriteit, datum, of waardering",
    )
    parser.add_argument(
        "--max", "-n",
        type=int,
        default=25,
        help="Maximum aantal items om te tonen",
    )

    args = parser.parse_args()

    # Header
    console.print(Panel.fit(
        "[bold]Cultuuroverzicht[/bold]\n"
        "[dim]NRC tips voor regio Haarlem/Hoofddorp[/dim]",
        border_style="blue",
    ))
    console.print()

    # Laad data
    tips = laad_nrc_tips()
    evenementen = laad_lokale_evenementen(
        dagen_vooruit=args.dagen,
        alleen_beschikbaar=args.alleen_beschikbaar,
    )

    # Filter op zoekterm indien opgegeven
    if args.zoek:
        zoek = args.zoek.lower()
        tips = [
            t for t in tips
            if zoek in t.titel.lower()
            or zoek in t.beschrijving.lower()
            or any(zoek in g.lower() for g in t.genres)
        ]
        evenementen = [
            e for e in evenementen
            if zoek in e.titel.lower()
            or zoek in e.beschrijving.lower()
            or zoek in e.genre.lower()
        ]
        console.print(f"\n[dim]Gefilterd op '{args.zoek}': {len(tips)} tips, {len(evenementen)} evenementen[/dim]")

    console.print()

    # Toon resultaten
    if args.tips:
        # Filter tips indien nodig
        gefilterde_tips = tips
        if args.aanraders:
            gefilterde_tips = [t for t in tips if t.is_aanrader]
        if args.min_ballen:
            gefilterde_tips = [t for t in gefilterde_tips if t.waardering and t.waardering >= args.min_ballen]
        toon_tips(gefilterde_tips, max_items=args.max)
    elif args.agenda:
        toon_agenda(evenementen, max_items=args.max)
    else:
        # Default: toon matches
        matcher = Matcher(
            min_score=args.min_score,
            alleen_aanraders=args.aanraders,
            min_waardering=args.min_ballen,
        )
        result = matcher.match(tips, evenementen)

        # Sorteer volgens voorkeur
        if args.sorteer == "datum":
            result.sorteer_op_datum()
        elif args.sorteer == "waardering":
            result.sorteer_op_waardering()
        # Default is al prioriteit

        toon_matches(result, max_items=args.max, toon_topkeuzes=args.topkeuzes)

        if result.match_percentage > 0:
            console.print(
                f"\n[dim]Match rate: {result.match_percentage:.0%} van NRC tips gevonden in lokale agenda's[/dim]"
            )

        # Toon aantal aanraders in resultaat
        if result.aanraders:
            console.print(f"[dim]Aanraders in regio: {len(result.aanraders)}[/dim]")


if __name__ == "__main__":
    main()

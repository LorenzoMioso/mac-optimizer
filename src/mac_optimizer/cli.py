"""
cli.py - Entry point da riga di comando (CLI) e dispatcher per TUI o modalità headless.
"""

import os
import sys
import argparse
from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from mac_optimizer.models import ModuleDef, CleanResult
from mac_optimizer.registry import create_all_modules
from mac_optimizer.config import load_config, apply_saved_config_to_modules, save_module_selections
from mac_optimizer.utils import format_bytes, get_disk_free_info
from mac_optimizer.tui.app import MacOptimizerApp

console = Console()


def print_modules_table(modules: List[ModuleDef]) -> None:
    """Stampa l'elenco dei moduli in una tabella formattata con Rich."""
    table = Table(title="Moduli di Pulizia Disponibili per macOS", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", width=18)
    table.add_column("Rischio", width=12)
    table.add_column("Stato", width=12)
    table.add_column("Nome & Descrizione", style="white")

    for m in modules:
        stat_str = "[bold green]Attivo [✔][/]" if m.selected else "[dim]Disattivo [ ][/]"
        if m.risk_level == "caution":
            risk_str = "[bold yellow]Attenzione[/]"
        elif m.risk_level == "recommended":
            risk_str = "[bold cyan]Consigliato[/]"
        else:
            risk_str = "[bold green]Sicuro[/]"

        desc_content = f"[bold]{m.name}[/]\n[dim]↳ {m.description}[/]"
        table.add_row(m.id, risk_str, stat_str, desc_content)

    console.print(table)


def run_cli_cleaning(modules: List[ModuleDef], dry_run: bool) -> None:
    """Esegue la pulizia dei moduli selezionati in modalità CLI / headless."""
    mode_text = "[bold yellow]🔍 MODALITÀ DRY-RUN (Simulazione - Nessun file verrà modificato)[/]" if dry_run else "[bold green]⚡ MODALITÀ ESECUZIONE REALE[/]"
    disk = get_disk_free_info()
    disk_line = f"Disco: [bold cyan]{disk['free']}[/] liberi su {disk['total']} ({disk['percent']} usato)"

    console.print(Panel(f"{mode_text}\n{disk_line}", title="🧹 Mac Developer Cleaner & Optimizer", expand=False))

    total_freed = 0
    total_items = 0

    for idx, m in enumerate(modules, 1):
        console.print(f"\n[bold cyan]▶ [{idx}/{len(modules)}] {m.name}[/]...")
        try:
            res: CleanResult = m.clean_func(dry_run)
            total_freed += res.freed_bytes
            total_items += res.items_count
            for det in res.details:
                console.print(f"   [dim]•[/] {det}")
        except Exception as e:
            console.print(f"   [bold red]❌ Errore durante l'esecuzione del modulo {m.id}: {e}[/]")

    summary_title = "Spazio recuperabile stimato" if dry_run else "Spazio totale liberato"
    console.print(f"\n[bold green]{'=' * 60}[/]")
    console.print(f" 💾 {summary_title}: [bold cyan]{format_bytes(total_freed)}[/]")
    console.print(f"[bold green]{'=' * 60}[/]\n")

    if dry_run:
        console.print("[dim]ℹ️  Per applicare realmente questa pulizia sul sistema, avvia:[/]")
        console.print("    [bold yellow]./clean_mac.py --yes[/]\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mac Developer Optimizer & Cleaner - Pulizia profonda e manutenzione macOS per sviluppatori."
    )
    parser.add_argument("--dry-run", action="store_true", help="Forza la modalità simulazione (nessun file eliminato).")
    parser.add_argument("-y", "--yes", action="store_true", help="Esegui realmente la pulizia senza chiedere conferme.")
    parser.add_argument("--cli", action="store_true", help="Forza la modalità CLI (senza interfaccia Terminal UI).")
    parser.add_argument("--tui", action="store_true", help="Forza l'avvio della Terminal UI interattiva.")
    parser.add_argument("--only", type=str, help="Esegui solo specifici ID di moduli (separati da virgola).")
    parser.add_argument("--skip", type=str, help="Salta specifici ID di moduli (separati da virgola).")
    parser.add_argument("--list", action="store_true", help="Elenca tutti i moduli di pulizia disponibili e termina.")
    parser.add_argument("--purge-ram", action="store_true", help="Forza il purge della cache RAM al termine.")

    args = parser.parse_args()

    # Inizializza i moduli e carica la configurazione persistente
    all_modules = create_all_modules()
    saved_config = load_config()
    apply_saved_config_to_modules(all_modules, saved_config)

    # Determina stato dry-run
    saved_dry_run = saved_config.get("dry_run", True)
    if args.dry_run:
        dry_run = True
    elif args.yes:
        dry_run = False
    else:
        dry_run = saved_dry_run

    # Comando --list
    if args.list:
        print_modules_table(all_modules)
        return

    # Filtri --only e --skip
    if args.only:
        req = [k.strip().lower() for k in args.only.split(",") if k.strip()]
        for m in all_modules:
            m.selected = (m.id in req)
    if args.skip:
        to_skip = [k.strip().lower() for k in args.skip.split(",") if k.strip()]
        for m in all_modules:
            if m.id in to_skip:
                m.selected = False

    # Scelta modalità (TUI vs CLI)
    use_tui = False
    if args.tui:
        use_tui = True
    elif args.cli or args.yes or args.only or args.skip or not sys.stdin.isatty():
        use_tui = False
    else:
        use_tui = True

    if use_tui:
        app = MacOptimizerApp(all_modules, dry_run=dry_run)
        app.run()
    else:
        selected = [m for m in all_modules if m.selected]
        if not selected:
            console.print("[yellow]Nessun modulo selezionato per l'esecuzione.[/]")
            return
        run_cli_cleaning(selected, dry_run=dry_run)


if __name__ == "__main__":
    main()

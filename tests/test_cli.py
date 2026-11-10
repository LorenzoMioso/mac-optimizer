"""
Test per le funzioni CLI in mac_optimizer.cli.
"""

from mac_optimizer.registry import create_all_modules
from mac_optimizer.cli import print_modules_table, run_cli_cleaning


def test_print_modules_table():
    modules = create_all_modules()
    # Verifica che la stampa della tabella non sollevi eccezioni
    print_modules_table(modules)


def test_run_cli_cleaning_dry_run():
    modules = create_all_modules()
    # Seleziona solo 2 moduli sicuri per il test
    test_mods = [m for m in modules if m.id in ("trash", "logs")]
    run_cli_cleaning(test_mods, dry_run=True)

"""
Test headless per l'applicazione Terminal UI Textual in mac_optimizer.tui.app.
"""

import asyncio
from mac_optimizer.registry import create_all_modules
from mac_optimizer.tui.app import MacOptimizerApp
from textual.widgets import SelectionList


def test_tui_app_navigation_and_bindings():
    async def _run():
        modules = create_all_modules()
        app = MacOptimizerApp(modules, dry_run=True)
        app._stop_scan = True  # Disabilita worker in background durante il test unitario

        async with app.run_test() as pilot:
            sl = app.query_one(SelectionList)
            assert sl.option_count >= 20

            # Verifica stato iniziale dry run
            assert app.dry_run is True

            # Testa toggle Dry-Run con 'd'
            await pilot.press("d")
            assert app.dry_run is False

            await pilot.press("d")
            assert app.dry_run is True

            # Testa deselezione totale con 'n'
            await pilot.press("n")
            assert len(sl.selected) == 0

            # Testa selezione tutti con 'a'
            await pilot.press("a")
            assert len(sl.selected) > 0

    asyncio.run(_run())

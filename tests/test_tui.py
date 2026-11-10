"""
Test headless per l'applicazione Terminal UI Textual in mac_optimizer.tui.app.
"""

import asyncio
from mac_optimizer.registry import create_all_modules
from mac_optimizer.tui.app import MacOptimizerApp
from textual.widgets import OptionList


def test_tui_app_navigation_and_bindings():
    async def _run():
        modules = create_all_modules()
        app = MacOptimizerApp(modules, dry_run=True)
        app._stop_scan = True  # Disabilita worker in background durante il test unitario

        async with app.run_test() as pilot:
            ol = app.query_one(OptionList)
            assert ol.option_count >= 20

            # Testa pressione frecce su e giù per verificare l'evento on_option_list_option_highlighted
            await pilot.press("down")
            await pilot.press("down")
            await pilot.press("up")

            # Verifica stato iniziale dry run
            assert app.dry_run is True

            # Testa toggle Dry-Run con 'd'
            await pilot.press("d")
            assert app.dry_run is False

            await pilot.press("d")
            assert app.dry_run is True

            # Testa barra spaziatrice per commutare elemento
            init_selected = modules[0].selected
            await pilot.press("space")

            # Testa deselezione totale con 'n'
            await pilot.press("n")
            assert sum(1 for m in app.modules if m.selected) == 0

            # Testa selezione tutti con 'a'
            await pilot.press("a")
            assert sum(1 for m in app.modules if m.selected) > 0

    asyncio.run(_run())

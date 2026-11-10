"""
Test headless per l'applicazione Terminal UI Textual in mac_optimizer.tui.app.
"""

import asyncio
from mac_optimizer.registry import create_all_modules
from mac_optimizer.tui.app import MacOptimizerApp
from mac_optimizer.tui.screens import ExecutionScreen
from textual.widgets import OptionList


def test_tui_app_navigation_and_bindings(monkeypatch, tmp_path):
    # Isola la persistenza delle preferenze su una cartella temporanea per non sporcare la config reale
    fake_config = str(tmp_path / "config.json")
    saved_state = {}

    def mock_save(modules, dry_run):
        saved_state["selected_modules"] = {m.id: m.selected for m in modules}
        saved_state["dry_run"] = dry_run

    monkeypatch.setattr("mac_optimizer.tui.app.save_module_selections", mock_save)

    async def _run():
        modules = create_all_modules()
        for m in modules:
            m.selected = m.default_selected

        app = MacOptimizerApp(modules, dry_run=True)
        app._stop_scan = True  # Disabilita worker in background durante il test unitario

        async with app.run_test() as pilot:
            ol = app.query_one(OptionList)
            assert ol.option_count >= 20

            # 1. Testa navigazione con frecce su e giù
            await pilot.press("down")
            await pilot.press("down")
            await pilot.press("up")

            # 2. Testa stato iniziale dry-run e toggle con 'd'
            assert app.dry_run is True
            await pilot.press("d")
            assert app.dry_run is False
            assert saved_state.get("dry_run") is False
            await pilot.press("d")
            assert app.dry_run is True

            # 3. Testa barra spaziatrice per commutare il modulo evidenziato
            idx = ol.highlighted
            opt = ol.get_option_at_index(idx)
            mod = app.modules_by_id[opt.id]
            prev_sel = mod.selected
            await pilot.press("space")
            assert mod.selected is not prev_sel
            assert saved_state["selected_modules"][mod.id] == mod.selected

            # 4. Testa deselezione totale con 'n' e aggiornamento contatori
            await pilot.press("n")
            assert sum(1 for m in app.modules if m.selected) == 0
            stats_lbl = app.query_one("#selection_stats")
            top_lbl = app.query_one("#selection_top_label")
            assert "0/" in str(stats_lbl.render())
            assert "0/" in str(top_lbl.render())

            # 5. Testa selezione tutti con 'a' e aggiornamento contatori
            await pilot.press("a")
            sel_count = sum(1 for m in app.modules if m.selected)
            assert sel_count > 0
            assert f"{sel_count}/" in str(stats_lbl.render())
            assert f"{sel_count}/" in str(top_lbl.render())

            # 6. Testa tasto INVIO per avviare l'esecuzione della pulizia
            await pilot.press("enter")
            assert isinstance(app.screen, ExecutionScreen)
            exec_screen = app.screen
            
            # Attende che il worker completi l'esecuzione in dry-run
            while not exec_screen.completed:
                await pilot.pause(0.05)
            
            assert exec_screen.completed is True
            # Esci dallo schermo di esecuzione con Invio
            await pilot.press("enter")
            assert not isinstance(app.screen, ExecutionScreen)

    asyncio.run(_run())

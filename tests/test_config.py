"""
Test per la gestione della configurazione e persistenza in mac_optimizer.config.
"""

from mac_optimizer.models import ModuleDef, CleanResult
from mac_optimizer.config import (
    load_config,
    save_config,
    save_module_selections,
    apply_saved_config_to_modules,
)


def dummy_scan() -> int:
    return 100


def dummy_clean(dry_run: bool) -> CleanResult:
    return CleanResult("Dummy", freed_bytes=100)


def test_load_save_config(tmp_path):
    config_file = str(tmp_path / "test_config.json")
    assert load_config(config_file) == {}

    data = {"dry_run": False, "theme": "dark"}
    save_config(data, config_file)

    loaded = load_config(config_file)
    assert loaded["dry_run"] is False
    assert loaded["theme"] == "dark"


def test_save_module_selections(tmp_path):
    config_file = str(tmp_path / "test_config.json")
    m1 = ModuleDef("mod1", "Mod 1", "Cat", "Desc", True, "safe", dummy_scan, dummy_clean, selected=True)
    m2 = ModuleDef("mod2", "Mod 2", "Cat", "Desc", False, "caution", dummy_scan, dummy_clean, selected=False)

    save_module_selections([m1, m2], dry_run=True, config_path=config_file)

    loaded = load_config(config_file)
    assert loaded["dry_run"] is True
    assert loaded["selected_modules"] == {"mod1": True, "mod2": False}


def test_apply_saved_config_to_modules():
    m1 = ModuleDef("mod1", "Mod 1", "Cat", "Desc", True, "safe", dummy_scan, dummy_clean, selected=True)
    m2 = ModuleDef("mod2", "Mod 2", "Cat", "Desc", True, "safe", dummy_scan, dummy_clean, selected=True)
    m3 = ModuleDef("mod3", "Mod 3", "Cat", "Desc", False, "caution", dummy_scan, dummy_clean, selected=False)

    saved_config = {
        "selected_modules": {
            "mod1": False,
            "mod2": True,
        }
    }

    apply_saved_config_to_modules([m1, m2, m3], saved_config)
    assert m1.selected is False  # Aggiornato da config salvata
    assert m2.selected is True   # Aggiornato da config salvata
    assert m3.selected is False  # Fallback a default_selected

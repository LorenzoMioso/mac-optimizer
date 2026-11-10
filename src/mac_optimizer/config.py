"""
config.py - Gestione persistenza selezioni e preferenze utente.
"""

import os
import json
from typing import Dict, List, Any
from mac_optimizer.models import ModuleDef

CONFIG_DIR = os.path.expanduser("~/.config/mac-optimizer")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def load_config(config_path: str = CONFIG_FILE) -> Dict[str, Any]:
    """Carica la configurazione salvata (selezioni e preferenze)."""
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(config_data: Dict[str, Any], config_path: str = CONFIG_FILE) -> None:
    """Salva le preferenze utente nel file JSON di configurazione."""
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def save_module_selections(modules: List[ModuleDef], dry_run: bool, config_path: str = CONFIG_FILE) -> None:
    """Salva la mappa modulo->selezionato e lo stato dry_run."""
    current = load_config(config_path)
    current["selected_modules"] = {m.id: m.selected for m in modules}
    current["dry_run"] = dry_run
    save_config(current, config_path)


def apply_saved_config_to_modules(modules: List[ModuleDef], saved_config: Dict[str, Any]) -> None:
    """Applica le selezioni salvate in precedenza; se nuova, usa default."""
    saved_selections = saved_config.get("selected_modules", {})
    for m in modules:
        if m.id in saved_selections:
            m.selected = bool(saved_selections[m.id])
        else:
            m.selected = m.default_selected

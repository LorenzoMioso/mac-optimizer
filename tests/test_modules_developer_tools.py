"""
Test per i moduli di strumenti per sviluppatori in mac_optimizer.modules.developer_tools.
"""

import os
from mac_optimizer.modules.developer_tools import (
    scan_vscode_extensions_cache,
    clean_vscode_extensions_cache,
    scan_docker_system_prune,
    clean_docker_system_prune,
)


def test_vscode_extensions_deduplication(tmp_path, monkeypatch):
    """Verifica che le versioni precedenti di un'estensione vengano identificate come obsolete."""
    ext_dir = tmp_path / "extensions"
    ext_dir.mkdir()

    # Crea due versioni della stessa estensione e una versione singola di un'altra
    (ext_dir / "ms-python.python-2026.1.0").mkdir()
    (ext_dir / "ms-python.python-2026.1.0" / "package.json").write_text("old")
    (ext_dir / "ms-python.python-2026.2.0").mkdir()
    (ext_dir / "ms-python.python-2026.2.0" / "package.json").write_text("new")
    (ext_dir / "esbenp.prettier-vscode-10.0.0").mkdir()

    monkeypatch.setattr(os.path, "expanduser", lambda p: str(ext_dir) if "extensions" in p else p)

    res_dry = clean_vscode_extensions_cache(dry_run=True)
    assert res_dry.items_count == 1
    assert any("ms-python.python-2026.1.0" in d for d in res_dry.details)

    res_real = clean_vscode_extensions_cache(dry_run=False)
    assert res_real.items_count == 1
    assert not (ext_dir / "ms-python.python-2026.1.0").exists()
    assert (ext_dir / "ms-python.python-2026.2.0").exists()
    assert (ext_dir / "esbenp.prettier-vscode-10.0.0").exists()


def test_docker_system_prune():
    res = clean_docker_system_prune(dry_run=True)
    assert res.name == "Docker System Prune"

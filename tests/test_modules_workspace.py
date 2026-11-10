"""
Test per il modulo di pulizia artefatti nei workspace in mac_optimizer.modules.workspace.
"""

from mac_optimizer.modules.workspace import (
    scan_workspace_builds,
    clean_workspace_builds,
)


def test_workspace_builds_scan_and_clean(tmp_path):
    root = tmp_path / "GitHub"
    root.mkdir()

    # Progetto 1: Flutter project con build e .dart_tool
    proj1 = root / "pulsarApp"
    proj1.mkdir()
    (proj1 / "pubspec.yaml").write_text("name: pulsarApp")
    (proj1 / "build").mkdir()
    (proj1 / "build" / "app.apk").write_text("binary data" * 100)
    (proj1 / ".dart_tool").mkdir()
    (proj1 / ".dart_tool" / "package_config.json").write_text("{}" * 50)

    # Progetto 2: Progetto senza cartelle build
    proj2 = root / "cleanRepo"
    proj2.mkdir()
    (proj2 / ".git").mkdir()
    (proj2 / "main.py").write_text("print('hello')")

    # Progetto 3: Directory non-progetto (senza marker git/pubspec/package.json)
    not_a_proj = root / "randomDir"
    not_a_proj.mkdir()
    (not_a_proj / "build").mkdir()
    (not_a_proj / "build" / "temp.txt").write_text("should be ignored")

    # Scansione
    total_sz = scan_workspace_builds(roots=[str(root)])
    assert total_sz > 0

    # Dry-run
    res_dry = clean_workspace_builds(dry_run=True, roots=[str(root)])
    assert res_dry.freed_bytes == total_sz
    assert res_dry.items_count == 2
    assert (proj1 / "build" / "app.apk").exists()

    # Esecuzione reale
    res_real = clean_workspace_builds(dry_run=False, roots=[str(root)])
    assert res_real.freed_bytes == total_sz
    assert not (proj1 / "build" / "app.apk").exists()
    assert not (proj1 / ".dart_tool" / "package_config.json").exists()

    # Verifica che la directory del progetto non-progetto non sia stata toccata
    assert (not_a_proj / "build" / "temp.txt").exists()
    # Verifica che i file sorgenti del progetto siano intatti
    assert (proj1 / "pubspec.yaml").exists()
    assert (proj2 / "main.py").exists()

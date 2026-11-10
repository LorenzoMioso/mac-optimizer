"""
Test per i moduli gestori di pacchetti in mac_optimizer.modules.package_managers.
"""

from mac_optimizer.modules.package_managers import (
    scan_swiftpm_cache, clean_swiftpm_cache,
    scan_homebrew_cache, clean_homebrew_cache,
    scan_cocoapods_cache, clean_cocoapods_cache,
    scan_node_npm_caches, clean_node_npm_caches,
    scan_gradle_android_caches, clean_gradle_android_caches,
    scan_python_pip_cache, clean_python_pip_cache,
    scan_flutter_cache, clean_flutter_cache,
)


def test_package_managers_dry_run(monkeypatch):
    # Mock rapido per comandi esterni (brew, pod, npm, pip) per velocizzare i test unitari
    def mock_run_cmd(cmd, timeout=None):
        if "which" in cmd:
            return 0, "/usr/bin/mock", ""
        if "brew" in cmd:
            return 0, "Would remove 2 old bottles", ""
        return 0, "", ""

    monkeypatch.setattr("mac_optimizer.modules.package_managers.run_cmd", mock_run_cmd)

    # Verifica che tutti i moduli di package managers rispondano correttamente a dry_run=True
    modules_clean_funcs = [
        clean_swiftpm_cache,
        clean_homebrew_cache,
        clean_cocoapods_cache,
        clean_node_npm_caches,
        clean_gradle_android_caches,
        clean_python_pip_cache,
        clean_flutter_cache,
    ]

    for clean_fn in modules_clean_funcs:
        res = clean_fn(dry_run=True)
        assert res.name
        assert isinstance(res.freed_bytes, int)
        assert isinstance(res.details, list)

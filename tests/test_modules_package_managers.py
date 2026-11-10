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
    scan_dart_analysis_cache, clean_dart_analysis_cache,
    scan_pub_hosted_cache, clean_pub_hosted_cache,
    scan_gradle_wrappers, clean_gradle_wrappers,
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
        clean_dart_analysis_cache,
        clean_pub_hosted_cache,
        clean_gradle_wrappers,
    ]

    for clean_fn in modules_clean_funcs:
        res = clean_fn(dry_run=True)
        assert res.name
        assert isinstance(res.freed_bytes, int)
        assert isinstance(res.details, list)


def test_dart_analysis_and_gradle_wrappers_real_clean(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_dart = fake_home / ".dartServer" / ".analysis-driver"
    fake_dart.mkdir(parents=True)
    (fake_dart / "cache_file.bin").write_text("dummy cache")

    fake_gradle = fake_home / ".gradle" / "wrapper" / "dists"
    fake_gradle.mkdir(parents=True)
    (fake_gradle / "gradle-dist.zip").write_text("gradle zip")

    def mock_expanduser(p):
        if p.startswith("~/.dartServer"):
            return str(fake_home / p.replace("~/", ""))
        if p.startswith("~/.gradle"):
            return str(fake_home / p.replace("~/", ""))
        return p

    monkeypatch.setattr("os.path.expanduser", mock_expanduser)

    res_dart = clean_dart_analysis_cache(dry_run=False)
    assert res_dart.freed_bytes > 0
    assert not (fake_dart / "cache_file.bin").exists()

    res_gradle = clean_gradle_wrappers(dry_run=False)
    assert res_gradle.freed_bytes > 0
    assert not (fake_gradle / "gradle-dist.zip").exists()

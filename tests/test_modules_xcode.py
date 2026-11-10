"""
Test per i moduli di pulizia Xcode in mac_optimizer.modules.xcode.
"""

import os
import shutil
from mac_optimizer.modules.xcode import (
    scan_xcode_deriveddata, clean_xcode_deriveddata,
    scan_xcode_archives, clean_xcode_archives,
    scan_xcode_devicesupport, clean_xcode_devicesupport,
    scan_xcode_ide_caches, clean_xcode_ide_caches,
)


def test_clean_xcode_deriveddata_dry_run():
    res = clean_xcode_deriveddata(dry_run=True)
    assert res.name == "Xcode DerivedData"
    assert isinstance(res.freed_bytes, int)
    assert len(res.details) > 0


def test_clean_xcode_archives_all_deleted(tmp_path, monkeypatch):
    """Verifica che TUTTI gli archivi .xcarchive vengano eliminati senza preservarne storici."""
    fake_archives = tmp_path / "Archives" / "2026-11-10"
    fake_archives.mkdir(parents=True)
    
    # Crea 3 finti archivi .xcarchive
    for i in range(1, 4):
        arch = fake_archives / f"App_v{i}.xcarchive"
        arch.mkdir()
        (arch / "Info.plist").write_text("dummy plist")

    monkeypatch.setattr(os.path, "expanduser", lambda p: str(tmp_path / "Archives") if "Archives" in p else p)

    res_dry = clean_xcode_archives(dry_run=True)
    assert res_dry.items_count == 3
    assert any("[Simulazione] Da eliminare:" in d for d in res_dry.details)

    res_real = clean_xcode_archives(dry_run=False)
    assert res_real.items_count == 3
    # Verifica che tutti gli archivi siano stati realmente rimossi dal filesystem
    remaining = [d for d in os.listdir(fake_archives) if d.endswith(".xcarchive")] if fake_archives.exists() else []
    assert len(remaining) == 0


def test_clean_xcode_devicesupport_dry_run():
    res = clean_xcode_devicesupport(dry_run=True)
    assert res.name == "Xcode iOS DeviceSupport"
    assert isinstance(res.freed_bytes, int)


def test_clean_xcode_ide_caches_dry_run():
    res = clean_xcode_ide_caches(dry_run=True)
    assert res.name == "Xcode IDE Caches & Documentazione"
    assert isinstance(res.freed_bytes, int)

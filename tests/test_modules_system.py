"""
Test per i moduli di sistema macOS in mac_optimizer.modules.system.
"""

from mac_optimizer.modules.system import (
    scan_trash_can, clean_trash_can,
    scan_system_user_logs, clean_system_user_logs,
    scan_time_machine_snapshots, clean_time_machine_snapshots,
    scan_kill_gradle_daemons, clean_kill_gradle_daemons,
    scan_ram_purge, clean_ram_purge,
)


def test_trash_can():
    res = clean_trash_can(dry_run=True)
    assert res.name == "Cestino macOS (~/.Trash)"


def test_system_logs():
    res = clean_system_user_logs(dry_run=True)
    assert res.name == "Log Utente & Crash Reports"
    assert isinstance(res.freed_bytes, int)


def test_time_machine_snapshots():
    res = clean_time_machine_snapshots(dry_run=True)
    assert res.name == "Time Machine Local Snapshots"


def test_kill_gradle_daemons():
    res = clean_kill_gradle_daemons(dry_run=True)
    assert res.name == "Termina Demoni Gradle/Kotlin in RAM"


def test_ram_purge():
    res = clean_ram_purge(dry_run=True)
    assert res.name == "macOS Purge RAM (svuota cache inattiva)"
    assert any("purge" in d for d in res.details)

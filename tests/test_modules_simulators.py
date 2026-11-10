"""
Test per il modulo di gestione e pulizia intelligente simulatori iOS.
"""

import json
from mac_optimizer.modules.simulators import (
    get_simulators_analysis,
    scan_old_simulators,
    clean_old_simulators,
    clean_simulators_erase_all,
)


def test_simulators_analysis_mock(monkeypatch):
    """Verifica l'identificazione della versione più recente da mantenere e delle obsolete da rimuovere."""
    fake_runtimes = {
        "UUID_NEW": {
            "version": "27.0",
            "platformIdentifier": "com.apple.platform.iphonesimulator",
            "runtimeIdentifier": "com.apple.CoreSimulator.SimRuntime.iOS-27-0",
            "sizeBytes": 8000000000,
        },
        "UUID_OLD": {
            "version": "26.5",
            "platformIdentifier": "com.apple.platform.iphonesimulator",
            "runtimeIdentifier": "com.apple.CoreSimulator.SimRuntime.iOS-26-5",
            "sizeBytes": 7000000000,
        }
    }
    fake_devices = {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-5": [
                {"name": "iPhone 16 Pro", "udid": "DEV_OLD_1", "dataPathSize": 2000000000, "state": "Shutdown"},
                {"name": "iPhone 16", "udid": "DEV_OLD_2", "dataPathSize": 1000000000, "state": "Shutdown"},
            ],
            "com.apple.CoreSimulator.SimRuntime.iOS-27-0": [
                {"name": "iPhone 17 Pro", "udid": "DEV_NEW_1", "dataPathSize": 5000000000, "state": "Shutdown"},
            ]
        }
    }

    def mock_run_cmd(cmd, timeout=None):
        if "which" in cmd:
            return 0, "/usr/bin/xcrun", ""
        if "runtime" in cmd and "list" in cmd:
            return 0, json.dumps(fake_runtimes), ""
        if "list" in cmd and "devices" in cmd:
            return 0, json.dumps(fake_devices), ""
        return 0, "", ""

    monkeypatch.setattr("mac_optimizer.modules.simulators.run_cmd", mock_run_cmd)

    analysis = get_simulators_analysis(force_refresh=True)
    assert analysis["available"] is True
    assert "iOS 27.0" in analysis["kept_summary"]
    assert "iOS 26.5" in analysis["old_summary"]
    assert len(analysis["kept_runtimes"]) == 1
    assert analysis["kept_runtimes"][0]["version"] == "27.0"
    assert len(analysis["older_runtimes"]) == 1
    assert analysis["older_runtimes"][0]["version"] == "26.5"
    assert len(analysis["deleted_devices"]) == 2
    # 7 GB (runtime) + 3 GB (dispositivi) = 10 GB
    assert analysis["runtimes_bytes"] == 7000000000
    assert analysis["devices_bytes"] == 3000000000
    assert analysis["total_reclaimable_bytes"] >= 10000000000


def test_clean_old_simulators_dry_run(monkeypatch):
    fake_runtimes = {
        "UUID_NEW": {
            "version": "27.0",
            "platformIdentifier": "com.apple.platform.iphonesimulator",
            "runtimeIdentifier": "com.apple.CoreSimulator.SimRuntime.iOS-27-0",
            "sizeBytes": 8000000000,
        },
        "UUID_OLD": {
            "version": "26.5",
            "platformIdentifier": "com.apple.platform.iphonesimulator",
            "runtimeIdentifier": "com.apple.CoreSimulator.SimRuntime.iOS-26-5",
            "sizeBytes": 7000000000,
        }
    }
    fake_devices = {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-5": [
                {"name": "Pulsar Tests", "udid": "DEV_OLD_1", "dataPathSize": 2000000000, "state": "Shutdown"},
            ]
        }
    }

    def mock_run_cmd(cmd, timeout=None):
        if "which" in cmd:
            return 0, "/usr/bin/xcrun", ""
        if "runtime" in cmd and "list" in cmd:
            return 0, json.dumps(fake_runtimes), ""
        if "list" in cmd and "devices" in cmd:
            return 0, json.dumps(fake_devices), ""
        return 0, "", ""

    monkeypatch.setattr("mac_optimizer.modules.simulators.run_cmd", mock_run_cmd)
    monkeypatch.setattr("mac_optimizer.modules.simulators._SIM_ANALYSIS_CACHE", None)

    res = clean_old_simulators(dry_run=True)
    assert "Mantiene iOS 27.0" in res.name
    assert any("Versione che verrà mantenuta: iOS 27.0" in d for d in res.details)
    assert any("iOS 26.5" in d for d in res.details)
    assert any("Pulsar Tests" in d for d in res.details)


def test_clean_simulators_erase_all():
    res = clean_simulators_erase_all(dry_run=True)
    assert "Reset Totale" in res.name
    assert len(res.details) > 0

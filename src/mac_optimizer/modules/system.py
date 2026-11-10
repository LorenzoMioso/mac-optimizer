"""
modules/system.py - Moduli di manutenzione sistema macOS, Cestino, Log, Snapshots APFS e RAM Purge.
"""

import os
from mac_optimizer.models import CleanResult
from mac_optimizer.utils import run_cmd, fast_get_path_size, safe_remove_directory_contents, format_bytes


def scan_trash_can() -> int:
    return fast_get_path_size("~/.Trash", timeout=5)


def clean_trash_can(dry_run: bool) -> CleanResult:
    result = CleanResult("Cestino macOS (~/.Trash)")
    p = os.path.expanduser("~/.Trash")
    sz = fast_get_path_size(p, timeout=5)
    result.freed_bytes = sz
    if not os.path.exists(p) or not os.listdir(p):
        result.add_detail("Il Cestino è già completamente vuoto.")
        return result

    if dry_run:
        result.add_detail(f"[Simulazione] Spazio liberabile svuotando il Cestino: {format_bytes(sz)}")
    else:
        cnt, _ = safe_remove_directory_contents(p)
        result.items_count = cnt
        result.add_detail(f"Cestino utente svuotato ({format_bytes(sz)}).")
    return result


def scan_system_user_logs() -> int:
    total = fast_get_path_size("~/Library/Logs", timeout=5)
    total += fast_get_path_size("~/Library/Application Support/CrashReporter", timeout=5)
    return total


def clean_system_user_logs(dry_run: bool) -> CleanResult:
    result = CleanResult("Log Utente & Crash Reports")
    logs_p = os.path.expanduser("~/Library/Logs")
    crash_p = os.path.expanduser("~/Library/Application Support/CrashReporter")
    total_sz = fast_get_path_size(logs_p, timeout=5) + fast_get_path_size(crash_p, timeout=5)
    result.freed_bytes = total_sz
    if dry_run:
        result.add_detail(f"[Simulazione] File di log e crash report eliminabili: {format_bytes(total_sz)}")
    else:
        cnt1, _ = safe_remove_directory_contents(logs_p)
        cnt2, _ = safe_remove_directory_contents(crash_p)
        result.items_count = cnt1 + cnt2
        result.add_detail(f"File di log e crash dump rimossi ({format_bytes(total_sz)}).")
    return result


def scan_time_machine_snapshots() -> int:
    code, out, _ = run_cmd(["tmutil", "listlocalsnapshots", "/"], timeout=5)
    if code == 0:
        snaps = [l for l in out.splitlines() if "com.apple.TimeMachine" in l]
        return len(snaps)
    return 0


def clean_time_machine_snapshots(dry_run: bool) -> CleanResult:
    result = CleanResult("Time Machine Local Snapshots")
    code, out, _ = run_cmd(["tmutil", "listlocalsnapshots", "/"], timeout=5)
    snaps = [l.strip() for l in out.splitlines() if "com.apple.TimeMachine" in l]
    result.items_count = len(snaps)
    if not snaps:
        result.add_detail("Nessuno snapshot locale Time Machine attivo su disco.")
        return result

    result.add_detail(f"Rilevati {len(snaps)} snapshot locali APFS che bloccano spazio.")
    if dry_run:
        result.add_detail("[Simulazione] Gli snapshot locali verranno assottigliati per sbloccare spazio purgabile.")
    else:
        run_cmd(["tmutil", "thinlocalsnapshots", "/", "10000000000", "4"], timeout=20)
        result.add_detail("Snapshot locali APFS assottigliati con successo.")
    return result


def scan_kill_gradle_daemons() -> int:
    code, out, _ = run_cmd(["pgrep", "-f", "gradle-launcher"])
    pids = [p for p in out.splitlines() if p.strip()]
    return len(pids)


def clean_kill_gradle_daemons(dry_run: bool) -> CleanResult:
    result = CleanResult("Termina Demoni Gradle/Kotlin in RAM")
    code, out, _ = run_cmd(["pgrep", "-f", "gradle-launcher"])
    pids = [p.strip() for p in out.splitlines() if p.strip()]
    result.items_count = len(pids)
    if not pids:
        result.add_detail("Nessun demone Gradle o compiler Kotlin rimasto aperto in background.")
        return result

    if dry_run:
        result.add_detail(f"[Simulazione] Rilevati {len(pids)} processi demone Gradle in background da terminare.")
    else:
        run_cmd(["pkill", "-f", "gradle-launcher"])
        result.add_detail(f"Terminati {len(pids)} processi Gradle/Kotlin: RAM unificata liberata.")
    return result


def scan_ram_purge() -> int:
    return 0


def clean_ram_purge(dry_run: bool) -> CleanResult:
    result = CleanResult("macOS Purge RAM (svuota cache inattiva)")
    if dry_run:
        result.add_detail("[Simulazione] Il comando 'purge' rilascerà la memoria file-cache inattiva alla RAM fisica.")
    else:
        code, _, err = run_cmd(["purge"], timeout=10)
        if code == 0:
            result.add_detail("Comando purge eseguito: cache disco inattiva rilasciata alla RAM fisica.")
        else:
            result.add_detail(f"Nota: comando purge non completato: {err.strip() or 'permessi insufficienti'}")
    return result

#!/usr/bin/env python3
"""
clean_mac.py - Utility avanzata di pulizia, manutenzione e ottimizzazione disco/RAM per macOS.
Ottimizzato per Mac Apple Silicon (M1/M2/M3/M4 & Intel) e ambienti di sviluppo:
iOS, Xcode, Flutter, Android, Node/NPM, Docker, Homebrew, VS Code, Browser e Cache di Sistema.

Include una Terminal UI (TUI) interattiva con checkmark, navigazione con frecce,
selezione salvata per le esecuzioni successive, divisione in categorie e supporto Dry-Run.
"""

import os
import sys
import shutil
import subprocess
import argparse
import json
import re
import time
import threading
import concurrent.futures
import select
import termios
import tty
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Callable, Any

# ==============================================================================
# CONFIGURAZIONE E PERSISTENZA SELEZIONI
# ==============================================================================

CONFIG_DIR = os.path.expanduser("~/.config/mac-optimizer")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def load_config() -> Dict[str, Any]:
    """Carica la configurazione salvata (selezioni e preferenze)."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(selected_modules: Dict[str, bool], dry_run: bool):
    """Salva le selezioni dell'utente per le sessioni successive."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        data = {
            "selected_modules": selected_modules,
            "dry_run": dry_run,
            "last_updated": datetime.now().isoformat()
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# ==============================================================================
# COLORI E FORMATTAZIONE ANSI
# ==============================================================================

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'
    REVERSE = '\033[7m'

ANSI_REGEX = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

def visible_len(text: str) -> int:
    """Calcola la lunghezza visibile di una stringa escludendo i codici ANSI."""
    return len(ANSI_REGEX.sub('', text))

def fit_line(text: str, max_width: int) -> str:
    """Tronca una stringa con codici ANSI in modo che non superi la larghezza del terminale."""
    vlen = visible_len(text)
    if vlen <= max_width:
        return text
    # Se supera, tronca rimuovendo caratteri visibili in eccesso
    chars = []
    curr_vlen = 0
    in_ansi = False
    for ch in text:
        if ch == '\x1b':
            in_ansi = True
            chars.append(ch)
        elif in_ansi:
            chars.append(ch)
            if ch.isalpha():
                in_ansi = False
        else:
            if curr_vlen < max_width - 1:
                chars.append(ch)
                curr_vlen += 1
            else:
                break
    chars.append(Colors.RESET)
    return "".join(chars)

def colorize(text: str, color: str) -> str:
    if sys.stdout.isatty():
        return f"{color}{text}{Colors.RESET}"
    return text

def format_bytes(size_bytes: int) -> str:
    """Formatta i byte in formato leggibile (B, KB, MB, GB, TB)."""
    if size_bytes <= 0:
        return "0 B"
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    idx = 0
    val = float(size_bytes)
    while val >= 1024.0 and idx < len(units) - 1:
        val /= 1024.0
        idx += 1
    return f"{val:.1f} {units[idx]}"

def run_cmd(cmd: List[str], check: bool = False, timeout: int = 60) -> Tuple[int, str, str]:
    """Esegue un comando di sistema e restituisce exit code, stdout, stderr."""
    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=check,
            timeout=timeout
        )
        return res.returncode, res.stdout, res.stderr
    except FileNotFoundError:
        return 127, "", f"Comando non trovato: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"Timeout ({timeout}s) durante l'esecuzione di {cmd[0]}"
    except Exception as e:
        return 1, "", str(e)

def fast_get_path_size(path: str, timeout: int = 15) -> int:
    """Calcola rapidamente la dimensione in byte di un percorso usando du -sk."""
    expanded = os.path.expanduser(path)
    if not os.path.exists(expanded):
        return 0
    if os.path.isfile(expanded) or os.path.islink(expanded):
        try:
            return os.path.getsize(expanded)
        except OSError:
            return 0
    try:
        res = subprocess.run(
            ['du', '-sk', expanded],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        if res.returncode == 0 and res.stdout.strip():
            kb_str = res.stdout.strip().split()[0]
            if kb_str.isdigit():
                return int(kb_str) * 1024
    except Exception:
        pass

    total = 0
    try:
        for root, _, files in os.walk(expanded, followlinks=False):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    except Exception:
        pass
    return total

def safe_remove_directory_contents(dir_path: str) -> Tuple[int, int]:
    """Svuota il contenuto di una cartella senza cancellare la cartella principale."""
    expanded = os.path.expanduser(dir_path)
    if not os.path.isdir(expanded):
        return 0, 0
    items_count = 0
    freed_bytes = 0
    try:
        for entry in os.listdir(expanded):
            full_path = os.path.join(expanded, entry)
            try:
                sz = fast_get_path_size(full_path, timeout=5)
                if os.path.isdir(full_path) and not os.path.islink(full_path):
                    shutil.rmtree(full_path, ignore_errors=True)
                else:
                    os.remove(full_path)
                items_count += 1
                freed_bytes += sz
            except OSError:
                continue
    except OSError:
        pass
    return items_count, freed_bytes

def get_disk_usage_info() -> Dict[str, str]:
    """Restituisce informazioni sull'occupazione del disco principale macOS."""
    info = {"total": "N/D", "free": "N/D", "used": "N/D", "percent": "0%"}
    try:
        stat = os.statvfs("/")
        total_b = stat.f_blocks * stat.f_frsize
        free_b = stat.f_bavail * stat.f_frsize
        used_b = total_b - free_b
        pct = (used_b / total_b) * 100 if total_b > 0 else 0
        info["total"] = format_bytes(total_b)
        info["free"] = format_bytes(free_b)
        info["used"] = format_bytes(used_b)
        info["percent"] = f"{pct:.1f}%"
    except Exception:
        pass
    return info


# ==============================================================================
# MODELLO DATI MODULI DI PULIZIA
# ==============================================================================

class CleanResult:
    def __init__(self, name: str, freed_bytes: int = 0, items_count: int = 0, details: Optional[List[str]] = None):
        self.name = name
        self.freed_bytes = freed_bytes
        self.items_count = items_count
        self.details = details or []

    def add_detail(self, text: str):
        self.details.append(text)


class ModuleDef:
    def __init__(
        self,
        mod_id: str,
        name: str,
        category: str,
        description: str,
        default_selected: bool,
        risk_level: str,  # 'safe', 'recommended', 'caution'
        scan_func: Callable[[], int],
        clean_func: Callable[[bool], CleanResult]
    ):
        self.id = mod_id
        self.name = name
        self.category = category
        self.description = description
        self.selected = default_selected
        self.risk_level = risk_level
        self.scan_func = scan_func
        self.clean_func = clean_func
        self.estimated_bytes: int = 0
        self.scan_done: bool = False
        self.scan_in_progress: bool = False


# ==============================================================================
# IMPLEMENTAZIONE DEI MODULI DI PULIZIA
# ==============================================================================

# --- 1. SVILUPPO IOS & MACOS (XCODE & SIMULATORI) ---

def scan_xcode_deriveddata() -> int:
    return fast_get_path_size("~/Library/Developer/Xcode/DerivedData", timeout=20)

def clean_xcode_deriveddata(dry_run: bool) -> CleanResult:
    result = CleanResult("Xcode DerivedData")
    p = os.path.expanduser("~/Library/Developer/Xcode/DerivedData")
    if not os.path.isdir(p):
        result.add_detail("Cartella DerivedData non trovata.")
        return result
    size = fast_get_path_size(p, timeout=20)
    result.freed_bytes = size
    if dry_run:
        result.add_detail(f"[Simulazione] Spazio liberabile da DerivedData: {format_bytes(size)}")
    else:
        cnt, _ = safe_remove_directory_contents(p)
        result.items_count = cnt
        result.add_detail(f"DerivedData ripulita con successo ({format_bytes(size)}, {cnt} progetti/cache).")
    return result


def scan_xcode_archives() -> int:
    """Calcola lo spazio di TUTTI gli archivi Xcode (.xcarchive) senza filtri storici."""
    p = os.path.expanduser("~/Library/Developer/Xcode/Archives")
    if not os.path.isdir(p):
        return 0
    total = 0
    try:
        for date_f in os.listdir(p):
            date_p = os.path.join(p, date_f)
            if not os.path.isdir(date_p):
                continue
            for item in os.listdir(date_p):
                if item.endswith(".xcarchive"):
                    arch_p = os.path.join(date_p, item)
                    try:
                        total += fast_get_path_size(arch_p, timeout=5)
                    except OSError:
                        pass
    except OSError:
        pass
    return total

def clean_xcode_archives(dry_run: bool) -> CleanResult:
    """Rimuove TUTTI gli archivi Xcode (.xcarchive) liberando l'intero spazio occupato."""
    result = CleanResult("Xcode Archives (Tutti gli archivi)")
    p = os.path.expanduser("~/Library/Developer/Xcode/Archives")
    if not os.path.isdir(p):
        result.add_detail("Nessuna cartella Archives trovata.")
        return result

    archives_to_delete = []
    total_bytes = 0
    try:
        for date_f in os.listdir(p):
            date_p = os.path.join(p, date_f)
            if not os.path.isdir(date_p):
                continue
            for item in os.listdir(date_p):
                if item.endswith(".xcarchive"):
                    arch_p = os.path.join(date_p, item)
                    try:
                        sz = fast_get_path_size(arch_p, timeout=5)
                        mtime = datetime.fromtimestamp(os.path.getmtime(arch_p))
                        total_bytes += sz
                        archives_to_delete.append((arch_p, item, mtime, sz))
                    except OSError:
                        pass
    except OSError:
        pass

    result.freed_bytes = total_bytes
    result.items_count = len(archives_to_delete)
    if not archives_to_delete:
        result.add_detail("Nessun archivio Xcode (.xcarchive) presente.")
        return result

    result.add_detail(f"Trovati {len(archives_to_delete)} archivi totali ({format_bytes(total_bytes)}).")
    for path, name, mtime, sz in archives_to_delete[:4]:
        tag = "[Simulazione] Da eliminare:" if dry_run else "Eliminato:"
        result.add_detail(f"  {tag} {name} [{mtime.strftime('%Y-%m-%d')}] ({format_bytes(sz)})")
    if len(archives_to_delete) > 4:
        result.add_detail(f"  ... e altri {len(archives_to_delete) - 4} archivi.")

    if not dry_run:
        for path, _, _, _ in archives_to_delete:
            shutil.rmtree(path, ignore_errors=True)
        for date_f in os.listdir(p):
            dp = os.path.join(p, date_f)
            if os.path.isdir(dp) and not os.listdir(dp):
                shutil.rmtree(dp, ignore_errors=True)
        result.add_detail(f"Tutti gli archivi eliminati con successo ({format_bytes(total_bytes)}).")
    return result


def scan_xcode_devicesupport() -> int:
    return fast_get_path_size("~/Library/Developer/Xcode/iOS DeviceSupport", timeout=10)

def clean_xcode_devicesupport(dry_run: bool) -> CleanResult:
    result = CleanResult("Xcode iOS DeviceSupport")
    p = os.path.expanduser("~/Library/Developer/Xcode/iOS DeviceSupport")
    if not os.path.isdir(p):
        result.add_detail("Cartella iOS DeviceSupport non presente.")
        return result
    size = fast_get_path_size(p, timeout=10)
    result.freed_bytes = size
    if dry_run:
        result.add_detail(f"[Simulazione] Simboli dispositivi iOS rimovibili: {format_bytes(size)}")
    else:
        cnt, _ = safe_remove_directory_contents(p)
        result.items_count = cnt
        result.add_detail(f"iOS DeviceSupport ripulita ({format_bytes(size)}).")
    return result


def scan_xcode_ide_caches() -> int:
    total = fast_get_path_size("~/Library/Caches/com.apple.dt.Xcode", timeout=5)
    total += fast_get_path_size("~/Library/Developer/Xcode/DocumentationCache", timeout=5)
    total += fast_get_path_size("~/Library/Developer/Xcode/UserData/IB Support", timeout=5)
    return total

def clean_xcode_ide_caches(dry_run: bool) -> CleanResult:
    result = CleanResult("Xcode IDE Caches & Documentazione")
    paths = [
        "~/Library/Caches/com.apple.dt.Xcode",
        "~/Library/Developer/Xcode/DocumentationCache",
        "~/Library/Developer/Xcode/UserData/IB Support"
    ]
    total_sz = 0
    for p in paths:
        total_sz += fast_get_path_size(p, timeout=5)
    result.freed_bytes = total_sz
    if dry_run:
        result.add_detail(f"[Simulazione] Cache interne Xcode rimovibili: {format_bytes(total_sz)}")
    else:
        for p in paths:
            safe_remove_directory_contents(p)
        result.add_detail(f"Cache interne e documentazione temporanea Xcode svuotate ({format_bytes(total_sz)}).")
    return result


# --- Gestione Intelligente Simulatori iOS ---
_SIM_ANALYSIS_CACHE: Optional[Dict[str, Any]] = None

def get_simulators_analysis(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Analizza i runtime di simulatori installati e i relativi dispositivi virtuali.
    Rileva per ciascuna piattaforma (iOS, watchOS, tvOS, visionOS) l'ultima versione disponibile
    da preservare e individua i runtime e simulatori obsoleti da rimuovere.
    """
    global _SIM_ANALYSIS_CACHE
    if _SIM_ANALYSIS_CACHE is not None and not force_refresh:
        return _SIM_ANALYSIS_CACHE

    analysis: Dict[str, Any] = {
        "available": False,
        "kept_summary": "",
        "old_summary": "",
        "kept_runtimes": [],
        "older_runtimes": [],
        "deleted_devices": [],
        "runtimes_bytes": 0,
        "devices_bytes": 0,
        "cache_bytes": 0,
        "total_reclaimable_bytes": 0,
    }

    code, _, _ = run_cmd(["which", "xcrun"])
    if code != 0:
        _SIM_ANALYSIS_CACHE = analysis
        return analysis

    cache_p = os.path.expanduser("~/Library/Developer/CoreSimulator/Caches")
    logs_p = os.path.expanduser("~/Library/Logs/CoreSimulator")
    cache_sz = fast_get_path_size(cache_p, timeout=5) + fast_get_path_size(logs_p, timeout=5)
    analysis["cache_bytes"] = cache_sz

    # 1. Interroga i runtime dei simulatori
    code_rt, out_rt, _ = run_cmd(["xcrun", "simctl", "runtime", "list", "-j"], timeout=10)
    if code_rt != 0 or not out_rt.strip():
        analysis["total_reclaimable_bytes"] = cache_sz
        _SIM_ANALYSIS_CACHE = analysis
        return analysis

    try:
        runtimes_raw = json.loads(out_rt)
    except Exception:
        analysis["total_reclaimable_bytes"] = cache_sz
        _SIM_ANALYSIS_CACHE = analysis
        return analysis

    # 2. Interroga i dispositivi virtuali
    code_dev, out_dev, _ = run_cmd(["xcrun", "simctl", "list", "-j", "devices"], timeout=10)
    devices_by_rt: Dict[str, List[Dict[str, Any]]] = {}
    if code_dev == 0 and out_dev.strip():
        try:
            devices_by_rt = json.loads(out_dev).get("devices", {})
        except Exception:
            pass

    analysis["available"] = True

    def parse_version(v_str: str) -> Tuple[int, ...]:
        nums = [int(x) for x in re.findall(r"\d+", v_str or "")]
        return tuple(nums) if nums else (0,)

    def plat_name(plat_id: str) -> str:
        if "iphonesimulator" in plat_id:
            return "iOS"
        if "watchsimulator" in plat_id:
            return "watchOS"
        if "appletvsimulator" in plat_id:
            return "tvOS"
        if "xrsimulator" in plat_id:
            return "visionOS"
        return plat_id.split(".")[-1].replace("simulator", "")

    by_plat: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
    for uuid, info in runtimes_raw.items():
        if not isinstance(info, dict):
            continue
        plat = info.get("platformIdentifier", "com.apple.platform.iphonesimulator")
        by_plat.setdefault(plat, []).append((uuid, info))

    kept_summaries = []
    old_summaries = []
    runtimes_sz = 0
    devices_sz = 0

    for plat, rts in by_plat.items():
        rts.sort(key=lambda item: parse_version(item[1].get("version", "0")))
        latest_uuid, latest_info = rts[-1]
        pname = plat_name(plat)
        latest_v = latest_info.get("version", "sconosciuta")
        kept_summaries.append(f"{pname} {latest_v}")
        analysis["kept_runtimes"].append({
            "uuid": latest_uuid,
            "platform": pname,
            "version": latest_v,
            "info": latest_info,
        })

        older = rts[:-1]
        for u, inf in older:
            v = inf.get("version", "sconosciuta")
            sz = int(inf.get("sizeBytes", 0) or 0)
            rt_id = inf.get("runtimeIdentifier", "")
            devs = devices_by_rt.get(rt_id, [])
            d_sz = sum(int(d.get("dataPathSize", 0) or 0) for d in devs)

            runtimes_sz += sz
            devices_sz += d_sz

            analysis["older_runtimes"].append({
                "uuid": u,
                "platform": pname,
                "version": v,
                "runtimeIdentifier": rt_id,
                "sizeBytes": sz,
                "devices": devs,
                "devicesSizeBytes": d_sz,
            })
            for d in devs:
                analysis["deleted_devices"].append(d)

            old_summaries.append(f"{pname} {v}")

    analysis["kept_summary"] = ", ".join(kept_summaries) if kept_summaries else ""
    analysis["old_summary"] = ", ".join(old_summaries) if old_summaries else ""
    analysis["runtimes_bytes"] = runtimes_sz
    analysis["devices_bytes"] = devices_sz
    analysis["total_reclaimable_bytes"] = runtimes_sz + devices_sz + cache_sz

    _SIM_ANALYSIS_CACHE = analysis
    return analysis


def scan_old_simulators() -> int:
    """Calcola lo spazio totale recuperabile da vecchi runtime, simulatori associati e cache."""
    info = get_simulators_analysis()
    return info["total_reclaimable_bytes"]


def clean_old_simulators(dry_run: bool) -> CleanResult:
    """
    Rimuove i vecchi runtime di simulatori iOS e i dispositivi associati,
    preservando sempre l'ultima versione installata.
    """
    global _SIM_ANALYSIS_CACHE
    info = get_simulators_analysis()
    kept_label = info.get("kept_summary") or "ultima versione"
    result = CleanResult(f"Vecchi Simulatori iOS (Mantiene {kept_label})")

    code, _, _ = run_cmd(["which", "xcrun"])
    if code != 0:
        result.add_detail("xcrun non installato nel sistema.")
        return result

    result.freed_bytes = info["total_reclaimable_bytes"]
    result.items_count = len(info["older_runtimes"]) + len(info["deleted_devices"])

    if not info["older_runtimes"]:
        result.add_detail(f"Versione attiva mantenuta: {kept_label}.")
        result.add_detail("Nessun runtime precedente da rimuovere.")
        if dry_run:
            if info["cache_bytes"] > 0:
                result.add_detail(f"[Simulazione] Cache CoreSimulator da svuotare: {format_bytes(info['cache_bytes'])}")
        else:
            run_cmd(["xcrun", "simctl", "delete", "unavailable"])
            safe_remove_directory_contents(os.path.expanduser("~/Library/Developer/CoreSimulator/Caches"))
            safe_remove_directory_contents(os.path.expanduser("~/Library/Logs/CoreSimulator"))
            _SIM_ANALYSIS_CACHE = None
        return result

    if dry_run:
        result.add_detail(f"Versione che verrà mantenuta: {kept_label}")
        for rt in info["older_runtimes"]:
            result.add_detail(
                f"[Simulazione] Runtime da rimuovere: {rt['platform']} {rt['version']} "
                f"({format_bytes(rt['sizeBytes'])}, UUID: {rt['uuid']})"
            )
            devs = rt["devices"]
            if devs:
                result.add_detail(
                    f"  ↳ {len(devs)} simulatori associati da eliminare ({format_bytes(rt['devicesSizeBytes'])}):"
                )
                for d in devs[:4]:
                    sz_str = format_bytes(d.get("dataPathSize", 0))
                    result.add_detail(f"     • {d.get('name', 'Dispositivo')} ({sz_str})")
                if len(devs) > 4:
                    result.add_detail(f"     • ... e altri {len(devs) - 4} simulatori.")
        if info["cache_bytes"] > 0:
            result.add_detail(f"[Simulazione] Cache CoreSimulator da svuotare: {format_bytes(info['cache_bytes'])}")
        result.add_detail(f"[Simulazione] Spazio totale stimato da liberare: {format_bytes(info['total_reclaimable_bytes'])}")
    else:
        # 1. Spegni e rimuovi i dispositivi virtuali associati ai vecchi runtime
        for dev in info["deleted_devices"]:
            udid = dev.get("udid")
            if not udid:
                continue
            if dev.get("state") == "Booted":
                run_cmd(["xcrun", "simctl", "shutdown", udid], timeout=15)
            run_cmd(["xcrun", "simctl", "delete", udid], timeout=20)

        # 2. Rimuovi i runtime disk images obsoleti
        for rt in info["older_runtimes"]:
            u = rt.get("uuid")
            if u:
                run_cmd(["xcrun", "simctl", "runtime", "delete", u], timeout=60)

        # 3. Pulizia dispositivi orfani e cache
        run_cmd(["xcrun", "simctl", "delete", "unavailable"], timeout=20)
        run_cmd(["xcrun", "simctl", "runtime", "delete", "unavailable"], timeout=20)
        safe_remove_directory_contents(os.path.expanduser("~/Library/Developer/CoreSimulator/Caches"))
        safe_remove_directory_contents(os.path.expanduser("~/Library/Logs/CoreSimulator"))

        old_cnt = len(info['older_runtimes'])
        dev_cnt = len(info['deleted_devices'])
        rt_str = "1 runtime obsoleto" if old_cnt == 1 else f"{old_cnt} runtime obsoleti"
        dev_str = "1 simulatore associato" if dev_cnt == 1 else f"{dev_cnt} simulatori associati"
        result.add_detail(f"Conservata versione attiva più recente: {kept_label}.")
        result.add_detail(
            f"Rimossi {rt_str} ({info.get('old_summary', '')}) e {dev_str}."
        )
        result.add_detail("Cache CoreSimulator e log rimossi.")
        result.add_detail(f"Spazio liberato: {format_bytes(info['total_reclaimable_bytes'])}")
        _SIM_ANALYSIS_CACHE = None

    return result

# Alias per retrocompatibilità
scan_simulators_cache = scan_old_simulators
clean_simulators_cache = clean_old_simulators


def scan_swiftpm_cache() -> int:
    return fast_get_path_size("~/Library/Caches/org.swift.swiftpm", timeout=10)

def clean_swiftpm_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("Swift Package Manager Cache")
    p = os.path.expanduser("~/Library/Caches/org.swift.swiftpm")
    if not os.path.isdir(p):
        result.add_detail("Cache SPM non presente.")
        return result
    sz = fast_get_path_size(p, timeout=10)
    result.freed_bytes = sz
    if dry_run:
        result.add_detail(f"[Simulazione] Spazio occupato dalla cache SPM: {format_bytes(sz)}")
    else:
        cnt, _ = safe_remove_directory_contents(p)
        result.items_count = cnt
        result.add_detail(f"Cache Swift Package Manager liberata ({format_bytes(sz)}).")
    return result


# --- 2. PACKAGE MANAGERS & SDK ---

def scan_homebrew_cache() -> int:
    return fast_get_path_size("~/Library/Caches/Homebrew", timeout=10)

def clean_homebrew_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("Homebrew Cache & Bottles")
    code, _, _ = run_cmd(["which", "brew"])
    if code != 0:
        result.add_detail("Homebrew non installato nel sistema.")
        return result

    cache_p = os.path.expanduser("~/Library/Caches/Homebrew")
    sz = fast_get_path_size(cache_p, timeout=10)
    result.freed_bytes = sz

    if dry_run:
        code, out, _ = run_cmd(["brew", "cleanup", "-n", "--prune=all"])
        lines = [l.strip() for l in out.splitlines() if l.strip().startswith("Would remove:")]
        result.items_count = len(lines)
        result.add_detail(f"Dimensione cache Homebrew rilevata: {format_bytes(sz)}")
        if lines:
            for s in lines[:3]:
                result.add_detail(f"  [Simulazione] {s}")
            if len(lines) > 3:
                result.add_detail(f"  ... e altri {len(lines) - 3} file/bottles.")
    else:
        run_cmd(["brew", "cleanup", "--prune=all", "-s"])
        safe_remove_directory_contents(cache_p)
        result.add_detail(f"Cache e bottles Homebrew liberati ({format_bytes(sz)}).")
    return result


def scan_cocoapods_cache() -> int:
    return fast_get_path_size("~/Library/Caches/CocoaPods", timeout=10)

def clean_cocoapods_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("CocoaPods Cache")
    p = os.path.expanduser("~/Library/Caches/CocoaPods")
    if not os.path.isdir(p):
        result.add_detail("Cartella cache CocoaPods non presente.")
        return result
    sz = fast_get_path_size(p, timeout=10)
    result.freed_bytes = sz
    if dry_run:
        result.add_detail(f"[Simulazione] Spazio occupato dalla cache CocoaPods: {format_bytes(sz)}")
    else:
        code, _, _ = run_cmd(["which", "pod"])
        if code == 0:
            run_cmd(["pod", "cache", "clean", "--all"])
        safe_remove_directory_contents(p)
        result.add_detail(f"Cache CocoaPods svuotata ({format_bytes(sz)}).")
    return result


def scan_npm_cache() -> int:
    total = fast_get_path_size("~/.npm", timeout=10)
    total += fast_get_path_size("~/.yarn/cache", timeout=5)
    total += fast_get_path_size("~/.cache/yarn", timeout=5)
    total += fast_get_path_size("~/.pnpm-store", timeout=5)
    return total

def clean_npm_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("Node / NPM / Yarn / PNPM Caches")
    npm_p = os.path.expanduser("~/.npm")
    yarn_p1 = os.path.expanduser("~/.yarn/cache")
    yarn_p2 = os.path.expanduser("~/.cache/yarn")
    pnpm_p = os.path.expanduser("~/.pnpm-store")

    sz = scan_npm_cache()
    result.freed_bytes = sz

    if dry_run:
        result.add_detail(f"[Simulazione] Cache gestori pacchetti Node: {format_bytes(sz)}")
    else:
        code, _, _ = run_cmd(["which", "npm"])
        if code == 0:
            run_cmd(["npm", "cache", "clean", "--force"])
        if os.path.isdir(npm_p):
            safe_remove_directory_contents(npm_p)
        if os.path.isdir(yarn_p1):
            shutil.rmtree(yarn_p1, ignore_errors=True)
        if os.path.isdir(yarn_p2):
            shutil.rmtree(yarn_p2, ignore_errors=True)
        if os.path.isdir(pnpm_p):
            shutil.rmtree(pnpm_p, ignore_errors=True)
        result.add_detail(f"Cache NPM/Yarn/PNPM eliminate con successo ({format_bytes(sz)}).")
    return result


def scan_gradle_cache() -> int:
    total = fast_get_path_size("~/.gradle/caches", timeout=10)
    total += fast_get_path_size("~/.android/cache", timeout=5)
    total += fast_get_path_size("~/.android/build-cache", timeout=5)
    return total

def clean_gradle_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("Gradle & Android Build Caches")
    gc = os.path.expanduser("~/.gradle/caches")
    ac = os.path.expanduser("~/.android/cache")
    abc = os.path.expanduser("~/.android/build-cache")
    sz = scan_gradle_cache()
    result.freed_bytes = sz

    if dry_run:
        result.add_detail(f"[Simulazione] Spazio occupato dalle build cache Gradle/Android: {format_bytes(sz)}")
    else:
        safe_remove_directory_contents(gc)
        safe_remove_directory_contents(ac)
        safe_remove_directory_contents(abc)
        result.add_detail(f"Cache Gradle e Android ripulite ({format_bytes(sz)}).")
    return result


def scan_pip_cache() -> int:
    total = fast_get_path_size("~/Library/Caches/pip", timeout=5)
    total += fast_get_path_size("~/.cache/pip", timeout=5)
    total += fast_get_path_size("~/.cache/uv", timeout=5)
    return total

def clean_pip_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("Python / Pip / UV Cache")
    p1 = os.path.expanduser("~/Library/Caches/pip")
    p2 = os.path.expanduser("~/.cache/pip")
    p3 = os.path.expanduser("~/.cache/uv")
    sz = scan_pip_cache()
    result.freed_bytes = sz

    if dry_run:
        result.add_detail(f"[Simulazione] Cache pacchetti Python/Pip/UV: {format_bytes(sz)}")
    else:
        safe_remove_directory_contents(p1)
        safe_remove_directory_contents(p2)
        safe_remove_directory_contents(p3)
        result.add_detail(f"Cache Python/Pip/UV svuotata ({format_bytes(sz)}).")
    return result


def scan_flutter_pub_cache() -> int:
    total = fast_get_path_size("~/.pub-cache/git", timeout=5)
    return total

def clean_flutter_pub_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("Flutter & Dart Pub Git Cache")
    git_cache = os.path.expanduser("~/.pub-cache/git")
    sz = fast_get_path_size(git_cache, timeout=5)
    result.freed_bytes = sz
    if dry_run:
        result.add_detail(f"[Simulazione] Cache repository git di pub-cache: {format_bytes(sz)}")
    else:
        safe_remove_directory_contents(git_cache)
        result.add_detail(f"Cache git pub-cache eliminata ({format_bytes(sz)}).")
    return result


# --- 3. EDITOR & DOCKER ---

def parse_semver(ver_str: str) -> Tuple:
    clean = re.split(r'[-+]', ver_str)[0]
    parts = []
    for p in clean.split('.'):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(p)
    return tuple(parts)

def scan_vscode_extensions() -> int:
    ext_dir = os.path.expanduser("~/.vscode/extensions")
    if not os.path.isdir(ext_dir):
        return 0
    obsolete_file = os.path.join(ext_dir, ".obsolete")
    obsolete_dirs = set()
    if os.path.exists(obsolete_file):
        try:
            with open(obsolete_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                obsolete_dirs.update(data.keys())
        except Exception:
            pass

    ext_groups: Dict[str, List[Tuple[Tuple, str, str]]] = {}
    try:
        for entry in os.listdir(ext_dir):
            fp = os.path.join(ext_dir, entry)
            if not os.path.isdir(fp):
                continue
            m = re.match(r"^(.+)-(\d+\.[\w\.\-]+)$", entry)
            if m:
                base_name, ver = m.groups()
                ext_groups.setdefault(base_name, []).append((parse_semver(ver), ver, entry))
    except OSError:
        return 0

    for base_name, versions in ext_groups.items():
        if len(versions) > 1:
            try:
                sorted_vers = sorted(versions, key=lambda x: x[0])
            except TypeError:
                sorted_vers = sorted(versions, key=lambda x: str(x[0]))
            for _, _, folder_name in sorted_vers[:-1]:
                obsolete_dirs.add(folder_name)

    total = 0
    for folder in obsolete_dirs:
        p = os.path.join(ext_dir, folder)
        total += fast_get_path_size(p, timeout=5)
    return total

def clean_vscode_extensions(dry_run: bool) -> CleanResult:
    result = CleanResult("VS Code: Estensioni Obsolete")
    ext_dir = os.path.expanduser("~/.vscode/extensions")
    if not os.path.isdir(ext_dir):
        result.add_detail("Directory estensioni VS Code non presente.")
        return result

    obsolete_file = os.path.join(ext_dir, ".obsolete")
    obsolete_dirs = set()
    if os.path.exists(obsolete_file):
        try:
            with open(obsolete_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                obsolete_dirs.update(data.keys())
        except Exception:
            pass

    ext_groups: Dict[str, List[Tuple[Tuple, str, str]]] = {}
    for entry in os.listdir(ext_dir):
        fp = os.path.join(ext_dir, entry)
        if not os.path.isdir(fp):
            continue
        m = re.match(r"^(.+)-(\d+\.[\w\.\-]+)$", entry)
        if m:
            base_name, ver = m.groups()
            ext_groups.setdefault(base_name, []).append((parse_semver(ver), ver, entry))

    for base_name, versions in ext_groups.items():
        if len(versions) > 1:
            try:
                sorted_vers = sorted(versions, key=lambda x: x[0])
            except TypeError:
                sorted_vers = sorted(versions, key=lambda x: str(x[0]))
            for _, _, folder_name in sorted_vers[:-1]:
                obsolete_dirs.add(folder_name)

    folders_to_delete = []
    total_bytes = 0
    for folder in obsolete_dirs:
        p = os.path.join(ext_dir, folder)
        if os.path.isdir(p):
            sz = fast_get_path_size(p, timeout=5)
            total_bytes += sz
            folders_to_delete.append((folder, p, sz))

    result.freed_bytes = total_bytes
    result.items_count = len(folders_to_delete)
    if not folders_to_delete:
        result.add_detail("Nessuna versione obsoleta di estensione rilevata.")
        return result

    result.add_detail(f"Trovate {len(folders_to_delete)} versioni obsolete ({format_bytes(total_bytes)}).")
    for folder, _, sz in folders_to_delete[:3]:
        tag = "[Simulazione] Da eliminare:" if dry_run else "Eliminato:"
        result.add_detail(f"  {tag} {folder} ({format_bytes(sz)})")
    if len(folders_to_delete) > 3:
        result.add_detail(f"  ... e altre {len(folders_to_delete) - 3} estensioni.")

    if not dry_run:
        for _, p, _ in folders_to_delete:
            shutil.rmtree(p, ignore_errors=True)
        if os.path.exists(obsolete_file):
            try:
                os.remove(obsolete_file)
            except OSError:
                pass
    return result


def scan_docker() -> int:
    code, _, _ = run_cmd(["which", "docker"])
    if code != 0:
        return 0
    code, _, _ = run_cmd(["docker", "info"], timeout=3)
    if code != 0:
        return 0
    return 1

def clean_docker(dry_run: bool) -> CleanResult:
    result = CleanResult("Docker System Prune")
    code, _, _ = run_cmd(["which", "docker"])
    if code != 0:
        result.add_detail("Docker non installato.")
        return result
    code, _, _ = run_cmd(["docker", "info"], timeout=4)
    if code != 0:
        result.add_detail("Il demone Docker non è in esecuzione (nessuna pulizia necessaria).")
        return result

    if dry_run:
        code, out, _ = run_cmd(["docker", "system", "df"])
        result.add_detail("Stato occupazione Docker:")
        for line in out.splitlines():
            if line.strip():
                result.add_detail(f"  {line.strip()}")
    else:
        run_cmd(["docker", "system", "prune", "-f", "--volumes"])
        run_cmd(["docker", "builder", "prune", "-f"])
        result.add_detail("Docker prune completato (container fermi, volumi orfani e build cache rimossi).")
    return result


# --- 4. CACHE APP & BROWSER ---

def scan_spotify_cache() -> int:
    return fast_get_path_size("~/Library/Caches/com.spotify.client", timeout=10)

def clean_spotify_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("Spotify Streaming Cache")
    p = os.path.expanduser("~/Library/Caches/com.spotify.client")
    if not os.path.isdir(p):
        result.add_detail("Cache Spotify non presente.")
        return result
    sz = fast_get_path_size(p, timeout=10)
    result.freed_bytes = sz

    if dry_run:
        result.add_detail(f"[Simulazione] Spazio cache brani Spotify: {format_bytes(sz)}")
        result.add_detail("  (Nota: account, preferenze e playlist rimangono intatti in Application Support)")
    else:
        data_p = os.path.join(p, "Data")
        browser_p = os.path.join(p, "Browser")
        if os.path.isdir(data_p):
            safe_remove_directory_contents(data_p)
        if os.path.isdir(browser_p):
            safe_remove_directory_contents(browser_p)
        safe_remove_directory_contents(p)
        result.add_detail(f"Cache brani musicali Spotify svuotata ({format_bytes(sz)}).")
    return result


def scan_browser_cache() -> int:
    paths = [
        "~/Library/Caches/BraveSoftware",
        "~/Library/Caches/com.brave.Browser",
        "~/Library/Caches/Google/Chrome",
        "~/Library/Caches/com.google.Chrome",
        "~/Library/Caches/com.apple.Safari"
    ]
    total = 0
    for p in paths:
        total += fast_get_path_size(p, timeout=5)
    return total

def clean_browser_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("Browser Web Caches (Brave, Chrome, Safari)")
    paths = [
        "~/Library/Caches/BraveSoftware",
        "~/Library/Caches/com.brave.Browser",
        "~/Library/Caches/Google/Chrome",
        "~/Library/Caches/com.google.Chrome",
        "~/Library/Caches/com.apple.Safari"
    ]
    sz = scan_browser_cache()
    result.freed_bytes = sz

    if dry_run:
        result.add_detail(f"[Simulazione] File temporanei di cache web rimovibili: {format_bytes(sz)}")
        result.add_detail("  (Nota: cronologia, cookie, schede e password NON vengono toccati)")
    else:
        for p in paths:
            safe_remove_directory_contents(p)
        result.add_detail(f"Cache temporanea browser svuotata con successo ({format_bytes(sz)}).")
    return result


# --- 5. SISTEMA MACOS & RAM ---

def scan_trash() -> int:
    return fast_get_path_size("~/.Trash", timeout=10)

def clean_trash(dry_run: bool) -> CleanResult:
    result = CleanResult("Cestino macOS (~/.Trash)")
    p = os.path.expanduser("~/.Trash")
    sz = fast_get_path_size(p, timeout=10)
    result.freed_bytes = sz
    if dry_run:
        result.add_detail(f"[Simulazione] File presenti nel Cestino: {format_bytes(sz)}")
    else:
        cnt, _ = safe_remove_directory_contents(p)
        result.items_count = cnt
        result.add_detail(f"Cestino di macOS svuotato definitivamente ({format_bytes(sz)}, {cnt} elementi).")
    return result


def scan_system_logs() -> int:
    return fast_get_path_size("~/Library/Logs", timeout=10)

def clean_system_logs(dry_run: bool) -> CleanResult:
    result = CleanResult("Log e Crash Report Utente")
    p = os.path.expanduser("~/Library/Logs")
    sz = fast_get_path_size(p, timeout=10)
    result.freed_bytes = sz
    if dry_run:
        result.add_detail(f"[Simulazione] Log applicativi e report di crash: {format_bytes(sz)}")
    else:
        cnt, _ = safe_remove_directory_contents(p)
        result.items_count = cnt
        result.add_detail(f"Cartella Log utente ripulita ({format_bytes(sz)}).")
    return result


def scan_snapshots() -> int:
    code, out, _ = run_cmd(["tmutil", "listlocalsnapshots", "/"], timeout=3)
    if code == 0:
        lines = [l.strip() for l in out.splitlines() if l.strip().startswith("com.apple.TimeMachine")]
        return len(lines) * 1024 * 1024 * 1024
    return 0

def clean_snapshots(dry_run: bool) -> CleanResult:
    result = CleanResult("Time Machine Local Snapshots")
    code, out, _ = run_cmd(["tmutil", "listlocalsnapshots", "/"], timeout=4)
    snaps = [l.strip() for l in out.splitlines() if l.strip().startswith("com.apple.TimeMachine")]
    result.items_count = len(snaps)

    if not snaps:
        result.add_detail("Nessuno snapshot Time Machine locale presente sul disco.")
        return result

    result.add_detail(f"Rilevati {len(snaps)} snapshot APFS locali.")
    if dry_run:
        result.add_detail("[Simulazione] Esecuzione di tmutil thinlocalsnapshots per liberare spazio su disco.")
    else:
        run_cmd(["tmutil", "thinlocalsnapshots", "/", "10000000000", "4"])
        result.add_detail("Snapshot locali assottigliati con successo.")
    return result


def scan_idle_daemons() -> int:
    code, out, _ = run_cmd(["pgrep", "-f", "GradleDaemon|KotlinCompileDaemon"], timeout=3)
    pids = [p.strip() for p in out.splitlines() if p.strip()]
    return len(pids)

def clean_idle_daemons(dry_run: bool) -> CleanResult:
    result = CleanResult("Termina Demoni Gradle/Kotlin in RAM")
    code, out, _ = run_cmd(["pgrep", "-f", "GradleDaemon|KotlinCompileDaemon"], timeout=3)
    pids = [p.strip() for p in out.splitlines() if p.strip()]
    result.items_count = len(pids)

    if not pids:
        result.add_detail("Nessun demone Gradle o Kotlin attivo in memoria.")
        return result

    if dry_run:
        result.add_detail(f"[Simulazione] Rilevati {len(pids)} demoni Java (Gradle/Kotlin) attivi in memoria.")
    else:
        run_cmd(["pkill", "-f", "GradleDaemon"])
        run_cmd(["pkill", "-f", "KotlinCompileDaemon"])
        result.add_detail(f"Terminati {len(pids)} demoni in background per recuperare memoria RAM.")
    return result


def scan_ram_purge() -> int:
    return 0

def clean_ram_purge(dry_run: bool) -> CleanResult:
    result = CleanResult("macOS Purge RAM (Svuota Cache Inattiva)")
    if dry_run:
        result.add_detail("[Simulazione] Esecuzione del comando di sistema 'purge' per liberare memoria fisica.")
    else:
        code, _, err = run_cmd(["purge"], timeout=10)
        if code == 0:
            result.add_detail("Comando purge eseguito: cache disco inattiva rilasciata alla RAM fisica.")
        else:
            result.add_detail(f"Nota: comando purge non completato: {err.strip() or 'permessi insufficienti'}")
    return result


# --- 6. OPERAZIONI AVANZATE (OPT-IN) ---

def scan_simulators_erase_all() -> int:
    return 0

def clean_simulators_erase_all(dry_run: bool) -> CleanResult:
    result = CleanResult("Reset Totale Simulatori iOS (Factory Reset)")
    if dry_run:
        result.add_detail("[Simulazione] Esecuzione 'xcrun simctl erase all': tutti i simulatori verranno azzerati.")
    else:
        run_cmd(["xcrun", "simctl", "erase", "all"], timeout=30)
        result.add_detail("Tutti i simulatori iOS sono stati ripristinati allo stato di fabbrica iniziale.")
    return result


# ==============================================================================
# REGISTRO DEI MODULI
# ==============================================================================

def create_all_modules() -> List[ModuleDef]:
    """Crea e registra tutti i moduli di pulizia disponibili."""
    # Analisi dinamica simulatori per mostrare versione conservata ed eliminabili
    sim_info = get_simulators_analysis()
    if sim_info.get("kept_summary"):
        sim_name = f"Vecchi Simulatori iOS (Mantiene solo {sim_info['kept_summary']})"
    else:
        sim_name = "Vecchi Simulatori iOS (Mantiene ultima versione)"

    if sim_info.get("old_summary"):
        old_cnt = len(sim_info.get("older_runtimes", []))
        dev_cnt = len(sim_info.get("deleted_devices", []))
        rt_str = "1 runtime obsoleto" if old_cnt == 1 else f"{old_cnt} runtime obsoleti"
        dev_str = "1 simulatore associato" if dev_cnt == 1 else f"{dev_cnt} simulatori associati"
        sim_desc = (
            f"Rimuove {rt_str} ({sim_info['old_summary']}: {format_bytes(sim_info['runtimes_bytes'])}) "
            f"e i {dev_str} ({format_bytes(sim_info['devices_bytes'])}), "
            f"conservando solo {sim_info['kept_summary']}."
        )
    elif sim_info.get("kept_summary"):
        sim_desc = (
            f"Nessun runtime precedente da rimuovere. Conserva l'ultima versione installata "
            f"({sim_info['kept_summary']}) e ripulisce le cache orfane."
        )
    else:
        sim_desc = "Rimuove le versioni precedenti dei simulatori e mantiene solo l'ultima versione installata."

    return [
        # --- 🍎 Sviluppo iOS & macOS ---
        ModuleDef(
            mod_id="deriveddata",
            name="Xcode DerivedData",
            category="🍎 Sviluppo iOS & macOS",
            description="Build cache intermedie dei progetti Xcode e Flutter iOS.",
            default_selected=True,
            risk_level="recommended",
            scan_func=scan_xcode_deriveddata,
            clean_func=clean_xcode_deriveddata
        ),
        ModuleDef(
            mod_id="archives",
            name="Xcode Archives (TUTTI gli archivi)",
            category="🍎 Sviluppo iOS & macOS",
            description="Elimina tutti gli archivi .xcarchive generati in passato.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_xcode_archives,
            clean_func=clean_xcode_archives
        ),
        ModuleDef(
            mod_id="devicesupport",
            name="Xcode iOS DeviceSupport",
            category="🍎 Sviluppo iOS & macOS",
            description="Simboli di debug di dispositivi fisici iOS connessi in passato.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_xcode_devicesupport,
            clean_func=clean_xcode_devicesupport
        ),
        ModuleDef(
            mod_id="xcode_cache",
            name="Xcode IDE Caches & Documentazione",
            category="🍎 Sviluppo iOS & macOS",
            description="Cache interna di compilazione/indicizzazione Xcode e documentazione.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_xcode_ide_caches,
            clean_func=clean_xcode_ide_caches
        ),
        ModuleDef(
            mod_id="simulators",
            name=sim_name,
            category="🍎 Sviluppo iOS & macOS",
            description=sim_desc,
            default_selected=True,
            risk_level="recommended",
            scan_func=scan_old_simulators,
            clean_func=clean_old_simulators
        ),
        ModuleDef(
            mod_id="swiftpm",
            name="Swift Package Manager Cache",
            category="🍎 Sviluppo iOS & macOS",
            description="Cache globale di clone e build dei pacchetti SwiftPM.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_swiftpm_cache,
            clean_func=clean_swiftpm_cache
        ),

        # --- 📦 Package Managers & SDK ---
        ModuleDef(
            mod_id="brew",
            name="Homebrew Cache & Bottles",
            category="📦 Package Managers & SDK",
            description="Download vecchi pacchetti e formule con brew cleanup --prune=all.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_homebrew_cache,
            clean_func=clean_homebrew_cache
        ),
        ModuleDef(
            mod_id="cocoapods",
            name="CocoaPods Cache",
            category="📦 Package Managers & SDK",
            description="Cache locale archivio pod (~/Library/Caches/CocoaPods).",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_cocoapods_cache,
            clean_func=clean_cocoapods_cache
        ),
        ModuleDef(
            mod_id="npm",
            name="Node / NPM / Yarn / PNPM Caches",
            category="📦 Package Managers & SDK",
            description="Cache pacchetti JavaScript (~/.npm, ~/.yarn/cache, ~/.pnpm-store).",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_npm_cache,
            clean_func=clean_npm_cache
        ),
        ModuleDef(
            mod_id="gradle",
            name="Gradle & Android Build Caches",
            category="📦 Package Managers & SDK",
            description="Cache di compilazione Gradle e Android (~/.gradle/caches, ~/.android/cache).",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_gradle_cache,
            clean_func=clean_gradle_cache
        ),
        ModuleDef(
            mod_id="pip",
            name="Python / Pip / UV Cache",
            category="📦 Package Managers & SDK",
            description="Cache ruote (.whl) e download pacchetti Python (~/Library/Caches/pip).",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_pip_cache,
            clean_func=clean_pip_cache
        ),
        ModuleDef(
            mod_id="flutter",
            name="Flutter & Dart Pub Git Cache",
            category="📦 Package Managers & SDK",
            description="Cache repository git clonati in ~/.pub-cache/git.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_flutter_pub_cache,
            clean_func=clean_flutter_pub_cache
        ),

        # --- 💻 Editor & Strumenti ---
        ModuleDef(
            mod_id="vscode",
            name="VS Code: Estensioni Obsolete",
            category="💻 Editor & Strumenti",
            description="Rimuove versioni precedenti duplicate in ~/.vscode/extensions.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_vscode_extensions,
            clean_func=clean_vscode_extensions
        ),
        ModuleDef(
            mod_id="docker",
            name="Docker System Prune",
            category="💻 Editor & Strumenti",
            description="Container fermi, immagini orfane, volumi non associati e build cache.",
            default_selected=False,
            risk_level="caution",
            scan_func=scan_docker,
            clean_func=clean_docker
        ),

        # --- 🌐 Cache App & Browser ---
        ModuleDef(
            mod_id="spotify",
            name="Spotify Streaming Cache",
            category="🌐 Cache App & Browser",
            description="Cache locale delle canzoni in streaming (account e playlist intatti).",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_spotify_cache,
            clean_func=clean_spotify_cache
        ),
        ModuleDef(
            mod_id="browser",
            name="Browser Web Caches (Brave, Chrome, Safari)",
            category="🌐 Cache App & Browser",
            description="Cache web temporanea dei browser (nessun cookie/password toccato).",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_browser_cache,
            clean_func=clean_browser_cache
        ),

        # --- ⚙️ Sistema macOS & RAM ---
        ModuleDef(
            mod_id="trash",
            name="Cestino macOS (~/.Trash)",
            category="⚙️ Sistema macOS & RAM",
            description="Svuota definitivamente i file rimasti nel Cestino utente.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_trash,
            clean_func=clean_trash
        ),
        ModuleDef(
            mod_id="logs",
            name="Log Utente & Crash Reports",
            category="⚙️ Sistema macOS & RAM",
            description="File di log applicativi e crash dump accumulati in ~/Library/Logs.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_system_logs,
            clean_func=clean_system_logs
        ),
        ModuleDef(
            mod_id="snapshots",
            name="Time Machine Local Snapshots",
            category="⚙️ Sistema macOS & RAM",
            description="Assottiglia gli snapshot locali APFS per sbloccare spazio su disco.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_snapshots,
            clean_func=clean_snapshots
        ),
        ModuleDef(
            mod_id="daemons",
            name="Termina Demoni Gradle/Kotlin in RAM",
            category="⚙️ Sistema macOS & RAM",
            description="Chiude i processi Java inattivi che occupano memoria unificata.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_idle_daemons,
            clean_func=clean_idle_daemons
        ),
        ModuleDef(
            mod_id="ram_purge",
            name="macOS Purge RAM (svuota cache inattiva)",
            category="⚙️ Sistema macOS & RAM",
            description="Svuota la cache disco inattiva di macOS per restituire RAM fisica al sistema.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_ram_purge,
            clean_func=clean_ram_purge
        ),

        # --- ⚠️ Operazioni Avanzate (Opt-in) ---
        ModuleDef(
            mod_id="simulators_erase",
            name="Reset Totale Simulatori iOS (Opt-in)",
            category="⚠️ Operazioni Avanzate (Opt-in)",
            description="xcrun simctl erase all: azzera tutte le app e dati installati nei simulatori.",
            default_selected=False,
            risk_level="caution",
            scan_func=scan_simulators_erase_all,
            clean_func=clean_simulators_erase_all
        ),
    ]


def apply_saved_config_to_modules(modules: List[ModuleDef], saved_config: Dict[str, Any]):
    """Applica le selezioni salvate in precedenza; se nuova, usa default."""
    saved_selections = saved_config.get("selected_modules", {})
    for m in modules:
        if m.id in saved_selections:
            m.selected = bool(saved_selections[m.id])


# ==============================================================================
# SCANSIONE IN PARALLELO
# ==============================================================================

def start_background_scanner(modules: List[ModuleDef]):
    """Scansiona le dimensioni dei moduli in parallelo in background usando thread daemon."""
    def _worker(m: ModuleDef):
        m.scan_in_progress = True
        try:
            m.estimated_bytes = m.scan_func()
        except Exception:
            m.estimated_bytes = 0
        finally:
            m.scan_done = True
            m.scan_in_progress = False

    def _scanner_pool():
        threads = []
        for m in modules:
            th = threading.Thread(target=_worker, args=(m,), daemon=True)
            th.start()
            threads.append(th)

    t = threading.Thread(target=_scanner_pool, daemon=True)
    t.start()


# ==============================================================================
# TERMINAL UI INTERATTIVA (IN-PLACE ANSI & RAWMONITOR)
# ==============================================================================

def read_key(fd: int, timeout: float = 0.08) -> Optional[str]:
    """Legge un singolo tasto o sequenza di escape (frecce) da stdin in modo unbuffered e non bloccante."""
    r, _, _ = select.select([fd], [], [], timeout)
    if not r:
        return None
    try:
        data = os.read(fd, 32)
    except OSError:
        return None
    if not data:
        return None

    # Se è arrivato solo il byte ESC (\x1b), aspetta brevissimamente se seguono altri byte di sequenza
    if data == b'\x1b':
        r2, _, _ = select.select([fd], [], [], 0.03)
        if r2:
            try:
                more = os.read(fd, 16)
                data += more
            except OSError:
                pass

    if data.startswith(b'\x1b'):
        # Riconoscimento frecce standard ANSI (\x1b[A), SS3 (\x1bOA), e varianti con modificatori
        if data in (b'\x1b[A', b'\x1bOA') or data.endswith(b'A'):
            return 'UP'
        elif data in (b'\x1b[B', b'\x1bOB') or data.endswith(b'B'):
            return 'DOWN'
        elif data in (b'\x1b[C', b'\x1bOC') or data.endswith(b'C'):
            return 'RIGHT'
        elif data in (b'\x1b[D', b'\x1bOD') or data.endswith(b'D'):
            return 'LEFT'
        elif data in (b'\x1b[H', b'\x1bOH'):
            return 'HOME'
        elif data in (b'\x1b[F', b'\x1bOF'):
            return 'END'
        elif data in (b'\x1b[5~', b'\x1b[5;2~'):
            return 'PAGE_UP'
        elif data in (b'\x1b[6~', b'\x1b[6;2~'):
            return 'PAGE_DOWN'
        elif data == b'\x1b':
            return 'ESC'
        # Sequenza escape non riconosciuta: ignora per sicurezza, NON uscire!
        return None
    elif data in (b'\r', b'\n'):
        return 'ENTER'
    elif data == b' ':
        return 'SPACE'
    elif data == b'\x03':  # Ctrl+C
        raise KeyboardInterrupt

    try:
        return data.decode('utf-8', errors='ignore')
    except Exception:
        return None


def run_interactive_tui(modules: List[ModuleDef], dry_run_initial: bool = True) -> Tuple[bool, bool, List[ModuleDef]]:
    """
    Mostra la lista interattiva di attività di pulizia direttamente nel terminale.
    - Arrow keys (↑ / ↓) per scorrere
    - Barra spaziatrice per attivare / disattivare
    - Divisione in categorie
    - Selezione salvata automaticamente
    - Sliding window viewport per terminali di qualsiasi altezza
    """
    start_background_scanner(modules)
    disk_info = get_disk_usage_info()

    # Prepara lista elementi (categorie + moduli)
    display_items: List[Dict[str, Any]] = []
    selectable_indices: List[int] = []
    curr_cat = None
    for m in modules:
        if m.category != curr_cat:
            curr_cat = m.category
            display_items.append({"type": "category", "label": curr_cat})
        idx = len(display_items)
        display_items.append({"type": "module", "module": m})
        selectable_indices.append(idx)

    cursor_idx = 0  # Indice all'interno di selectable_indices
    offset = 0      # Offset di scorrimento nella display_items
    dry_run = dry_run_initial
    prev_rendered_lines = 0

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    def persist_current_state():
        selections = {m.id: m.selected for m in modules}
        save_config(selections, dry_run)

    try:
        tty.setcbreak(fd)
        sys.stdout.write("\033[?25l")  # Nascondi cursore
        sys.stdout.flush()

        needs_redraw = True
        last_done_count = -1
        prev_term_size = (-1, -1)

        while True:
            # Dimensioni terminale
            term_cols, term_lines = shutil.get_terminal_size((80, 24))
            term_cols = max(40, term_cols)
            term_lines = max(14, term_lines)

            if (term_cols, term_lines) != prev_term_size:
                prev_term_size = (term_cols, term_lines)
                needs_redraw = True

            # Controlla se nuove dimensioni sono arrivate dalla scansione background
            current_done_count = sum(1 for m in modules if m.scan_done)
            if current_done_count != last_done_count:
                last_done_count = current_done_count
                needs_redraw = True

            # Posizione attiva nella lista display
            active_disp_idx = selectable_indices[cursor_idx]
            active_module = display_items[active_disp_idx]["module"]

            # Calcolo viewport
            header_lines_count = 5
            footer_lines_count = 5
            viewport_size = max(4, term_lines - (header_lines_count + footer_lines_count))

            # Aggiusta scorrimento offset
            if len(display_items) <= viewport_size:
                offset = 0
            else:
                if active_disp_idx < offset:
                    offset = active_disp_idx
                elif active_disp_idx >= offset + viewport_size:
                    offset = active_disp_idx - viewport_size + 1
                offset = max(0, min(offset, len(display_items) - viewport_size))

            if needs_redraw:
                visible_slice = display_items[offset : offset + viewport_size]

                # Costruisci righe da stampare
                lines: List[str] = []

                # 1. HEADER
                title_text = f" 🧹 Mac Developer Optimizer & Cleaner "
                mode_badge = f"{Colors.YELLOW}[✔] 🔍 DRY-RUN (Simulazione){Colors.RESET}" if dry_run else f"{Colors.GREEN}[ ] ⚡ ESECUZIONE REALE{Colors.RESET}"
                disk_line = f"Disco: {Colors.BOLD}{disk_info['free']}{Colors.RESET} liberi su {disk_info['total']} ({disk_info['percent']} usato)  |  Modalità: {mode_badge}"
                lines.append(colorize("=" * (term_cols - 1), Colors.BOLD))
                lines.append(f"{Colors.HEADER}{Colors.BOLD}{title_text}{Colors.RESET}")
                lines.append(disk_line)
                lines.append(colorize("-" * (term_cols - 1), Colors.DIM))
                lines.append(f"{Colors.DIM}  (Usa [↑/↓] per muoverti, [Spazio] per abilitare/disabilitare, [d] Dry-run, [Invio] Avvia){Colors.RESET}")

                # 2. INDICATORE SOPRA
                if offset > 0:
                    lines.append(f"{Colors.DIM}  ▲ ... ({offset} voci sopra) ...{Colors.RESET}")
                else:
                    lines.append("")

                # 3. LISTA ELEMENTI
                for item in visible_slice:
                    if item["type"] == "category":
                        cat_str = f"  {Colors.BOLD}{Colors.HEADER}▸ {item['label']}{Colors.RESET}"
                        lines.append(fit_line(cat_str, term_cols))
                    else:
                        m = item["module"]
                        is_active = (m == active_module)

                        # Simbolo Checkmark
                        if m.selected:
                            chk_str = f"{Colors.GREEN}{Colors.BOLD}[✔]{Colors.RESET}"
                        else:
                            chk_str = f"{Colors.DIM}[ ]{Colors.RESET}"

                        # Dimensione
                        if m.scan_done:
                            sz_str = f"{format_bytes(m.estimated_bytes):>9}"
                        else:
                            sz_str = f"{Colors.DIM}(in calcolo){Colors.RESET}"

                        # Badge rischio
                        if m.risk_level == "caution":
                            risk_str = f"{Colors.YELLOW}[Attenzione]{Colors.RESET}"
                        elif m.risk_level == "recommended":
                            risk_str = f"{Colors.CYAN}[Consigliato]{Colors.RESET}"
                        else:
                            risk_str = f"{Colors.GREEN}[Sicuro]{Colors.RESET}"

                        name_w = max(24, term_cols - 30)
                        t_name = m.name[:name_w].ljust(name_w)

                        if is_active:
                            prefix = f"{Colors.CYAN}{Colors.BOLD}❯{Colors.RESET}"
                            line_content = f"{prefix} {chk_str} {Colors.BOLD}{t_name}{Colors.RESET}  {sz_str}  {risk_str}"
                        else:
                            prefix = " "
                            line_content = f"{prefix} {chk_str} {t_name}  {sz_str}  {risk_str}"

                        lines.append(fit_line(line_content, term_cols))

                # Riempi righe vuote se fine elenco per stabilizzare altezza
                while len(visible_slice) < viewport_size:
                    lines.append("")
                    visible_slice.append({"type": "blank"})

                # 4. INDICATORE SOTTO
                remaining_below = len(display_items) - (offset + viewport_size)
                if remaining_below > 0:
                    lines.append(f"{Colors.DIM}  ▼ ... ({remaining_below} voci sotto) ...{Colors.RESET}")
                else:
                    lines.append("")

                # 5. FOOTER
                lines.append(colorize("-" * (term_cols - 1), Colors.DIM))
                desc_text = f"ℹ️  {active_module.description}"
                lines.append(fit_line(colorize(desc_text, Colors.CYAN), term_cols))

                sel_count = sum(1 for m in modules if m.selected)
                sel_bytes = sum(m.estimated_bytes for m in modules if m.selected)
                stat_text = f"Totale selezionato: {Colors.BOLD}{format_bytes(sel_bytes)}{Colors.RESET} ({sel_count}/{len(modules)} moduli attivi)"
                lines.append(fit_line(stat_text, term_cols))

                help_keys = "[↑/↓] Naviga  [Spazio] Attiva/Disattiva  [a] Tutti  [n] Nessuno  [d] Dry-run  [Invio] Esegui  [q] Esci"
                lines.append(fit_line(colorize(help_keys, Colors.DIM), term_cols))

                # --- RENDERING ANSI PULITO ED EFFICIENTE ---
                if prev_rendered_lines > 0:
                    sys.stdout.write(f"\r\033[{prev_rendered_lines}A\033[0J")
                output_chunk = "\n".join(lines) + "\n"
                sys.stdout.write(output_chunk)
                sys.stdout.flush()
                prev_rendered_lines = len(lines)
                needs_redraw = False

            # --- INPUT UTENTE ---
            key = read_key(fd, timeout=0.08)
            if key is None:
                continue

            needs_redraw = True
            if key in ('UP', 'k', 'K'):
                cursor_idx = max(0, cursor_idx - 1)
            elif key in ('DOWN', 'j', 'J'):
                cursor_idx = min(len(selectable_indices) - 1, cursor_idx + 1)
            elif key == 'PAGE_UP':
                cursor_idx = max(0, cursor_idx - 5)
            elif key == 'PAGE_DOWN':
                cursor_idx = min(len(selectable_indices) - 1, cursor_idx + 5)
            elif key == 'HOME':
                cursor_idx = 0
            elif key == 'END':
                cursor_idx = len(selectable_indices) - 1
            elif key == 'SPACE':
                active_module.selected = not active_module.selected
                persist_current_state()
            elif key == 'RIGHT':
                active_module.selected = True
                persist_current_state()
            elif key == 'LEFT':
                active_module.selected = False
                persist_current_state()
            elif key in ('a', 'A'):
                for m in modules:
                    if m.risk_level != "caution":
                        m.selected = True
                persist_current_state()
            elif key in ('n', 'N'):
                for m in modules:
                    m.selected = False
                persist_current_state()
            elif key in ('d', 'D'):
                dry_run = not dry_run
                persist_current_state()
            elif key in ('s', 'S'):
                for m in modules:
                    m.scan_done = False
                start_background_scanner(modules)
            elif key in ('q', 'Q', 'ESC'):
                persist_current_state()
                if prev_rendered_lines > 0:
                    sys.stdout.write(f"\r\033[{prev_rendered_lines}A\033[0J")
                    sys.stdout.flush()
                return False, dry_run, modules
            elif key == 'ENTER':
                persist_current_state()
                sel_count = sum(1 for m in modules if m.selected)
                if sel_count == 0:
                    continue
                if prev_rendered_lines > 0:
                    sys.stdout.write(f"\r\033[{prev_rendered_lines}A\033[0J")
                    sys.stdout.flush()
                return True, dry_run, modules

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write("\033[?25h")  # Ripristina cursore
        sys.stdout.flush()

    return False, dry_run, modules


# ==============================================================================
# MOTORE DI ESECUZIONE PULIZIA (CLI & POST-TUI)
# ==============================================================================

def execute_cleaning(selected_modules: List[ModuleDef], dry_run: bool) -> List[CleanResult]:
    """Esegue la sequenza di moduli selezionati e stampa l'output dettagliato."""
    results: List[CleanResult] = []
    total_reclaimed = 0

    print("\n" + colorize("=" * 72, Colors.BOLD))
    print(colorize(" 🧹 Mac Developer Cleaner & Optimizer", Colors.HEADER + Colors.BOLD))
    if dry_run:
        print(colorize(" 🔍 MODALITÀ DRY-RUN (Simulazione - Nessun file verrà modificato)", Colors.YELLOW + Colors.BOLD))
    else:
        print(colorize(" ⚡ MODALITÀ DIRETTA (Eliminazione e ottimizzazione in corso)", Colors.GREEN + Colors.BOLD))
    print(colorize("=" * 72, Colors.BOLD) + "\n")

    for idx, mod in enumerate(selected_modules, 1):
        prefix = f"[{idx}/{len(selected_modules)}]"
        print(colorize(f"▶ {prefix} {mod.name}...", Colors.BOLD))
        try:
            res = mod.clean_func(dry_run)
        except Exception as e:
            res = CleanResult(mod.name)
            res.add_detail(f"Errore durante l'esecuzione del modulo: {e}")

        results.append(res)
        total_reclaimed += res.freed_bytes

        for detail in res.details:
            print(f"   {colorize('•', Colors.CYAN)} {detail}")
        print()

    print(colorize("-" * 72, Colors.DIM))
    tag = "Spazio recuperabile stimato:" if dry_run else "Spazio totale liberato:"
    print(colorize(f" 💾 {tag} {format_bytes(total_reclaimed)}", Colors.BOLD + Colors.GREEN))
    print(colorize("-" * 72, Colors.DIM))

    if dry_run:
        print(colorize("\nℹ️  Per applicare realmente questa pulizia sul sistema, avvia:", Colors.CYAN))
        print(colorize("    ./clean_mac.py --yes\n", Colors.BOLD))
    else:
        print(colorize("\n✨ Pulizia e ottimizzazione completate con successo!\n", Colors.BOLD + Colors.GREEN))

    return results


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="clean_mac.py - Pulizia e ottimizzazione disco/RAM per MacBook (Apple Silicon & Intel)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi di utilizzo:
  ./clean_mac.py                     # Avvia la lista interattiva con checkmark (TUI)
  ./clean_mac.py --dry-run           # Esegue la simulazione in modalità CLI
  ./clean_mac.py --yes               # Esegue la pulizia automatica completa in CLI
  ./clean_mac.py --only deriveddata,brew,trash --dry-run
  ./clean_mac.py --list              # Elenca tutti i moduli disponibili e le descrizioni
"""
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Esegue solo una simulazione senza cancellare o modificare file."
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Esegue la pulizia in modalità non interattiva (CLI) senza chiedere conferma."
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Forza l'avvio della Terminal UI (TUI) interattiva."
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Forza la modalità CLI senza interfaccia interattiva."
    )
    parser.add_argument(
        "--only",
        type=str,
        help="Esegui solo specifici ID di moduli (separati da virgola). Usa --list per vederli."
    )
    parser.add_argument(
        "--skip",
        type=str,
        help="Salta specifici ID di moduli (separati da virgola)."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Elenca tutti i moduli di pulizia disponibili e termina."
    )
    parser.add_argument(
        "--purge-ram",
        action="store_true",
        help="Forza l'esecuzione del purge della cache RAM al termine."
    )

    args = parser.parse_args()

    # Inizializza tutti i moduli e applica selezioni persistenti
    all_modules = create_all_modules()
    saved_config = load_config()
    apply_saved_config_to_modules(all_modules, saved_config)

    # Determina stato iniziale dry-run (salvato o via flag)
    saved_dry_run = saved_config.get("dry_run", True)
    if args.dry_run:
        initial_dry_run = True
    elif args.yes:
        initial_dry_run = False
    else:
        initial_dry_run = saved_dry_run

    # Comando --list
    if args.list:
        print("\n" + colorize("Moduli di Pulizia Disponibili:", Colors.BOLD + Colors.HEADER))
        print(colorize("-" * 75, Colors.DIM))
        print(f"{'ID':<18} {'Rischio':<12} {'Stato':<10} {'Nome & Descrizione'}")
        print(colorize("-" * 75, Colors.DIM))
        for m in all_modules:
            stat_str = "Attivo [✔]" if m.selected else "Disattivo [ ]"
            print(f"{m.id:<18} {m.risk_level:<12} {stat_str:<10} {colorize(m.name, Colors.BOLD)}")
            print(f"   ↳ {colorize(m.description, Colors.DIM)}")
        print()
        return

    # Filtri --only e --skip
    if args.only:
        req = [k.strip().lower() for k in args.only.split(",") if k.strip()]
        for m in all_modules:
            m.selected = (m.id in req)
    if args.skip:
        to_skip = [k.strip().lower() for k in args.skip.split(",") if k.strip()]
        for m in all_modules:
            if m.id in to_skip:
                m.selected = False

    # Modalità di esecuzione (TUI vs CLI)
    use_tui = False
    if args.tui:
        use_tui = True
    elif args.cli or args.yes or args.only or args.skip or not sys.stdin.isatty():
        use_tui = False
    else:
        # Default in terminale interattivo: avvia TUI!
        use_tui = True

    if use_tui:
        confirmed, dry_run, configured_modules = run_interactive_tui(all_modules, dry_run_initial=initial_dry_run)
        if not confirmed:
            print("\nOperazione annullata. Nessuna modifica apportata.\n")
            os._exit(0)
        selected = [m for m in configured_modules if m.selected]
        if not selected:
            print("\nNessun modulo selezionato. Uscita.")
            return
        execute_cleaning(selected, dry_run=dry_run)
    else:
        # Modalità CLI diretta
        selected = [m for m in all_modules if m.selected]
        if not selected:
            print(colorize("Nessun modulo selezionato per l'esecuzione.", Colors.YELLOW))
            return

        dry_run = args.dry_run if args.dry_run else initial_dry_run
        if not dry_run and not args.yes:
            sel_ids = ", ".join([m.id for m in selected])
            print(f"\nModuli selezionati ({len(selected)}): {colorize(sel_ids, Colors.CYAN)}")
            ans = input("Confermi di voler procedere con l'eliminazione effettiva? [s/N]: ").strip().lower()
            if ans not in ['s', 'si', 'sì', 'y', 'yes']:
                print("Operazione annullata.")
                return

        execute_cleaning(selected, dry_run=dry_run)


if __name__ == "__main__":
    main()

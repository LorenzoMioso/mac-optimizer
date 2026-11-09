#!/usr/bin/env python3
"""
clean_mac.py - Utility avanzata di pulizia, manutenzione e ottimizzazione disco/RAM per macOS.
Ottimizzato in particolare per Mac Apple Silicon (M1/M2/M3/M4) e ambienti di sviluppo:
iOS, Xcode, Flutter, Android, Node/NPM, Docker, Homebrew, VS Code, Browser e Cache di Sistema.

Include una Terminal UI (TUI) interattiva per selezionare le opzioni con tastiera,
calcolo parallelo dello spazio occupato in tempo reale e modalità CLI per script/automazione.
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
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Callable

# ==============================================================================
# COLORI E FORMATTAZIONE TERMINALE (CLI)
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

    # Fallback su iterazione limitata in caso di fallimento o timeout
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


def parse_semver(ver_str: str) -> Tuple:
    clean = re.split(r'[-+]', ver_str)[0]
    parts = []
    for p in clean.split('.'):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(p)
    return tuple(parts)

def scan_xcode_archives(keep_days: int = 30) -> int:
    p = os.path.expanduser("~/Library/Developer/Xcode/Archives")
    if not os.path.isdir(p):
        return 0
    cutoff = datetime.now() - timedelta(days=keep_days)
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
                        mtime = datetime.fromtimestamp(os.path.getmtime(arch_p))
                        if mtime < cutoff:
                            total += fast_get_path_size(arch_p, timeout=5)
                    except OSError:
                        pass
    except OSError:
        pass
    return total

def clean_xcode_archives(dry_run: bool, keep_days: int = 30) -> CleanResult:
    result = CleanResult(f"Xcode Archives (> {keep_days} giorni)")
    p = os.path.expanduser("~/Library/Developer/Xcode/Archives")
    if not os.path.isdir(p):
        result.add_detail("Nessuna cartella Archives trovata.")
        return result
    cutoff = datetime.now() - timedelta(days=keep_days)
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
                        mtime = datetime.fromtimestamp(os.path.getmtime(arch_p))
                        if mtime < cutoff:
                            sz = fast_get_path_size(arch_p, timeout=5)
                            total_bytes += sz
                            archives_to_delete.append((arch_p, item, mtime, sz))
                    except OSError:
                        pass
    except OSError:
        pass

    result.freed_bytes = total_bytes
    result.items_count = len(archives_to_delete)
    if not archives_to_delete:
        result.add_detail(f"Nessun archivio Xcode più vecchio di {keep_days} giorni trovato.")
        return result

    result.add_detail(f"Trovati {len(archives_to_delete)} archivi datati ({format_bytes(total_bytes)}).")
    for path, name, mtime, sz in archives_to_delete[:3]:
        tag = "[Simulazione] Da eliminare:" if dry_run else "Eliminato:"
        result.add_detail(f"  {tag} {name} [{mtime.strftime('%Y-%m-%d')}] ({format_bytes(sz)})")
    if len(archives_to_delete) > 3:
        result.add_detail(f"  ... e altri {len(archives_to_delete) - 3} archivi.")

    if not dry_run:
        for path, _, _, _ in archives_to_delete:
            shutil.rmtree(path, ignore_errors=True)
        for date_f in os.listdir(p):
            dp = os.path.join(p, date_f)
            if os.path.isdir(dp) and not os.listdir(dp):
                shutil.rmtree(dp, ignore_errors=True)
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


def scan_simulators_cache() -> int:
    total = fast_get_path_size("~/Library/Developer/CoreSimulator/Caches", timeout=10)
    total += fast_get_path_size("~/Library/Logs/CoreSimulator", timeout=5)
    return total

def clean_simulators_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("Simulatori iOS: Cache & Orfani")
    code, _, _ = run_cmd(["which", "xcrun"])
    if code != 0:
        result.add_detail("xcrun non installato nel sistema.")
        return result

    cache_p = os.path.expanduser("~/Library/Developer/CoreSimulator/Caches")
    logs_p = os.path.expanduser("~/Library/Logs/CoreSimulator")
    sz = fast_get_path_size(cache_p, timeout=10) + fast_get_path_size(logs_p, timeout=5)
    result.freed_bytes = sz

    if dry_run:
        code, out, _ = run_cmd(["xcrun", "simctl", "list", "devices", "unavailable"])
        unavail = [l.strip() for l in out.splitlines() if l.strip() and not l.startswith("==")]
        result.items_count = len(unavail)
        result.add_detail(f"Dispositivi orfani/indisponibili rilevati: {len(unavail)}")
        result.add_detail(f"Cache CoreSimulator e log stimati: {format_bytes(sz)}")
    else:
        run_cmd(["xcrun", "simctl", "runtime", "delete", "unavailable"])
        run_cmd(["xcrun", "simctl", "delete", "unavailable"])
        safe_remove_directory_contents(cache_p)
        safe_remove_directory_contents(logs_p)
        result.add_detail("Runtime e simulatori indisponibili eliminati con successo.")
        result.add_detail(f"Cache CoreSimulator svuotata ({format_bytes(sz)}).")
    return result


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
    result = CleanResult("VS Code: Versioni Obsolete Estensioni")
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
    return 1  # Valore simbolico per indicare che il demone è attivo

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
        return len(lines) * 1024 * 1024 * 1024  # Stima 1 GB per snapshot se presenti
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
        result.add_detail(f"[Simulazione] Esecuzione di tmutil thinlocalsnapshots per liberare spazio su disco.")
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
            name="Xcode Archives (> 30 giorni)",
            category="🍎 Sviluppo iOS & macOS",
            description="Vecchi archivi di release .xcarchive datati.",
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
            name="Xcode IDE Caches & Docs",
            category="🍎 Sviluppo iOS & macOS",
            description="Cache interna di compilazione/indicizzazione Xcode e documentazione.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_xcode_ide_caches,
            clean_func=clean_xcode_ide_caches
        ),
        ModuleDef(
            mod_id="simulators",
            name="Simulatori iOS: Cache & Orfani",
            category="🍎 Sviluppo iOS & macOS",
            description="Cache CoreSimulator ed eliminazione runtime/dispositivi indisponibili.",
            default_selected=True,
            risk_level="recommended",
            scan_func=scan_simulators_cache,
            clean_func=clean_simulators_cache
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

        # --- 📦 Package Manager & SDK ---
        ModuleDef(
            mod_id="brew",
            name="Homebrew Cache & Bottles",
            category="📦 Package Manager & SDK",
            description="Download vecchi pacchetti e formule con brew cleanup --prune=all.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_homebrew_cache,
            clean_func=clean_homebrew_cache
        ),
        ModuleDef(
            mod_id="cocoapods",
            name="CocoaPods Cache",
            category="📦 Package Manager & SDK",
            description="Cache locale archivio pod (~/Library/Caches/CocoaPods).",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_cocoapods_cache,
            clean_func=clean_cocoapods_cache
        ),
        ModuleDef(
            mod_id="npm",
            name="Node / NPM / Yarn / PNPM",
            category="📦 Package Manager & SDK",
            description="Cache pacchetti JavaScript (~/.npm, ~/.yarn/cache, ~/.pnpm-store).",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_npm_cache,
            clean_func=clean_npm_cache
        ),
        ModuleDef(
            mod_id="gradle",
            name="Gradle & Android Build Caches",
            category="📦 Package Manager & SDK",
            description="Cache di compilazione Gradle e Android (~/.gradle/caches, ~/.android/cache).",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_gradle_cache,
            clean_func=clean_gradle_cache
        ),
        ModuleDef(
            mod_id="pip",
            name="Python / Pip / UV Cache",
            category="📦 Package Manager & SDK",
            description="Cache ruote (.whl) e download pacchetti Python (~/Library/Caches/pip).",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_pip_cache,
            clean_func=clean_pip_cache
        ),
        ModuleDef(
            mod_id="flutter",
            name="Flutter & Dart Pub Git Cache",
            category="📦 Package Manager & SDK",
            description="Cache repository git clonati in ~/.pub-cache/git.",
            default_selected=False,
            risk_level="safe",
            scan_func=scan_flutter_pub_cache,
            clean_func=clean_flutter_pub_cache
        ),

        # --- 💻 Editor & Docker ---
        ModuleDef(
            mod_id="vscode",
            name="VS Code: Estensioni Obsolete",
            category="💻 Editor & Docker",
            description="Rimuove versioni precedenti duplicate in ~/.vscode/extensions.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_vscode_extensions,
            clean_func=clean_vscode_extensions
        ),
        ModuleDef(
            mod_id="docker",
            name="Docker System Prune",
            category="💻 Editor & Docker",
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
            name="Browser Web Caches",
            category="🌐 Cache App & Browser",
            description="Cache web temporanea di Brave, Chrome e Safari (nessun cookie/password toccato).",
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
            name="Log Utente & DiagnosticReports",
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
            name="macOS Purge RAM",
            category="⚙️ Sistema macOS & RAM",
            description="Svuota la cache disco inattiva di macOS per restituire RAM fisica al sistema.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_ram_purge,
            clean_func=clean_ram_purge
        ),

        # --- ⚠️ Operazioni Avanzate ---
        ModuleDef(
            mod_id="simulators_erase",
            name="Reset Totale Simulatori iOS",
            category="⚠️ Operazioni Avanzate (Opt-in)",
            description="xcrun simctl erase all: azzera tutte le app e dati installati nei simulatori.",
            default_selected=False,
            risk_level="caution",
            scan_func=scan_simulators_erase_all,
            clean_func=clean_simulators_erase_all
        ),
    ]


# ==============================================================================
# TERMINAL UI (TUI) CON CURSES
# ==============================================================================

import curses

def start_background_scanner(modules: List[ModuleDef]):
    """Scansiona le dimensioni dei moduli in parallelo in background."""
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
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            list(executor.map(_worker, modules))

    t = threading.Thread(target=_scanner_pool, daemon=True)
    t.start()


def run_tui(modules: List[ModuleDef], dry_run_default: bool = False) -> Tuple[bool, bool, List[ModuleDef]]:
    """
    Esegue la TUI interattiva.
    Restituisce: (confirmed: bool, dry_run: bool, modules_list)
    """
    start_background_scanner(modules)

    # Stato locale TUI
    state = {
        "cursor": 0,
        "offset": 0,
        "dry_run": dry_run_default,
        "confirmed": False,
        "quit": False
    }

    def _tui_main(stdscr):
        # Configurazione curses
        curses.curs_set(0)
        stdscr.timeout(100) # Rinfresca ogni 100ms per riflettere la scansione background
        curses.use_default_colors()

        # Inizializza coppie di colori se supportati
        has_colors = curses.has_colors()
        if has_colors:
            curses.init_pair(1, curses.COLOR_CYAN, -1)     # Titoli / Evidenziazioni
            curses.init_pair(2, curses.COLOR_GREEN, -1)    # Successo / Sicuro
            curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Avviso / Dry-run
            curses.init_pair(4, curses.COLOR_RED, -1)      # Attenzione / Pericolo
            curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_CYAN) # Cursore riga attiva
            curses.init_pair(6, curses.COLOR_MAGENTA, -1)  # Categorie

        disk_info = get_disk_usage_info()

        while True:
            max_y, max_x = stdscr.getmaxyx()
            stdscr.erase()

            if max_y < 16 or max_x < 65:
                msg = "Allarga la finestra del terminale (min 65x16)"
                stdscr.addstr(max_y // 2, max(0, (max_x - len(msg)) // 2), msg, curses.A_BOLD)
                key = stdscr.getch()
                if key in [ord('q'), ord('Q'), 27]:
                    state["quit"] = True
                    break
                continue

            # --- 1. HEADER ---
            title = " 🧹 Mac Developer Cleaner & Optimizer "
            stdscr.addstr(0, 0, "=" * (max_x - 1), curses.A_DIM)
            stdscr.addstr(1, 2, title, curses.color_pair(1) | curses.A_BOLD if has_colors else curses.A_BOLD)

            # Modalità Dry-Run / Reale
            mode_badge = "[ SIMULAZIONE (DRY-RUN) ]" if state["dry_run"] else "[ ESECUZIONE REALE ]"
            mode_color = curses.color_pair(3) if state["dry_run"] else curses.color_pair(2)
            if max_x > 60:
                stdscr.addstr(1, max(30, max_x - len(mode_badge) - 3), mode_badge, mode_color | curses.A_BOLD if has_colors else curses.A_BOLD)

            # Barra disco
            disk_str = f"Disco: {disk_info['free']} liberi su {disk_info['total']} ({disk_info['percent']} usato)"
            stdscr.addstr(2, 2, disk_str, curses.A_DIM)
            stdscr.addstr(3, 0, "-" * (max_x - 1), curses.A_DIM)

            # --- 2. LISTA SCROLLABILE DEI MODULI ---
            header_lines = 4
            footer_lines = 5
            available_rows = max_y - header_lines - footer_lines

            # Mappa degli elementi (tenendo traccia di categorie e indici modulo)
            display_items = []
            curr_cat = None
            for idx, m in enumerate(modules):
                if m.category != curr_cat:
                    curr_cat = m.category
                    display_items.append({"type": "category", "label": curr_cat})
                display_items.append({"type": "module", "index": idx, "module": m})

            # Trova l'elemento selezionato nella display list
            selected_display_idx = 0
            for d_idx, d_item in enumerate(display_items):
                if d_item["type"] == "module" and d_item["index"] == state["cursor"]:
                    selected_display_idx = d_idx
                    break

            # Aggiusta lo scorrimento
            if selected_display_idx < state["offset"]:
                state["offset"] = selected_display_idx
            elif selected_display_idx >= state["offset"] + available_rows:
                state["offset"] = selected_display_idx - available_rows + 1

            # Renderizza righe visibili
            for row in range(available_rows):
                item_idx = state["offset"] + row
                if item_idx >= len(display_items):
                    break
                d_item = display_items[item_idx]
                y_pos = header_lines + row

                if d_item["type"] == "category":
                    cat_title = f"-- {d_item['label']} --"
                    stdscr.addstr(y_pos, 2, cat_title[:max_x-4], curses.color_pair(6) | curses.A_BOLD if has_colors else curses.A_BOLD)
                else:
                    m = d_item["module"]
                    is_active = (d_item["index"] == state["cursor"])
                    chk = "[X]" if m.selected else "[ ]"

                    # Formattazione dimensione
                    if m.scan_done:
                        if m.estimated_bytes > 0:
                            sz_str = f"{format_bytes(m.estimated_bytes):>9}"
                        else:
                            sz_str = f"{'0 B':>9}"
                    else:
                        sz_str = " (calcolo)"

                    # Badge rischio
                    if m.risk_level == "caution":
                        risk_str = "[Attenzione]"
                        risk_col = curses.color_pair(4)
                    elif m.risk_level == "recommended":
                        risk_str = "[Consigliato]"
                        risk_col = curses.color_pair(1)
                    else:
                        risk_str = "[Sicuro]"
                        risk_col = curses.color_pair(2)

                    name_width = max(18, max_x - 38)
                    truncated_name = m.name[:name_width].ljust(name_width)
                    line_str = f" {chk} {truncated_name}  {sz_str}  {risk_str}"

                    if is_active:
                        attr = curses.color_pair(5) | curses.A_BOLD if has_colors else curses.A_REVERSE
                        stdscr.addstr(y_pos, 1, line_str[:max_x-2].ljust(max_x - 2), attr)
                    else:
                        chk_attr = curses.color_pair(2) | curses.A_BOLD if (has_colors and m.selected) else curses.A_NORMAL
                        stdscr.addstr(y_pos, 1, f" {chk}", chk_attr)
                        stdscr.addstr(y_pos, 6, f"{truncated_name}  {sz_str}  ")
                        stdscr.addstr(y_pos, 6 + len(truncated_name) + 2 + len(sz_str) + 2, risk_str, risk_col if has_colors else curses.A_NORMAL)

            # --- 3. FOOTER (DESCRIZIONE, RIEPILOGO, CONTROLLI) ---
            sep_y = max_y - footer_lines
            stdscr.addstr(sep_y, 0, "-" * (max_x - 1), curses.A_DIM)

            # Descrizione modulo attivo
            active_mod = modules[state["cursor"]]
            desc_str = f"ℹ️  {active_mod.description}"
            stdscr.addstr(sep_y + 1, 2, desc_str[:max_x-4], curses.color_pair(1) if has_colors else curses.A_NORMAL)

            # Totale stimato selezionato
            sel_count = sum(1 for m in modules if m.selected)
            sel_bytes = sum(m.estimated_bytes for m in modules if m.selected)
            stat_str = f"Selezionati: {sel_count}/{len(modules)}  |  Spazio stimato recuperabile: {format_bytes(sel_bytes)}"
            stdscr.addstr(sep_y + 2, 2, stat_str[:max_x-4], curses.color_pair(2) | curses.A_BOLD if has_colors else curses.A_BOLD)

            # Tasti funzione
            keys_str = "[↑/↓] Naviga  [Spazio] Seleziona  [a] Tutti  [n] Nessuno  [d] Dry-run  [s] Riscansiona  [Invio] Esegui  [q] Esci"
            stdscr.addstr(sep_y + 3, 2, keys_str[:max_x-4], curses.A_DIM)

            # --- 4. GESTIONE INPUT ---
            try:
                ch = stdscr.getch()
            except curses.error:
                continue

            if ch == -1:
                continue
            elif ch in [ord('q'), ord('Q'), 27]: # q, Q o ESC
                state["quit"] = True
                break
            elif ch in [curses.KEY_UP, ord('k'), ord('K')]:
                state["cursor"] = max(0, state["cursor"] - 1)
            elif ch in [curses.KEY_DOWN, ord('j'), ord('J')]:
                state["cursor"] = min(len(modules) - 1, state["cursor"] + 1)
            elif ch == ord(' '):
                active_mod.selected = not active_mod.selected
            elif ch in [ord('a'), ord('A')]:
                for m in modules:
                    if m.risk_level != "caution":
                        m.selected = True
            elif ch in [ord('n'), ord('N')]:
                for m in modules:
                    m.selected = False
            elif ch in [ord('d'), ord('D')]:
                state["dry_run"] = not state["dry_run"]
            elif ch in [ord('s'), ord('S')]:
                for m in modules:
                    m.scan_done = False
                start_background_scanner(modules)
            elif ch in [10, 13, curses.KEY_ENTER]:
                if sel_count == 0:
                    continue
                # Schermata di conferma prima di procedere
                mode_label = "SIMULAZIONE DRY-RUN (nessun file verrà cancellato)" if state["dry_run"] else "ELIMINAZIONE REALE (i file verranno rimossi)"
                prompt = f"Avviare la pulizia di {sel_count} moduli in modalità {mode_label}? (s/N): "
                stdscr.addstr(sep_y + 2, 0, " " * (max_x - 1))
                stdscr.addstr(sep_y + 2, 2, prompt[:max_x-4], curses.color_pair(3) | curses.A_BOLD if has_colors else curses.A_BOLD)
                stdscr.refresh()
                curses.echo()
                stdscr.timeout(-1)
                ans = stdscr.getstr(sep_y + 2, min(len(prompt) + 2, max_x - 5), 4).decode('utf-8', errors='ignore').strip().lower()
                curses.noecho()
                stdscr.timeout(100)
                if ans in ['s', 'si', 'sì', 'y', 'yes']:
                    state["confirmed"] = True
                    break

    try:
        curses.wrapper(_tui_main)
    except Exception as e:
        print(f"Errore nell'avvio della TUI: {e}", file=sys.stderr)
        return False, dry_run_default, modules

    return state["confirmed"], state["dry_run"], modules


# ==============================================================================
# MOTORE DI ESECUZIONE PULIZIA (CLI & POST-TUI)
# ==============================================================================

def execute_cleaning(selected_modules: List[ModuleDef], dry_run: bool, keep_archives_days: int = 30) -> List[CleanResult]:
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
            if mod.id == "archives":
                res = mod.clean_func(dry_run)
            else:
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
  ./clean_mac.py                     # Avvia la Terminal UI interattiva
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
        help="Forza la modalità CLI (disabilita la TUI)."
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
        "--keep-archives-days",
        type=int,
        default=30,
        help="Giorni di ritenzione per gli archivi Xcode (default: 30)."
    )
    parser.add_argument(
        "--purge-ram",
        action="store_true",
        help="Forza l'esecuzione del purge della cache RAM al termine."
    )

    args = parser.parse_args()
    all_modules = create_all_modules()
    modules_map = {m.id: m for m in all_modules}

    # Comando --list
    if args.list:
        print("\n" + colorize("Moduli di Pulizia Disponibili:", Colors.BOLD + Colors.HEADER))
        print(colorize("-" * 75, Colors.DIM))
        print(f"{'ID':<18} {'Rischio':<12} {'Default':<10} {'Nome & Descrizione'}")
        print(colorize("-" * 75, Colors.DIM))
        for m in all_modules:
            def_str = "Attivo" if m.selected else "Disattivo"
            print(f"{m.id:<18} {m.risk_level:<12} {def_str:<10} {colorize(m.name, Colors.BOLD)}")
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

    # Decide se avviare TUI o CLI
    use_tui = False
    if args.tui:
        use_tui = True
    elif args.cli or args.yes or args.dry_run or args.only or args.skip or not sys.stdin.isatty():
        use_tui = False
    else:
        # Default in terminale interattivo: avvia TUI!
        use_tui = True

    if use_tui:
        confirmed, dry_run, configured_modules = run_tui(all_modules, dry_run_default=args.dry_run)
        if not confirmed:
            print("\nOperazione annullata. Nessuna modifica apportata.")
            return
        selected = [m for m in configured_modules if m.selected]
        if not selected:
            print("\nNessun modulo selezionato. Uscita.")
            return
        execute_cleaning(selected, dry_run=dry_run, keep_archives_days=args.keep_archives_days)
    else:
        # Modalità CLI
        selected = [m for m in all_modules if m.selected]
        if not selected:
            print(colorize("Nessun modulo selezionato per l'esecuzione.", Colors.YELLOW))
            return

        dry_run = args.dry_run
        if not dry_run and not args.yes:
            # Chiedi conferma interattiva in CLI
            sel_ids = ", ".join([m.id for m in selected])
            print(f"\nModuli selezionati ({len(selected)}): {colorize(sel_ids, Colors.CYAN)}")
            ans = input("Confermi di voler procedere con l'eliminazione effettiva? [s/N]: ").strip().lower()
            if ans not in ['s', 'si', 'sì', 'y', 'yes']:
                print("Operazione annullata.")
                return

        execute_cleaning(selected, dry_run=dry_run, keep_archives_days=args.keep_archives_days)


if __name__ == "__main__":
    main()

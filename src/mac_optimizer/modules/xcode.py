"""
modules/xcode.py - Moduli di pulizia specifici per Xcode, DerivedData, Archivi e DeviceSupport.
"""

import os
import shutil
from datetime import datetime
from mac_optimizer.models import CleanResult
from mac_optimizer.utils import fast_get_path_size, safe_remove_directory_contents, format_bytes


def scan_xcode_deriveddata() -> int:
    return fast_get_path_size("~/Library/Developer/Xcode/DerivedData", timeout=10)


def clean_xcode_deriveddata(dry_run: bool) -> CleanResult:
    result = CleanResult("Xcode DerivedData")
    p = os.path.expanduser("~/Library/Developer/Xcode/DerivedData")
    if not os.path.isdir(p):
        result.add_detail("Cartella DerivedData non presente.")
        return result
    size = fast_get_path_size(p, timeout=10)
    result.freed_bytes = size
    if dry_run:
        result.add_detail(f"[Simulazione] Spazio stimato da liberare in DerivedData: {format_bytes(size)}")
    else:
        cnt, _ = safe_remove_directory_contents(p)
        result.items_count = cnt
        result.add_detail(f"DerivedData ripulita con successo ({format_bytes(size)} liberati).")
    return result


def scan_xcode_archives() -> int:
    return fast_get_path_size("~/Library/Developer/Xcode/Archives", timeout=10)


def clean_xcode_archives(dry_run: bool) -> CleanResult:
    """Elimina TUTTI gli archivi .xcarchive generati da Xcode in passato."""
    result = CleanResult("Xcode Archives (TUTTI gli archivi)")
    p = os.path.expanduser("~/Library/Developer/Xcode/Archives")
    if not os.path.isdir(p):
        result.add_detail("Nessuna cartella Archives trovata.")
        return result

    archives_to_delete = []
    total_bytes = 0
    try:
        for root, dirs, _ in os.walk(p):
            for d in list(dirs):
                if d.endswith(".xcarchive"):
                    arch_path = os.path.join(root, d)
                    dirs.remove(d)
                    sz = fast_get_path_size(arch_path, timeout=5)
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(arch_path))
                    except Exception:
                        mtime = datetime.now()
                    archives_to_delete.append((arch_path, d, mtime, sz))
                    total_bytes += sz
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

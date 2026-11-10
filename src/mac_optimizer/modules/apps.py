"""
modules/apps.py - Pulizia cache applicazioni e browser (Spotify, Google Chrome, Brave, Safari).
Tutte le operazioni preservano rigorosamente login, password, segnalibri e sessioni.
"""

import os
from mac_optimizer.models import CleanResult
from mac_optimizer.utils import fast_get_path_size, safe_remove_directory_contents, format_bytes


def scan_spotify_cache() -> int:
    return fast_get_path_size("~/Library/Caches/com.spotify.client", timeout=5)


def clean_spotify_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("Spotify Streaming Cache")
    p = os.path.expanduser("~/Library/Caches/com.spotify.client")
    if not os.path.isdir(p):
        result.add_detail("Cartella cache Spotify non trovata.")
        return result
    sz = fast_get_path_size(p, timeout=5)
    result.freed_bytes = sz
    if dry_run:
        result.add_detail(f"[Simulazione] Cache streaming Spotify rimovibile: {format_bytes(sz)}")
        result.add_detail("  (Nessun dato di login o playlist verrà perso)")
    else:
        cnt, _ = safe_remove_directory_contents(p)
        result.items_count = cnt
        result.add_detail(f"Cache brani in streaming Spotify svuotata ({format_bytes(sz)} liberati).")
    return result


def scan_browser_caches() -> int:
    browser_cache_paths = [
        "~/Library/Caches/Google/Chrome",
        "~/Library/Caches/BraveSoftware/Brave-Browser",
        "~/Library/Caches/com.apple.Safari"
    ]
    total = 0
    for bp in browser_cache_paths:
        total += fast_get_path_size(bp, timeout=5)
    return total


def clean_browser_caches(dry_run: bool) -> CleanResult:
    result = CleanResult("Browser Web Caches (Brave, Chrome, Safari)")
    browser_cache_paths = [
        ("Google Chrome", "~/Library/Caches/Google/Chrome"),
        ("Brave Browser", "~/Library/Caches/BraveSoftware/Brave-Browser"),
        ("Apple Safari", "~/Library/Caches/com.apple.Safari")
    ]
    total_sz = 0
    found_any = False
    for bname, bp in browser_cache_paths:
        p = os.path.expanduser(bp)
        if os.path.isdir(p):
            found_any = True
            sz = fast_get_path_size(p, timeout=5)
            total_sz += sz
            if dry_run:
                result.add_detail(f"[Simulazione] {bname}: {format_bytes(sz)} di file web temporanei.")
            else:
                safe_remove_directory_contents(p)
                result.add_detail(f"{bname}: cache web eliminata ({format_bytes(sz)}).")

    result.freed_bytes = total_sz
    if not found_any:
        result.add_detail("Nessuna cache dei browser supportati trovata.")
    else:
        result.add_detail("Nota di sicurezza: cookie, credenziali salvate, segnalibri e cronologia restano intatti al 100%.")
    return result

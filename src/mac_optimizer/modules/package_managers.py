"""
modules/package_managers.py - Pulizia cache gestori di pacchetti e SDK di sviluppo:
SwiftPM, Homebrew, CocoaPods, NPM/Yarn/PNPM, Gradle/Android, Pip/UV, Flutter/Dart.
"""

import os
from mac_optimizer.models import CleanResult
from mac_optimizer.utils import run_cmd, fast_get_path_size, safe_remove_directory_contents, format_bytes


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
        result.add_detail(f"[Simulazione] Spazio stimato da liberare in cache SwiftPM: {format_bytes(sz)}")
    else:
        cnt, _ = safe_remove_directory_contents(p)
        result.items_count = cnt
        result.add_detail(f"Cache SwiftPM svuotata ({format_bytes(sz)}).")
    return result


def scan_homebrew_cache() -> int:
    code, out, _ = run_cmd(["which", "brew"])
    if code != 0:
        return 0
    p = os.path.expanduser("~/Library/Caches/Homebrew")
    return fast_get_path_size(p, timeout=10)


def clean_homebrew_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("Homebrew Cache & Bottles")
    code, _, _ = run_cmd(["which", "brew"])
    if code != 0:
        result.add_detail("Homebrew non installato nel sistema.")
        return result
    p = os.path.expanduser("~/Library/Caches/Homebrew")
    sz = fast_get_path_size(p, timeout=10)
    result.freed_bytes = sz
    if dry_run:
        code, out, _ = run_cmd(["brew", "cleanup", "-n", "--prune=all"])
        lines = [l for l in out.splitlines() if l.strip()]
        result.items_count = len(lines)
        result.add_detail(f"[Simulazione] brew cleanup troverebbe ~{len(lines)} elementi obsoleti.")
        result.add_detail(f"Dimensione cartella cache Homebrew: {format_bytes(sz)}")
    else:
        code, out, err = run_cmd(["brew", "cleanup", "--prune=all"])
        result.add_detail(f"Comando 'brew cleanup --prune=all' completato.")
        safe_remove_directory_contents(p)
        result.add_detail(f"Cache temporanea download ripulita ({format_bytes(sz)}).")
    return result


def scan_cocoapods_cache() -> int:
    return fast_get_path_size("~/Library/Caches/CocoaPods", timeout=10)


def clean_cocoapods_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("CocoaPods Cache")
    p = os.path.expanduser("~/Library/Caches/CocoaPods")
    if not os.path.isdir(p):
        result.add_detail("Nessuna cache CocoaPods presente.")
        return result
    sz = fast_get_path_size(p, timeout=10)
    result.freed_bytes = sz
    if dry_run:
        result.add_detail(f"[Simulazione] Spazio stimato da liberare in CocoaPods: {format_bytes(sz)}")
    else:
        run_cmd(["pod", "cache", "clean", "--all"])
        safe_remove_directory_contents(p)
        result.add_detail(f"Cache CocoaPods svuotata ({format_bytes(sz)}).")
    return result


def scan_node_npm_caches() -> int:
    total = fast_get_path_size("~/.npm", timeout=10)
    total += fast_get_path_size("~/.yarn/cache", timeout=10)
    total += fast_get_path_size("~/.pnpm-store", timeout=10)
    total += fast_get_path_size("~/Library/Caches/Yarn", timeout=10)
    return total


def clean_node_npm_caches(dry_run: bool) -> CleanResult:
    result = CleanResult("Node / NPM / Yarn / PNPM Caches")
    paths = ["~/.npm/_cacache", "~/.yarn/cache", "~/Library/Caches/Yarn"]
    sz = 0
    for p in paths:
        sz += fast_get_path_size(p, timeout=10)
    result.freed_bytes = sz
    if dry_run:
        result.add_detail(f"[Simulazione] Spazio stimato cache JS (NPM/Yarn): {format_bytes(sz)}")
    else:
        code, _, _ = run_cmd(["which", "npm"])
        if code == 0:
            run_cmd(["npm", "cache", "clean", "--force"])
        for p in paths:
            safe_remove_directory_contents(p)
        result.add_detail(f"Cache NPM e Yarn ripulite ({format_bytes(sz)}).")
    return result


def scan_gradle_android_caches() -> int:
    total = fast_get_path_size("~/.gradle/caches", timeout=10)
    total += fast_get_path_size("~/.android/cache", timeout=10)
    total += fast_get_path_size("~/.android/build-cache", timeout=10)
    return total


def clean_gradle_android_caches(dry_run: bool) -> CleanResult:
    result = CleanResult("Gradle & Android Build Caches")
    paths = ["~/.gradle/caches", "~/.android/cache", "~/.android/build-cache"]
    total_sz = 0
    for p in paths:
        total_sz += fast_get_path_size(p, timeout=10)
    result.freed_bytes = total_sz
    if dry_run:
        result.add_detail(f"[Simulazione] Cache Gradle e Android eliminabili: {format_bytes(total_sz)}")
    else:
        for p in paths:
            safe_remove_directory_contents(p)
        result.add_detail(f"Cache di compilazione Gradle e Android svuotate ({format_bytes(total_sz)}).")
    return result


def scan_python_pip_cache() -> int:
    total = fast_get_path_size("~/Library/Caches/pip", timeout=10)
    total += fast_get_path_size("~/.cache/uv", timeout=10)
    return total


def clean_python_pip_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("Python / Pip / UV Cache")
    pip_c = os.path.expanduser("~/Library/Caches/pip")
    uv_c = os.path.expanduser("~/.cache/uv")
    sz = fast_get_path_size(pip_c, timeout=10) + fast_get_path_size(uv_c, timeout=10)
    result.freed_bytes = sz
    if dry_run:
        result.add_detail(f"[Simulazione] Cache ruote (.whl) Python e UV rimovibili: {format_bytes(sz)}")
    else:
        run_cmd(["pip", "cache", "purge"])
        run_cmd(["uv", "cache", "clean"])
        safe_remove_directory_contents(pip_c)
        safe_remove_directory_contents(uv_c)
        result.add_detail(f"Cache download Python e UV ripulite ({format_bytes(sz)}).")
    return result


def scan_flutter_cache() -> int:
    return fast_get_path_size("~/.pub-cache/git", timeout=10)


def clean_flutter_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("Flutter & Dart Pub Git Cache")
    p = os.path.expanduser("~/.pub-cache/git")
    if not os.path.isdir(p):
        result.add_detail("Cartella pub-cache git non presente.")
        return result
    sz = fast_get_path_size(p, timeout=10)
    result.freed_bytes = sz
    if dry_run:
        result.add_detail(f"[Simulazione] Repository Git clonati temporaneamente: {format_bytes(sz)}")
    else:
        cnt, _ = safe_remove_directory_contents(p)
        result.items_count = cnt
        result.add_detail(f"Clone temporanei Git di Dart/Flutter rimossi ({format_bytes(sz)}).")
    return result


def scan_dart_analysis_cache() -> int:
    p = os.path.expanduser("~/.dartServer/.analysis-driver")
    return fast_get_path_size(p, timeout=10)


def clean_dart_analysis_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("Dart Analysis Server Cache")
    p = os.path.expanduser("~/.dartServer/.analysis-driver")
    if not os.path.isdir(p):
        result.add_detail("Nessuna cache di analisi Dart trovata in ~/.dartServer/.analysis-driver.")
        return result
    sz = fast_get_path_size(p, timeout=10)
    result.freed_bytes = sz
    if dry_run:
        result.add_detail(f"[Simulazione] Cache analisi semantica Dart eliminabile: {format_bytes(sz)}")
        result.add_detail("  (Il Dart language server ricreerà la cache per i file attivi al prossimo avvio)")
    else:
        cnt, _ = safe_remove_directory_contents(p)
        result.items_count = cnt
        result.add_detail(f"Cache semantica Dart rimossa: liberati {format_bytes(sz)}.")
    return result


def scan_pub_hosted_cache() -> int:
    p = os.path.expanduser("~/.pub-cache/hosted")
    return fast_get_path_size(p, timeout=10)


def clean_pub_hosted_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("Dart / Flutter Pub Hosted Cache")
    p = os.path.expanduser("~/.pub-cache/hosted")
    if not os.path.isdir(p):
        result.add_detail("Nessuna cartella ~/.pub-cache/hosted trovata.")
        return result
    sz = fast_get_path_size(p, timeout=10)
    result.freed_bytes = sz
    if dry_run:
        result.add_detail(f"[Simulazione] Pacchetti hosted pub.dev rimovibili: {format_bytes(sz)}")
        result.add_detail("  (I pacchetti necessari ai progetti verranno riscaricati da pub.dev con 'flutter pub get')")
    else:
        cnt, _ = safe_remove_directory_contents(p)
        result.items_count = cnt
        result.add_detail(f"Cache pacchetti hosted di pub.dev rimossa: liberati {format_bytes(sz)}.")
    return result


def scan_gradle_wrappers() -> int:
    p = os.path.expanduser("~/.gradle/wrapper/dists")
    return fast_get_path_size(p, timeout=10)


def clean_gradle_wrappers(dry_run: bool) -> CleanResult:
    result = CleanResult("Gradle Wrapper Distributions")
    p = os.path.expanduser("~/.gradle/wrapper/dists")
    if not os.path.isdir(p):
        result.add_detail("Nessuna distribuzione Gradle trovata in ~/.gradle/wrapper/dists.")
        return result
    sz = fast_get_path_size(p, timeout=10)
    result.freed_bytes = sz
    if dry_run:
        result.add_detail(f"[Simulazione] Vecchie distribuzioni Gradle rimovibili: {format_bytes(sz)}")
    else:
        cnt, _ = safe_remove_directory_contents(p)
        result.items_count = cnt
        result.add_detail(f"Vecchie distribuzioni Gradle eliminate: liberati {format_bytes(sz)}.")
    return result

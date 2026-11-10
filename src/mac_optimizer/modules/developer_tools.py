"""
modules/developer_tools.py - Pulizia strumenti di sviluppo: VS Code estensioni obsolete e Docker Prune.
"""

import os
import shutil
from mac_optimizer.models import CleanResult
from mac_optimizer.utils import run_cmd, fast_get_path_size, format_bytes


def scan_vscode_extensions_cache() -> int:
    ext_dir = os.path.expanduser("~/.vscode/extensions")
    if not os.path.isdir(ext_dir):
        return 0
    dirs = [d for d in os.listdir(ext_dir) if os.path.isdir(os.path.join(ext_dir, d))]
    ext_map = {}
    for d in dirs:
        if "-" in d:
            parts = d.rsplit("-", 1)
            name = parts[0]
            ext_map.setdefault(name, []).append(d)
    obsolete_sz = 0
    for name, versions in ext_map.items():
        if len(versions) > 1:
            for v in versions[:-1]:
                obsolete_sz += fast_get_path_size(os.path.join(ext_dir, v), timeout=3)
    return obsolete_sz


def clean_vscode_extensions_cache(dry_run: bool) -> CleanResult:
    result = CleanResult("VS Code: Estensioni Obsolete")
    ext_dir = os.path.expanduser("~/.vscode/extensions")
    if not os.path.isdir(ext_dir):
        result.add_detail("Cartella estensioni VS Code non presente.")
        return result

    dirs = [d for d in os.listdir(ext_dir) if os.path.isdir(os.path.join(ext_dir, d))]
    ext_map = {}
    for d in dirs:
        if "-" in d:
            parts = d.rsplit("-", 1)
            name = parts[0]
            ext_map.setdefault(name, []).append(d)

    to_delete = []
    total_sz = 0
    for name, versions in ext_map.items():
        if len(versions) > 1:
            versions.sort()
            for v in versions[:-1]:
                vp = os.path.join(ext_dir, v)
                sz = fast_get_path_size(vp, timeout=3)
                total_sz += sz
                to_delete.append((v, sz))

    result.freed_bytes = total_sz
    result.items_count = len(to_delete)
    if not to_delete:
        result.add_detail("Nessuna versione obsoleta o duplicata di estensioni VS Code trovata.")
        return result

    if dry_run:
        result.add_detail(f"[Simulazione] Trovate {len(to_delete)} estensioni duplicate/obsolete ({format_bytes(total_sz)}):")
        for name, sz in to_delete[:5]:
            result.add_detail(f"  • {name} ({format_bytes(sz)})")
        if len(to_delete) > 5:
            result.add_detail(f"  ... e altre {len(to_delete) - 5} estensioni.")
    else:
        for name, _ in to_delete:
            shutil.rmtree(os.path.join(ext_dir, name), ignore_errors=True)
        result.add_detail(f"Rimosse {len(to_delete)} versioni precedenti di estensioni ({format_bytes(total_sz)}).")
    return result


def scan_docker_system_prune() -> int:
    code, _, _ = run_cmd(["which", "docker"])
    if code != 0:
        return 0
    code, out, _ = run_cmd(["docker", "system", "df"], timeout=5)
    if code != 0:
        return 0
    return 0


def clean_docker_system_prune(dry_run: bool) -> CleanResult:
    result = CleanResult("Docker System Prune")
    code, _, _ = run_cmd(["which", "docker"])
    if code != 0:
        result.add_detail("Docker non installato nel sistema.")
        return result

    code, out, _ = run_cmd(["docker", "info"], timeout=5)
    if code != 0:
        result.add_detail("Demone Docker non attivo in questo momento.")
        return result

    if dry_run:
        code, out, _ = run_cmd(["docker", "system", "df"])
        result.add_detail("[Simulazione] Stato attuale risorse Docker:")
        for line in out.splitlines()[:6]:
            result.add_detail(f"  {line}")
    else:
        code, out, err = run_cmd(["docker", "system", "prune", "-a", "-f", "--volumes"], timeout=120)
        if code == 0:
            result.add_detail("docker system prune eseguito con successo su container, immagini e volumi orfani.")
        else:
            result.add_detail(f"docker system prune terminato con codice {code}: {err.strip()}")
    return result

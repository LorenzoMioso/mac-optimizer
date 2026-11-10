"""
modules/workspace.py - Pulizia degli artefatti di compilazione temporanei (build/ e .dart_tool/)
nei repository e progetti di sviluppo locali (es. ~/Documents/GitHub e ~/Documents/DEV).
"""

import os
from typing import List, Optional, Tuple
from mac_optimizer.models import CleanResult
from mac_optimizer.utils import fast_get_path_size, safe_remove_directory_contents, format_bytes

DEFAULT_WORKSPACE_ROOTS = [
    os.path.expanduser("~/Documents/GitHub"),
    os.path.expanduser("~/Documents/DEV"),
]

BUILD_SUBDIRS = ["build", ".dart_tool"]
PROJECT_MARKERS = [".git", "pubspec.yaml", "package.json", "Makefile", "CMakeLists.txt", "build.gradle"]


def _find_workspace_build_dirs(roots: Optional[List[str]] = None) -> List[Tuple[str, str, str, int]]:
    """
    Rileva le cartelle di build all'interno dei repository di sviluppo.
    Restituisce una lista di tuple: (nome_progetto, nome_cartella, path_assoluto, dimensione_in_byte).
    """
    if roots is None:
        roots = DEFAULT_WORKSPACE_ROOTS

    found = []
    for root in roots:
        expanded_root = os.path.expanduser(root)
        if not os.path.isdir(expanded_root):
            continue

        try:
            with os.scandir(expanded_root) as entries:
                for entry in entries:
                    if entry.is_dir() and not entry.name.startswith("."):
                        proj_path = entry.path
                        # Verifica che si tratti di un progetto effettivo
                        has_marker = any(os.path.exists(os.path.join(proj_path, m)) for m in PROJECT_MARKERS)
                        if not has_marker:
                            continue

                        for sub in BUILD_SUBDIRS:
                            target_dir = os.path.join(proj_path, sub)
                            if os.path.isdir(target_dir):
                                sz = fast_get_path_size(target_dir, timeout=5)
                                if sz > 0:
                                    found.append((entry.name, sub, target_dir, sz))
        except Exception:
            pass

    return found


def scan_workspace_builds(roots: Optional[List[str]] = None) -> int:
    """Calcola la dimensione totale occupata da cartelle build e .dart_tool nei progetti locali."""
    dirs = _find_workspace_build_dirs(roots)
    return sum(sz for _, _, _, sz in dirs)


def clean_workspace_builds(dry_run: bool, roots: Optional[List[str]] = None) -> CleanResult:
    """Elimina i file temporanei di compilazione nei progetti locali mantenendo intatti sorgenti e configurazioni."""
    result = CleanResult("Build Artifacts Progetti Locali (~/Documents/GitHub)")
    dirs = _find_workspace_build_dirs(roots)

    if not dirs:
        result.add_detail("Nessun artefatto di build o cartella .dart_tool trovata nei repository.")
        return result

    # Ordina per dimensione decrescente
    dirs.sort(key=lambda x: x[3], reverse=True)
    total_sz = sum(sz for _, _, _, sz in dirs)
    result.freed_bytes = total_sz
    result.items_count = len(dirs)

    if dry_run:
        result.add_detail(f"[Simulazione] Trovate {len(dirs)} cartelle di build ({format_bytes(total_sz)}):")
        for proj, sub, path, sz in dirs[:8]:
            result.add_detail(f"  • {proj}/{sub}: {format_bytes(sz)}")
        if len(dirs) > 8:
            result.add_detail(f"  ... e altre {len(dirs) - 8} cartelle di compilazione.")
        result.add_detail("Nota: i file sorgente e git sono intatti. 'flutter build' o 'make' ricreeranno gli artefatti.")
    else:
        for proj, sub, path, sz in dirs:
            cnt, _ = safe_remove_directory_contents(path)
            result.add_detail(f"Svuotato {proj}/{sub}: {format_bytes(sz)}")
        result.add_detail(f"Completato: liberati {format_bytes(total_sz)} da {len(dirs)} cartelle di build.")

    return result

"""
utils.py - Funzioni di utilità per filesystem, esecuzione comandi e formattazione.
"""

import os
import shutil
import subprocess
from typing import Dict, List, Tuple, Optional


def format_bytes(bytes_count: int) -> str:
    """Formatta i byte in unità leggibili con precisione adattiva (B, KB, MB, GB, TB)."""
    if bytes_count <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    val = float(bytes_count)
    i = 0
    while val >= 1024.0 and i < len(units) - 1:
        val /= 1024.0
        i += 1
    if i == 0:
        return f"{int(val)} B"
    return f"{val:.1f} {units[i]}"


def run_cmd(cmd: List[str], timeout: Optional[int] = None) -> Tuple[int, str, str]:
    """Esegue un comando in subprocess in modo sicuro catturando stdout/stderr."""
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout scaduto durante l'esecuzione del comando."
    except Exception as e:
        return -1, "", str(e)


def fast_get_path_size(path_str: str, timeout: int = 5) -> int:
    """
    Calcola rapidamente la dimensione di un percorso.
    Usa 'du -sk' per efficienza se disponibile, con fallback su os.walk.
    """
    p = os.path.expanduser(path_str)
    if not os.path.exists(p):
        return 0
    if os.path.islink(p):
        return 0
    if os.path.isfile(p):
        try:
            return os.path.getsize(p)
        except OSError:
            return 0

    code, out, _ = run_cmd(["du", "-sk", p], timeout=timeout)
    if code == 0 and out.strip():
        parts = out.split()
        if parts:
            try:
                kb = int(parts[0])
                return kb * 1024
            except ValueError:
                pass

    total = 0
    try:
        for root, dirs, files in os.walk(p, topdown=True, followlinks=False):
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
            for f in files:
                fp = os.path.join(root, f)
                if not os.path.islink(fp):
                    try:
                        total += os.path.getsize(fp)
                    except OSError:
                        pass
    except OSError:
        pass
    return total


def safe_remove_directory_contents(dir_path: str) -> Tuple[int, int]:
    """
    Rimuove in sicurezza il contenuto di una cartella mantenendo intatta la cartella radice.
    Ritorna: (numero_elementi_rimossi, errori_incontrati).
    """
    p = os.path.expanduser(dir_path)
    if not os.path.exists(p) or not os.path.isdir(p):
        return 0, 0

    removed = 0
    errors = 0
    try:
        for item in os.listdir(p):
            ip = os.path.join(p, item)
            try:
                if os.path.islink(ip) or os.path.isfile(ip):
                    os.unlink(ip)
                    removed += 1
                elif os.path.isdir(ip):
                    shutil.rmtree(ip, ignore_errors=True)
                    removed += 1
            except Exception:
                errors += 1
    except OSError:
        errors += 1
    return removed, errors


def get_disk_free_info() -> Dict[str, str]:
    """Rileva spazio libero, totale e percentuale d'uso della partizione radice /."""
    try:
        usage = shutil.disk_usage("/")
        total_gb = usage.total / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        used_pct = ((usage.total - usage.free) / usage.total) * 100.0
        return {
            "total": f"{total_gb:.1f} GB",
            "free": f"{free_gb:.1f} GB",
            "percent": f"{used_pct:.1f}%",
            "free_bytes": str(usage.free),
            "total_bytes": str(usage.total)
        }
    except Exception:
        return {"total": "N/D", "free": "N/D", "percent": "N/D", "free_bytes": "0", "total_bytes": "0"}

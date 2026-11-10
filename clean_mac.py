#!/usr/bin/env python3
"""
clean_mac.py - Script di avvio per mac_optimizer.
Rileva automaticamente l'ambiente virtuale .venv creato da uv ed esegue l'applicazione.
"""

import os
import sys
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(BASE_DIR, ".venv", "bin", "python")

# 1. Se non siamo dentro il virtualenv .venv e questo esiste, riesegui con .venv/bin/python
if os.path.isfile(VENV_PYTHON):
    try:
        if os.path.realpath(sys.executable) != os.path.realpath(VENV_PYTHON):
            os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)
    except Exception:
        pass
else:
    # 2. Se .venv non esiste ancora ma uv è presente nel PATH, usa uv run per inizializzarlo
    uv_bin = shutil.which("uv")
    if uv_bin:
        try:
            os.execv(uv_bin, [uv_bin, "run", os.path.join(BASE_DIR, "clean_mac.py")] + sys.argv[1:])
        except Exception:
            pass

# Aggiunge la directory src al PYTHONPATH per esecuzione
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mac_optimizer.cli import main

if __name__ == "__main__":
    main()

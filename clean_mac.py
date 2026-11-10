#!/usr/bin/env python3
"""
clean_mac.py - Script di avvio per mac_optimizer.
Può essere eseguito direttamente con `./clean_mac.py` oppure con `uv run mac-optimizer`.
"""

import os
import sys

# Aggiunge la directory src al PYTHONPATH per esecuzione immediata
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mac_optimizer.cli import main

if __name__ == "__main__":
    main()

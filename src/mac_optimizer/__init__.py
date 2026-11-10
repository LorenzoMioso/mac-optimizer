"""
mac_optimizer - Suite di ottimizzazione e pulizia macOS per sviluppatori.
"""

from mac_optimizer.cli import main
from mac_optimizer.registry import create_all_modules
from mac_optimizer.tui.app import MacOptimizerApp

__version__ = "0.1.0"
__all__ = ["main", "create_all_modules", "MacOptimizerApp", "__version__"]

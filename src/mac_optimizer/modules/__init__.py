"""
mac_optimizer.modules - Package contenente tutti i moduli di pulizia per categoria.
"""

from mac_optimizer.modules.xcode import (
    scan_xcode_deriveddata, clean_xcode_deriveddata,
    scan_xcode_archives, clean_xcode_archives,
    scan_xcode_devicesupport, clean_xcode_devicesupport,
    scan_xcode_ide_caches, clean_xcode_ide_caches,
)
from mac_optimizer.modules.simulators import (
    get_simulators_analysis,
    scan_old_simulators, clean_old_simulators,
    scan_simulators_erase_all, clean_simulators_erase_all,
)
from mac_optimizer.modules.package_managers import (
    scan_swiftpm_cache, clean_swiftpm_cache,
    scan_homebrew_cache, clean_homebrew_cache,
    scan_cocoapods_cache, clean_cocoapods_cache,
    scan_node_npm_caches, clean_node_npm_caches,
    scan_gradle_android_caches, clean_gradle_android_caches,
    scan_python_pip_cache, clean_python_pip_cache,
    scan_flutter_cache, clean_flutter_cache,
)
from mac_optimizer.modules.developer_tools import (
    scan_vscode_extensions_cache, clean_vscode_extensions_cache,
    scan_docker_system_prune, clean_docker_system_prune,
)
from mac_optimizer.modules.apps import (
    scan_spotify_cache, clean_spotify_cache,
    scan_browser_caches, clean_browser_caches,
)
from mac_optimizer.modules.system import (
    scan_trash_can, clean_trash_can,
    scan_system_user_logs, clean_system_user_logs,
    scan_time_machine_snapshots, clean_time_machine_snapshots,
    scan_kill_gradle_daemons, clean_kill_gradle_daemons,
    scan_ram_purge, clean_ram_purge,
)

__all__ = [
    "scan_xcode_deriveddata", "clean_xcode_deriveddata",
    "scan_xcode_archives", "clean_xcode_archives",
    "scan_xcode_devicesupport", "clean_xcode_devicesupport",
    "scan_xcode_ide_caches", "clean_xcode_ide_caches",
    "get_simulators_analysis",
    "scan_old_simulators", "clean_old_simulators",
    "scan_simulators_erase_all", "clean_simulators_erase_all",
    "scan_swiftpm_cache", "clean_swiftpm_cache",
    "scan_homebrew_cache", "clean_homebrew_cache",
    "scan_cocoapods_cache", "clean_cocoapods_cache",
    "scan_node_npm_caches", "clean_node_npm_caches",
    "scan_gradle_android_caches", "clean_gradle_android_caches",
    "scan_python_pip_cache", "clean_python_pip_cache",
    "scan_flutter_cache", "clean_flutter_cache",
    "scan_vscode_extensions_cache", "clean_vscode_extensions_cache",
    "scan_docker_system_prune", "clean_docker_system_prune",
    "scan_spotify_cache", "clean_spotify_cache",
    "scan_browser_caches", "clean_browser_caches",
    "scan_trash_can", "clean_trash_can",
    "scan_system_user_logs", "clean_system_user_logs",
    "scan_time_machine_snapshots", "clean_time_machine_snapshots",
    "scan_kill_gradle_daemons", "clean_kill_gradle_daemons",
    "scan_ram_purge", "clean_ram_purge",
]

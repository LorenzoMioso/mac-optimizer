"""
registry.py - Registro dichiarativo di tutti i moduli di pulizia disponibili.
"""

from typing import List
from mac_optimizer.models import ModuleDef
from mac_optimizer.utils import format_bytes
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


def create_all_modules() -> List[ModuleDef]:
    """Crea e registra tutti i moduli di pulizia disponibili."""
    # Analisi dinamica simulatori per mostrare versione conservata ed eliminabili
    sim_info = get_simulators_analysis()
    if sim_info.get("kept_summary"):
        sim_name = f"Vecchi Simulatori iOS (Mantiene solo {sim_info['kept_summary']})"
    else:
        sim_name = "Vecchi Simulatori iOS (Mantiene ultima versione)"

    if sim_info.get("old_summary"):
        old_cnt = len(sim_info.get("older_runtimes", []))
        dev_cnt = len(sim_info.get("deleted_devices", []))
        rt_str = "1 runtime obsoleto" if old_cnt == 1 else f"{old_cnt} runtime obsoleti"
        dev_str = "1 simulatore associato" if dev_cnt == 1 else f"{dev_cnt} simulatori associati"
        sim_desc = (
            f"Rimuove {rt_str} ({sim_info['old_summary']}: {format_bytes(sim_info['runtimes_bytes'])}) "
            f"e i {dev_str} ({format_bytes(sim_info['devices_bytes'])}), "
            f"conservando solo {sim_info['kept_summary']}."
        )
    elif sim_info.get("kept_summary"):
        sim_desc = (
            f"Nessun runtime precedente da rimuovere. Conserva l'ultima versione installata "
            f"({sim_info['kept_summary']}) e ripulisce le cache orfane."
        )
    else:
        sim_desc = "Rimuove le versioni precedenti dei simulatori e mantiene solo l'ultima versione installata."

    return [
        # --- 🍎 Sviluppo iOS & macOS ---
        ModuleDef(
            id="deriveddata",
            name="Xcode DerivedData",
            category="🍎 Sviluppo iOS & macOS",
            description="Build cache intermedie dei progetti Xcode e Flutter iOS.",
            default_selected=True,
            risk_level="recommended",
            scan_func=scan_xcode_deriveddata,
            clean_func=clean_xcode_deriveddata
        ),
        ModuleDef(
            id="archives",
            name="Xcode Archives (TUTTI gli archivi)",
            category="🍎 Sviluppo iOS & macOS",
            description="Elimina tutti gli archivi .xcarchive generati in passato.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_xcode_archives,
            clean_func=clean_xcode_archives
        ),
        ModuleDef(
            id="devicesupport",
            name="Xcode iOS DeviceSupport",
            category="🍎 Sviluppo iOS & macOS",
            description="Simboli di debug di dispositivi fisici iOS connessi in passato.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_xcode_devicesupport,
            clean_func=clean_xcode_devicesupport
        ),
        ModuleDef(
            id="xcode_cache",
            name="Xcode IDE Caches & Documentazione",
            category="🍎 Sviluppo iOS & macOS",
            description="Cache interna di compilazione/indicizzazione Xcode e documentazione.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_xcode_ide_caches,
            clean_func=clean_xcode_ide_caches
        ),
        ModuleDef(
            id="simulators",
            name=sim_name,
            category="🍎 Sviluppo iOS & macOS",
            description=sim_desc,
            default_selected=True,
            risk_level="recommended",
            scan_func=scan_old_simulators,
            clean_func=clean_old_simulators
        ),
        ModuleDef(
            id="swiftpm",
            name="Swift Package Manager Cache",
            category="🍎 Sviluppo iOS & macOS",
            description="Cache globale di clone e build dei pacchetti SwiftPM.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_swiftpm_cache,
            clean_func=clean_swiftpm_cache
        ),

        # --- 📦 Package Managers & SDK ---
        ModuleDef(
            id="brew",
            name="Homebrew Cache & Bottles",
            category="📦 Package Managers & SDK",
            description="Download vecchi pacchetti e formule con brew cleanup --prune=all.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_homebrew_cache,
            clean_func=clean_homebrew_cache
        ),
        ModuleDef(
            id="cocoapods",
            name="CocoaPods Cache",
            category="📦 Package Managers & SDK",
            description="Cache locale archivio pod (~/Library/Caches/CocoaPods).",
            default_selected=False,
            risk_level="safe",
            scan_func=scan_cocoapods_cache,
            clean_func=clean_cocoapods_cache
        ),
        ModuleDef(
            id="npm",
            name="Node / NPM / Yarn / PNPM Caches",
            category="📦 Package Managers & SDK",
            description="Cache pacchetti JavaScript (~/.npm, ~/.yarn/cache, ~/.pnpm-store).",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_node_npm_caches,
            clean_func=clean_node_npm_caches
        ),
        ModuleDef(
            id="gradle",
            name="Gradle & Android Build Caches",
            category="📦 Package Managers & SDK",
            description="Cache di compilazione Gradle e Android (~/.gradle/caches, ~/.android/cache).",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_gradle_android_caches,
            clean_func=clean_gradle_android_caches
        ),
        ModuleDef(
            id="pip",
            name="Python / Pip / UV Cache",
            category="📦 Package Managers & SDK",
            description="Cache ruote (.whl) e download pacchetti Python (~/Library/Caches/pip).",
            default_selected=False,
            risk_level="safe",
            scan_func=scan_python_pip_cache,
            clean_func=clean_python_pip_cache
        ),
        ModuleDef(
            id="flutter",
            name="Flutter & Dart Pub Git Cache",
            category="📦 Package Managers & SDK",
            description="Cache repository git clonati in ~/.pub-cache/git.",
            default_selected=False,
            risk_level="safe",
            scan_func=scan_flutter_cache,
            clean_func=clean_flutter_cache
        ),

        # --- 💻 Editor & Strumenti ---
        ModuleDef(
            id="vscode",
            name="VS Code: Estensioni Obsolete",
            category="💻 Editor & Strumenti",
            description="Rimuove versioni precedenti duplicate in ~/.vscode/extensions.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_vscode_extensions_cache,
            clean_func=clean_vscode_extensions_cache
        ),
        ModuleDef(
            id="docker",
            name="Docker System Prune",
            category="💻 Editor & Strumenti",
            description="Container fermi, immagini orfane, volumi non associati e build cache.",
            default_selected=False,
            risk_level="caution",
            scan_func=scan_docker_system_prune,
            clean_func=clean_docker_system_prune
        ),

        # --- 🌐 Cache App & Browser ---
        ModuleDef(
            id="spotify",
            name="Spotify Streaming Cache",
            category="🌐 Cache App & Browser",
            description="Cache locale delle canzoni in streaming (account e playlist intatti).",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_spotify_cache,
            clean_func=clean_spotify_cache
        ),
        ModuleDef(
            id="browser",
            name="Browser Web Caches (Brave, Chrome, Safari)",
            category="🌐 Cache App & Browser",
            description="Cache web temporanea dei browser (nessun cookie/password toccato).",
            default_selected=False,
            risk_level="safe",
            scan_func=scan_browser_caches,
            clean_func=clean_browser_caches
        ),

        # --- ⚙️ Sistema macOS & RAM ---
        ModuleDef(
            id="trash",
            name="Cestino macOS (~/.Trash)",
            category="⚙️ Sistema macOS & RAM",
            description="Svuota definitivamente i file rimasti nel Cestino utente.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_trash_can,
            clean_func=clean_trash_can
        ),
        ModuleDef(
            id="logs",
            name="Log Utente & Crash Reports",
            category="⚙️ Sistema macOS & RAM",
            description="File di log applicativi e crash dump accumulati in ~/Library/Logs.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_system_user_logs,
            clean_func=clean_system_user_logs
        ),
        ModuleDef(
            id="snapshots",
            name="Time Machine Local Snapshots",
            category="⚙️ Sistema macOS & RAM",
            description="Assottiglia gli snapshot locali APFS per sbloccare spazio su disco.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_time_machine_snapshots,
            clean_func=clean_time_machine_snapshots
        ),
        ModuleDef(
            id="daemons",
            name="Termina Demoni Gradle/Kotlin in RAM",
            category="⚙️ Sistema macOS & RAM",
            description="Chiude i processi Java inattivi che occupano memoria unificata.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_kill_gradle_daemons,
            clean_func=clean_kill_gradle_daemons
        ),
        ModuleDef(
            id="ram_purge",
            name="macOS Purge RAM (svuota cache inattiva)",
            category="⚙️ Sistema macOS & RAM",
            description="Svuota la cache disco inattiva di macOS per restituire RAM fisica al sistema.",
            default_selected=True,
            risk_level="safe",
            scan_func=scan_ram_purge,
            clean_func=clean_ram_purge
        ),

        # --- ⚠️ Operazioni Avanzate (Opt-in) ---
        ModuleDef(
            id="simulators_erase",
            name="Reset Totale Simulatori iOS (Opt-in)",
            category="⚠️ Operazioni Avanzate (Opt-in)",
            description="xcrun simctl erase all: azzera tutte le app e dati installati nei simulatori.",
            default_selected=False,
            risk_level="caution",
            scan_func=scan_simulators_erase_all,
            clean_func=clean_simulators_erase_all
        ),
    ]

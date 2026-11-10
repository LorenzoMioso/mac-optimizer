"""
modules/simulators.py - Rilevamento e pulizia intelligente simulatori iOS / watchOS / tvOS.
Preserva sempre l'ultima versione attiva installata (es. iOS 27.0) e rimuove runtime e dispositivi obsoleti.
"""

import os
import json
import re
from typing import Dict, List, Tuple, Any, Optional
from mac_optimizer.models import CleanResult
from mac_optimizer.utils import run_cmd, fast_get_path_size, safe_remove_directory_contents, format_bytes

_SIM_ANALYSIS_CACHE: Optional[Dict[str, Any]] = None


def get_simulators_analysis(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Analizza i runtime di simulatori installati e i relativi dispositivi virtuali.
    Rileva per ciascuna piattaforma (iOS, watchOS, tvOS, visionOS) l'ultima versione disponibile
    da preservare e individua i runtime e simulatori obsoleti da rimuovere.
    """
    global _SIM_ANALYSIS_CACHE
    if _SIM_ANALYSIS_CACHE is not None and not force_refresh:
        return _SIM_ANALYSIS_CACHE

    analysis: Dict[str, Any] = {
        "available": False,
        "kept_summary": "",
        "old_summary": "",
        "kept_runtimes": [],
        "older_runtimes": [],
        "deleted_devices": [],
        "runtimes_bytes": 0,
        "devices_bytes": 0,
        "cache_bytes": 0,
        "total_reclaimable_bytes": 0,
    }

    code, _, _ = run_cmd(["which", "xcrun"])
    if code != 0:
        _SIM_ANALYSIS_CACHE = analysis
        return analysis

    cache_p = os.path.expanduser("~/Library/Developer/CoreSimulator/Caches")
    logs_p = os.path.expanduser("~/Library/Logs/CoreSimulator")
    cache_sz = fast_get_path_size(cache_p, timeout=5) + fast_get_path_size(logs_p, timeout=5)
    analysis["cache_bytes"] = cache_sz

    # 1. Interroga i runtime dei simulatori
    code_rt, out_rt, _ = run_cmd(["xcrun", "simctl", "runtime", "list", "-j"], timeout=10)
    if code_rt != 0 or not out_rt.strip():
        analysis["total_reclaimable_bytes"] = cache_sz
        _SIM_ANALYSIS_CACHE = analysis
        return analysis

    try:
        runtimes_raw = json.loads(out_rt)
    except Exception:
        analysis["total_reclaimable_bytes"] = cache_sz
        _SIM_ANALYSIS_CACHE = analysis
        return analysis

    # 2. Interroga i dispositivi virtuali
    code_dev, out_dev, _ = run_cmd(["xcrun", "simctl", "list", "-j", "devices"], timeout=10)
    devices_by_rt: Dict[str, List[Dict[str, Any]]] = {}
    if code_dev == 0 and out_dev.strip():
        try:
            devices_by_rt = json.loads(out_dev).get("devices", {})
        except Exception:
            pass

    analysis["available"] = True

    def parse_version(v_str: str) -> Tuple[int, ...]:
        nums = [int(x) for x in re.findall(r"\d+", v_str or "")]
        return tuple(nums) if nums else (0,)

    def plat_name(plat_id: str) -> str:
        if "iphonesimulator" in plat_id:
            return "iOS"
        if "watchsimulator" in plat_id:
            return "watchOS"
        if "appletvsimulator" in plat_id:
            return "tvOS"
        if "xrsimulator" in plat_id:
            return "visionOS"
        return plat_id.split(".")[-1].replace("simulator", "")

    by_plat: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
    for uuid, info in runtimes_raw.items():
        if not isinstance(info, dict):
            continue
        plat = info.get("platformIdentifier", "com.apple.platform.iphonesimulator")
        by_plat.setdefault(plat, []).append((uuid, info))

    kept_summaries = []
    old_summaries = []
    runtimes_sz = 0
    devices_sz = 0

    for plat, rts in by_plat.items():
        rts.sort(key=lambda item: parse_version(item[1].get("version", "0")))
        latest_uuid, latest_info = rts[-1]
        pname = plat_name(plat)
        latest_v = latest_info.get("version", "sconosciuta")
        kept_summaries.append(f"{pname} {latest_v}")
        analysis["kept_runtimes"].append({
            "uuid": latest_uuid,
            "platform": pname,
            "version": latest_v,
            "info": latest_info,
        })

        older = rts[:-1]
        for u, inf in older:
            v = inf.get("version", "sconosciuta")
            sz = int(inf.get("sizeBytes", 0) or 0)
            rt_id = inf.get("runtimeIdentifier", "")
            devs = devices_by_rt.get(rt_id, [])
            d_sz = sum(int(d.get("dataPathSize", 0) or 0) for d in devs)

            runtimes_sz += sz
            devices_sz += d_sz

            analysis["older_runtimes"].append({
                "uuid": u,
                "platform": pname,
                "version": v,
                "runtimeIdentifier": rt_id,
                "sizeBytes": sz,
                "devices": devs,
                "devicesSizeBytes": d_sz,
            })
            for d in devs:
                analysis["deleted_devices"].append(d)

            old_summaries.append(f"{pname} {v}")

    analysis["kept_summary"] = ", ".join(kept_summaries) if kept_summaries else ""
    analysis["old_summary"] = ", ".join(old_summaries) if old_summaries else ""
    analysis["runtimes_bytes"] = runtimes_sz
    analysis["devices_bytes"] = devices_sz
    analysis["total_reclaimable_bytes"] = runtimes_sz + devices_sz + cache_sz

    _SIM_ANALYSIS_CACHE = analysis
    return analysis


def scan_old_simulators() -> int:
    """Calcola lo spazio totale recuperabile da vecchi runtime, simulatori associati e cache."""
    info = get_simulators_analysis()
    return info["total_reclaimable_bytes"]


def clean_old_simulators(dry_run: bool) -> CleanResult:
    """
    Rimuove i vecchi runtime di simulatori iOS e i dispositivi associati,
    preservando sempre l'ultima versione installata.
    """
    global _SIM_ANALYSIS_CACHE
    info = get_simulators_analysis()
    kept_label = info.get("kept_summary") or "ultima versione"
    result = CleanResult(f"Vecchi Simulatori iOS (Mantiene {kept_label})")

    code, _, _ = run_cmd(["which", "xcrun"])
    if code != 0:
        result.add_detail("xcrun non installato nel sistema.")
        return result

    result.freed_bytes = info["total_reclaimable_bytes"]
    result.items_count = len(info["older_runtimes"]) + len(info["deleted_devices"])

    if not info["older_runtimes"]:
        result.add_detail(f"Versione attiva mantenuta: {kept_label}.")
        result.add_detail("Nessun runtime precedente da rimuovere.")
        if dry_run:
            if info["cache_bytes"] > 0:
                result.add_detail(f"[Simulazione] Cache CoreSimulator da svuotare: {format_bytes(info['cache_bytes'])}")
        else:
            run_cmd(["xcrun", "simctl", "delete", "unavailable"])
            safe_remove_directory_contents(os.path.expanduser("~/Library/Developer/CoreSimulator/Caches"))
            safe_remove_directory_contents(os.path.expanduser("~/Library/Logs/CoreSimulator"))
            _SIM_ANALYSIS_CACHE = None
        return result

    if dry_run:
        result.add_detail(f"Versione che verrà mantenuta: {kept_label}")
        for rt in info["older_runtimes"]:
            result.add_detail(
                f"[Simulazione] Runtime da rimuovere: {rt['platform']} {rt['version']} "
                f"({format_bytes(rt['sizeBytes'])}, UUID: {rt['uuid']})"
            )
            devs = rt["devices"]
            if devs:
                result.add_detail(
                    f"  ↳ {len(devs)} simulatori associati da eliminare ({format_bytes(rt['devicesSizeBytes'])}):"
                )
                for d in devs[:4]:
                    sz_str = format_bytes(d.get("dataPathSize", 0))
                    result.add_detail(f"     • {d.get('name', 'Dispositivo')} ({sz_str})")
                if len(devs) > 4:
                    result.add_detail(f"     • ... e altri {len(devs) - 4} simulatori.")
        if info["cache_bytes"] > 0:
            result.add_detail(f"[Simulazione] Cache CoreSimulator da svuotare: {format_bytes(info['cache_bytes'])}")
        result.add_detail(f"[Simulazione] Spazio totale stimato da liberare: {format_bytes(info['total_reclaimable_bytes'])}")
    else:
        # 1. Spegni e rimuovi i dispositivi virtuali associati ai vecchi runtime
        for dev in info["deleted_devices"]:
            udid = dev.get("udid")
            if not udid:
                continue
            if dev.get("state") == "Booted":
                run_cmd(["xcrun", "simctl", "shutdown", udid], timeout=15)
            run_cmd(["xcrun", "simctl", "delete", udid], timeout=20)

        # 2. Rimuovi i runtime disk images obsoleti
        for rt in info["older_runtimes"]:
            u = rt.get("uuid")
            if u:
                run_cmd(["xcrun", "simctl", "runtime", "delete", u], timeout=60)

        # 3. Pulizia dispositivi orfani e cache
        run_cmd(["xcrun", "simctl", "delete", "unavailable"], timeout=20)
        run_cmd(["xcrun", "simctl", "runtime", "delete", "unavailable"], timeout=20)
        safe_remove_directory_contents(os.path.expanduser("~/Library/Developer/CoreSimulator/Caches"))
        safe_remove_directory_contents(os.path.expanduser("~/Library/Logs/CoreSimulator"))

        old_cnt = len(info['older_runtimes'])
        dev_cnt = len(info['deleted_devices'])
        rt_str = "1 runtime obsoleto" if old_cnt == 1 else f"{old_cnt} runtime obsoleti"
        dev_str = "1 simulatore associato" if dev_cnt == 1 else f"{dev_cnt} simulatori associati"
        result.add_detail(f"Conservata versione attiva più recente: {kept_label}.")
        result.add_detail(
            f"Rimossi {rt_str} ({info.get('old_summary', '')}) e {dev_str}."
        )
        result.add_detail("Cache CoreSimulator e log rimossi.")
        result.add_detail(f"Spazio liberato: {format_bytes(info['total_reclaimable_bytes'])}")
        _SIM_ANALYSIS_CACHE = None

    return result


def scan_simulators_erase_all() -> int:
    return 0


def clean_simulators_erase_all(dry_run: bool) -> CleanResult:
    result = CleanResult("Reset Totale Simulatori iOS (Factory Reset)")
    if dry_run:
        result.add_detail("[Simulazione] Esecuzione 'xcrun simctl erase all': tutti i simulatori verranno azzerati.")
    else:
        run_cmd(["xcrun", "simctl", "erase", "all"], timeout=30)
        result.add_detail("Tutti i simulatori iOS sono stati ripristinati allo stato di fabbrica iniziale.")
    return result

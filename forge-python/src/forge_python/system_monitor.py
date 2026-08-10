"""Real-time system stats for the UI monitor."""

from __future__ import annotations

import psutil

from forge_python.models import SystemStats


def collect_stats(queue_pending: int = 0, queue_processing: int = 0) -> SystemStats:
    vm = psutil.virtual_memory()
    gpu_name = None
    gpu_util = None
    vram_used = None
    vram_total = None
    temp = None
    try:
        # Optional NVIDIA bindings are not required for MVP; leave None when unavailable.
        temps = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
        for entries in temps.values():
            if entries:
                temp = float(entries[0].current)
                break
    except Exception:
        temp = None

    return SystemStats(
        cpu_percent=float(psutil.cpu_percent(interval=0.05)),
        ram_percent=float(vm.percent),
        ram_used_gb=round(vm.used / (1024**3), 2),
        ram_total_gb=round(vm.total / (1024**3), 2),
        gpu_name=gpu_name,
        gpu_util_percent=gpu_util,
        vram_used_gb=vram_used,
        vram_total_gb=vram_total,
        temperature_c=temp,
        queue_pending=queue_pending,
        queue_processing=queue_processing,
    )

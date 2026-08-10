"""Real-time system stats for the UI monitor."""

from __future__ import annotations

import platform
import shutil
import subprocess

import psutil

from forge_python.models import SystemStats


def _nvidia_gpu() -> tuple[str | None, float | None, float | None, float | None, float | None]:
    """Return name, util%, vram_used_gb, vram_total_gb, temp_c via nvidia-smi."""
    if not shutil.which("nvidia-smi"):
        return None, None, None, None, None
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=2.0,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return None, None, None, None, None
    line = (out or "").strip().splitlines()
    if not line:
        return None, None, None, None, None
    parts = [p.strip() for p in line[0].split(",")]
    if len(parts) < 5:
        return None, None, None, None, None
    name = parts[0] or None

    def _f(raw: str) -> float | None:
        try:
            return float(raw)
        except ValueError:
            return None

    util = _f(parts[1])
    mem_used = _f(parts[2])
    mem_total = _f(parts[3])
    temp = _f(parts[4])
    vram_used = round(mem_used / 1024.0, 2) if mem_used is not None else None
    vram_total = round(mem_total / 1024.0, 2) if mem_total is not None else None
    return name, util, vram_used, vram_total, temp


def collect_stats(queue_pending: int = 0, queue_processing: int = 0) -> SystemStats:
    vm = psutil.virtual_memory()
    gpu_name = None
    gpu_util = None
    vram_used = None
    vram_total = None
    temp = None

    n_name, n_util, n_vram_u, n_vram_t, n_temp = _nvidia_gpu()
    if n_name:
        gpu_name = n_name
        gpu_util = n_util
        vram_used = n_vram_u
        vram_total = n_vram_t
        temp = n_temp
    elif platform.system() == "Darwin":
        # Apple Silicon has no nvidia-smi; label the accelerator for the UI.
        gpu_name = "Apple Silicon (MPS)"

    if temp is None:
        try:
            temps = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
            for entries in temps.values():
                if entries:
                    temp = float(entries[0].current)
                    break
        except (AttributeError, OSError, ValueError):
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

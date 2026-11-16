from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import psutil


@dataclass
class SystemStats:
    cpu: float
    ram: float
    ram_used_gb: float
    ram_total_gb: float
    disk: float
    disk_used_gb: float
    disk_total_gb: float
    cpu_count: int
    uptime_h: float

    def as_dict(self) -> dict:
        return asdict(self)

    def describe_tr(self, focus: str | None = None) -> str:
        parts = {
            "cpu": f"İşlemci kullanımı %{self.cpu:.0f} ({self.cpu_count} çekirdek)",
            "ram": f"RAM kullanımı %{self.ram:.0f} — {self.ram_used_gb:.1f} / {self.ram_total_gb:.1f} GB",
            "disk": f"Disk kullanımı %{self.disk:.0f} — {self.disk_used_gb:.0f} / {self.disk_total_gb:.0f} GB",
        }
        if focus in parts:
            return parts[focus] + "."
        return ". ".join(parts.values()) + "."


def read_stats(disk_path: str | None = None) -> SystemStats:
    vm = psutil.virtual_memory()
    du = psutil.disk_usage(disk_path or str(Path.home()))
    import time
    return SystemStats(
        cpu=psutil.cpu_percent(interval=None),
        ram=vm.percent,
        ram_used_gb=(vm.total - vm.available) / 1e9,
        ram_total_gb=vm.total / 1e9,
        disk=du.percent,
        disk_used_gb=du.used / 1e9,
        disk_total_gb=du.total / 1e9,
        cpu_count=psutil.cpu_count() or 1,
        uptime_h=(time.time() - psutil.boot_time()) / 3600,
    )


def top_processes(n: int = 6) -> list[dict]:
    procs = []
    for p in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
        info = p.info
        if info.get("memory_percent") is not None:
            procs.append(info)
    procs.sort(key=lambda x: x["memory_percent"] or 0, reverse=True)
    return [{"pid": p["pid"], "name": p["name"], "mem": round(p["memory_percent"] or 0, 1),
             "cpu": round(p["cpu_percent"] or 0, 1)} for p in procs[:n]]


def gpu_info() -> str:
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                 "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=2).stdout.strip()
            if out:
                name, util, used, total = [x.strip() for x in out.splitlines()[0].split(",")]
                return f"{name} • %{util} • {used}/{total} MB"
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
    return platform.machine()

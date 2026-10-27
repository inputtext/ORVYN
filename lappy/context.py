"""Opt-in, minimized, locally collected context. Nothing is uploaded."""
from __future__ import annotations

from pathlib import Path
import platform
import ctypes


class LaptopContext:
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir.expanduser().resolve()

    def system_status(self) -> str:
        try:
            import psutil
        except ImportError:
            return (
                "System status unavailable: psutil is not installed. "
                "Run: pip install psutil"
            )
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.15)
        battery = psutil.sensors_battery()
        items = [
            f"OS: {platform.system()} {platform.release()}",
            f"CPU usage: {cpu:.0f}%",
            f"RAM: {memory.used / (1024**3):.1f} / {memory.total / (1024**3):.1f} GiB ({memory.percent:.0f}%)",
        ]
        if battery is not None:
            items.append(f"Battery: {battery.percent:.0f}% ({'charging' if battery.power_plugged else 'on battery'})")
        return "; ".join(items)

    def running_apps(self) -> str:
        try:
            import psutil
        except ImportError:
            return (
                "Process listing unavailable: psutil is not installed. "
                "Run: pip install psutil"
            )
        # Name and PID only. No command lines, environment variables, paths, or user data.
        names = []
        for proc in psutil.process_iter(attrs=["pid", "name"]):
            try:
                info = proc.info
                name = info.get("name") or "unknown"
                names.append((name.casefold(), int(info["pid"]), name))
            except (psutil.AccessDenied, psutil.NoSuchProcess, ValueError, TypeError):
                continue
        names.sort()
        top = [f"{name} (PID {pid})" for _, pid, name in names[:25]]
        return f"Showing {len(top)} of {len(names)} processes: " + (", ".join(top) if top else "none")

    def active_window(self) -> str:
        if platform.system() != "Windows":
            return "Active-window inspection is supported only on Windows in v0.1."
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        size = user32.GetWindowTextLengthW(hwnd)
        if size == 0:
            return "No readable foreground-window title."
        buf = ctypes.create_unicode_buffer(size + 1)
        user32.GetWindowTextW(hwnd, buf, size + 1)
        return "Foreground window title: " + buf.value[:200]

    def workspace(self) -> str:
        root = self.workspace_dir
        if not root.exists() or not root.is_dir():
            return f"Workspace folder not found: {root}. Set ORVYN_WORKSPACE_DIR."
        try:
            # One-level directory listing only; no recursion or file contents.
            entries = sorted(root.iterdir(), key=lambda p: p.name.lower())
            entries = [p for p in entries if not p.is_symlink()]
            visible = entries[:30]
            names = [f"{'folder' if p.is_dir() else 'file'}: {p.name}" for p in visible]
            return f"Workspace: {root}; {len(entries)} items; first {len(visible)}: " + (", ".join(names) if names else "empty")
        except PermissionError:
            return "Access denied to the configured workspace."

"""A small auditable tool router; LLM output never becomes a shell command."""
from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from typing import Callable, Optional

from .context import LaptopContext

# Exact names only; arguments cannot be supplied by the AI.
WINDOWS_APPS = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
}


class ToolRouter:
    def __init__(self, context: LaptopContext, launcher: Optional[Callable] = None):
        self.context = context
        self.launcher = launcher if launcher is not None else subprocess.Popen

    def execute(self, action: str, target: str = "none") -> str:
        if action == "get_system_status" and target == "none":
            return self.context.system_status()
        if action == "list_running_apps" and target == "none":
            return self.context.running_apps()
        if action == "get_active_window" and target == "none":
            return self.context.active_window()
        if action == "list_workspace" and target == "none":
            return self.context.workspace()
        if action == "open_application" and target in WINDOWS_APPS:
            if platform.system() != "Windows":
                return "Application launch is Windows-only in v0.1."
            # Never run shell=True. Only hardcoded known executable names.
            self.launcher(WINDOWS_APPS[target], shell=False)
            return f"Requested Windows to open {target}. (Launch not independently verified.)"
        if action == "open_workspace" and target == "none":
            if platform.system() != "Windows":
                return "Opening Explorer is Windows-only in v0.1."
            root: Path = self.context.workspace_dir
            if not root.is_dir():
                return "Workspace directory not found; not launching Explorer."
            self.launcher(["explorer.exe", str(root)], shell=False)
            return f"Requested Windows to open Explorer at {root}. (Launch not independently verified.)"
        return "Blocked: unknown or unauthorized action/arguments."

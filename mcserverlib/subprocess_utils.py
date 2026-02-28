from __future__ import annotations

import subprocess
from pathlib import Path

from .exceptions import InstallError


def run_checked(command: list[str], cwd: Path) -> None:
    process = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if process.returncode != 0:
        details = process.stderr.strip() or process.stdout.strip()
        raise InstallError(
            "Command failed with exit code "
            f"{process.returncode}: {' '.join(command)}\n{details}"
        )

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


def _run(command: list[str], cwd: Path) -> None:
    result = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: {' '.join(command)}"
        )


def _pyinstaller_data_arg(source: Path, destination: str) -> str:
    separator = ";" if os.name == "nt" else ":"
    return f"{source}{separator}{destination}"


def _ensure_windows_icon(project_root: Path) -> Path | None:
    assets_dir = project_root / "assets"
    icon_path = assets_dir / "icon.ico"
    if icon_path.exists():
        return icon_path

    logo_candidates = [
        assets_dir / "logo.png",
        assets_dir / "kings-logo.png",
    ]
    logo_path = next((candidate for candidate in logo_candidates if candidate.exists()), None)
    if logo_path is None:
        return None

    try:
        from PIL import Image  # type: ignore[import-untyped]
    except Exception:
        return None

    assets_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(logo_path) as image:
        rgba = image.convert("RGBA")
        rgba.save(
            icon_path,
            format="ICO",
            sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
    return icon_path


def build_launcher(
    project_root: Path,
    app_name: str = "KingsServerLauncher",
    onefile: bool = True,
    skip_bootstrap: bool = False,
) -> Path:
    if skip_bootstrap:
        python_cmd = [sys.executable]
    else:
        _run([sys.executable, "-m", "pip", "install", "-e", ".[build]"], cwd=project_root)
        python_cmd = [sys.executable]

    launcher_script = project_root / "launcher_entry.py"
    command = [
        *python_cmd,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        app_name,
    ]
    assets_dir = project_root / "assets"
    if assets_dir.exists():
        command.extend(["--add-data", _pyinstaller_data_arg(assets_dir, "assets")])

    icon_path = _ensure_windows_icon(project_root)
    if icon_path is not None:
        command.extend(["--icon", str(icon_path)])

    command.append("--onefile" if onefile else "--onedir")
    command.append(str(launcher_script))
    _run(command, cwd=project_root)

    dist_dir = project_root / "dist"
    if onefile:
        return dist_dir / f"{app_name}.exe"
    return dist_dir / app_name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mcserver-build",
        description="Build a desktop executable for the Minecraft server starter launcher.",
    )
    parser.add_argument(
        "--name",
        default="KingsServerLauncher",
        help="Output app name (default: KingsServerLauncher).",
    )
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="Build a one-directory app instead of one-file executable.",
    )
    parser.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help="Skip installing build dependencies before invoking PyInstaller.",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    artifact = build_launcher(
        project_root=root,
        app_name=args.name,
        onefile=not args.onedir,
        skip_bootstrap=args.skip_bootstrap,
    )
    print(f"Build complete: {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

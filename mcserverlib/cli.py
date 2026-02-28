from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from .manager import ServerManager
from .models import InstallRequest


def _parse_properties(items: list[str] | None) -> dict[str, str] | None:
    if not items:
        return None
    parsed: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Invalid property '{item}'. Expected key=value.")
        key, value = item.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _cmd_loaders(manager: ServerManager) -> int:
    for loader in manager.supported_loaders:
        print(loader)
    return 0


def _cmd_install(args: argparse.Namespace, manager: ServerManager) -> int:
    server_properties = _parse_properties(args.property)
    request = InstallRequest(
        loader=args.loader,
        instance_dir=Path(args.dir).resolve(),
        minecraft_version=args.minecraft_version,
        loader_version=args.loader_version,
        build=args.build,
        java_path=args.java,
        accept_eula=args.accept_eula,
        server_properties=server_properties,
    )
    result = manager.install(request)
    payload = {
        "loader": result.manifest.loader,
        "minecraft_version": result.manifest.minecraft_version,
        "loader_version": result.manifest.loader_version,
        "build": result.manifest.build,
        "java_required": result.manifest.java_required,
        "instance_dir": str(result.instance_dir),
        "manifest_path": str(result.manifest_path),
        "server_jar": str(result.server_jar) if result.server_jar else None,
        "notes": result.notes,
    }
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_manifest(args: argparse.Namespace, manager: ServerManager) -> int:
    manifest = manager.load_manifest(Path(args.dir).resolve())
    print(json.dumps(manifest.to_dict(), indent=2))
    return 0


def _cmd_start(args: argparse.Namespace, manager: ServerManager) -> int:
    def _log(line: str) -> None:
        print(line)

    process = manager.start(
        instance_dir=Path(args.dir).resolve(),
        java_path=args.java,
        xms=args.xms,
        xmx=args.xmx,
        jvm_args=args.jvm_arg or [],
        log_handler=_log,
    )

    print(f"Started server with PID {process.pid}. Press Ctrl+C to stop.")
    try:
        return_code = process.wait()
        print(f"Server exited with code {return_code}.")
        return return_code
    except KeyboardInterrupt:
        print("Stopping server...")
        code = process.stop(graceful_timeout=30.0)
        while process.is_running():
            time.sleep(0.2)
        print(f"Server stopped with code {code}.")
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcserver",
        description="Install and run Minecraft servers across many loaders.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("loaders", help="Print supported loaders.")

    install = sub.add_parser("install", help="Install a server instance.")
    install.add_argument("--loader", required=True, help="Loader name.")
    install.add_argument(
        "--dir",
        required=True,
        help="Instance directory where files will be installed.",
    )
    install.add_argument(
        "--minecraft-version",
        default="latest",
        help="Minecraft version (default: latest).",
    )
    install.add_argument(
        "--loader-version",
        default=None,
        help="Specific loader version/build train (optional).",
    )
    install.add_argument(
        "--build",
        default=None,
        help="Specific build number for providers that support it.",
    )
    install.add_argument(
        "--java",
        default="java",
        help="Java executable path to run installer commands.",
    )
    install.add_argument(
        "--accept-eula",
        action="store_true",
        help="Write eula=true after installation.",
    )
    install.add_argument(
        "--property",
        action="append",
        help="Set server.properties entry using key=value. Can be used multiple times.",
    )

    manifest = sub.add_parser("manifest", help="Print stored instance manifest.")
    manifest.add_argument("--dir", required=True, help="Instance directory.")

    start = sub.add_parser("start", help="Start a previously installed server.")
    start.add_argument("--dir", required=True, help="Instance directory.")
    start.add_argument("--java", default="java", help="Java executable path.")
    start.add_argument("--xms", default=None, help="Initial heap size (for Java launchers).")
    start.add_argument("--xmx", default=None, help="Max heap size (for Java launchers).")
    start.add_argument(
        "--jvm-arg",
        action="append",
        help="Additional JVM argument (repeat for multiple).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    manager = ServerManager()

    if args.command == "loaders":
        return _cmd_loaders(manager)
    if args.command == "install":
        return _cmd_install(args, manager)
    if args.command == "manifest":
        return _cmd_manifest(args, manager)
    if args.command == "start":
        return _cmd_start(args, manager)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

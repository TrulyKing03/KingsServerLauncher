from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .exceptions import ManifestError
from .http import HttpClient
from .models import InstallRequest, InstallResult, ServerManifest
from .process import LogHandler, ServerProcess
from .providers import create_provider_registry
from .utils import (
    normalize_loader,
    load_manifest,
    save_manifest,
    write_eula,
    write_server_properties,
)


class ServerManager:
    def __init__(self, http_client: HttpClient | None = None) -> None:
        self.http_client = http_client or HttpClient()
        self._providers = create_provider_registry()

    @property
    def supported_loaders(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers.keys()))

    def install(self, request: InstallRequest) -> InstallResult:
        loader_id = normalize_loader(request.loader)
        provider = self._providers[loader_id]
        request.loader = loader_id
        request.instance_dir = Path(request.instance_dir).resolve()
        request.instance_dir.mkdir(parents=True, exist_ok=True)

        provider_result = provider.install(request=request, http_client=self.http_client)

        write_eula(request.instance_dir, accepted=request.accept_eula)
        if request.server_properties:
            write_server_properties(
                instance_dir=request.instance_dir,
                properties=dict(request.server_properties),
            )

        manifest_path = save_manifest(
            instance_dir=request.instance_dir,
            manifest=provider_result.manifest,
        )
        return InstallResult(
            instance_dir=request.instance_dir,
            manifest_path=manifest_path,
            manifest=provider_result.manifest,
            server_jar=provider_result.server_jar,
            notes=provider_result.notes or [],
        )

    def load_manifest(self, instance_dir: str | Path) -> ServerManifest:
        return load_manifest(Path(instance_dir))

    def build_start_command(
        self,
        manifest: ServerManifest,
        java_path: str = "java",
        xms: str | None = None,
        xmx: str | None = None,
        jvm_args: Iterable[str] | None = None,
    ) -> list[str]:
        self._validate_java_path(java_path)
        raw_command = manifest.start.for_platform()
        self._validate_start_template(raw_command)
        command = [java_path if token == "{java}" else token for token in raw_command]
        if "{java}" in raw_command and command:
            insert_at = command.index(java_path) + 1
            extra: list[str] = []
            if xms:
                extra.append(f"-Xms{xms}")
            if xmx:
                extra.append(f"-Xmx{xmx}")
            if jvm_args:
                extra.extend(list(jvm_args))
            if extra:
                command[insert_at:insert_at] = extra
        return command

    def start(
        self,
        instance_dir: str | Path,
        java_path: str = "java",
        xms: str | None = None,
        xmx: str | None = None,
        jvm_args: Iterable[str] | None = None,
        log_handler: LogHandler | None = None,
        env: dict[str, str] | None = None,
    ) -> ServerProcess:
        instance = Path(instance_dir).resolve()
        manifest = load_manifest(instance)
        raw_command = manifest.start.for_platform()
        self._validate_start_template(raw_command)
        self._validate_start_paths(raw_command, instance)
        command = self.build_start_command(
            manifest=manifest,
            java_path=java_path,
            xms=xms,
            xmx=xmx,
            jvm_args=jvm_args,
        )
        return ServerProcess.start(
            command=command,
            cwd=instance,
            log_handler=log_handler,
            env=env,
        )

    @staticmethod
    def _validate_java_path(java_path: str) -> None:
        value = str(java_path).strip()
        if not value:
            raise ManifestError("Java path cannot be empty.")
        if any(char in value for char in ("\x00", "\r", "\n")):
            raise ManifestError("Java path contains unsupported characters.")

    @staticmethod
    def _validate_start_template(raw_command: list[str]) -> None:
        if not raw_command:
            raise ManifestError("Start command is empty.")
        if len(raw_command) > 80:
            raise ManifestError("Start command contains too many arguments.")
        if raw_command[0] != "{java}":
            raise ManifestError(
                "Start command is invalid. First token must be '{java}'."
            )
        for token in raw_command:
            if not isinstance(token, str):
                raise ManifestError("Start command contains a non-string token.")
            if not token.strip():
                raise ManifestError("Start command contains an empty token.")
            if len(token) > 1024:
                raise ManifestError("Start command token exceeds supported length.")
            if any(char in token for char in ("\x00", "\r", "\n")):
                raise ManifestError("Start command contains unsupported characters.")
            if token in {"|", "||", "&&", ";"}:
                raise ManifestError("Start command contains blocked shell token.")

    def _validate_start_paths(self, raw_command: list[str], instance_dir: Path) -> None:
        token_count = len(raw_command)
        for idx, token in enumerate(raw_command):
            if token.startswith("@") and len(token) > 1:
                self._resolve_under_instance_dir(token[1:], instance_dir)
            if token == "-jar" and idx + 1 < token_count:
                jar_path = self._resolve_under_instance_dir(raw_command[idx + 1], instance_dir)
                if jar_path.suffix.lower() != ".jar":
                    raise ManifestError("Start command '-jar' target must be a .jar file.")

    @staticmethod
    def _resolve_under_instance_dir(token: str, instance_dir: Path) -> Path:
        normalized = token.strip().strip("\"'")
        path = Path(normalized)
        if path.is_absolute():
            raise ManifestError(
                "Start command contains absolute paths, which are blocked for security."
            )
        candidate = (instance_dir / path).resolve()
        try:
            candidate.relative_to(instance_dir)
        except ValueError as exc:
            raise ManifestError(
                "Start command contains path traversal outside the server directory."
            ) from exc
        return candidate

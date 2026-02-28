from __future__ import annotations

from collections import deque
from pathlib import Path
import subprocess
import threading
from typing import Callable


LogHandler = Callable[[str], None]


class ServerProcess:
    def __init__(
        self,
        process: subprocess.Popen[str],
        command: list[str],
        cwd: Path,
        log_handler: LogHandler | None = None,
    ) -> None:
        self._process = process
        self.command = command
        self.cwd = cwd
        self._log_handler = log_handler
        self._recent_lines: deque[str] = deque(maxlen=400)
        self._reader_thread = threading.Thread(
            target=self._pump_stdout,
            name="mcserverlib-log-reader",
            daemon=True,
        )
        self._reader_thread.start()

    @classmethod
    def start(
        cls,
        command: list[str],
        cwd: Path,
        log_handler: LogHandler | None = None,
        env: dict[str, str] | None = None,
    ) -> ServerProcess:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        return cls(process=process, command=command, cwd=cwd, log_handler=log_handler)

    def _pump_stdout(self) -> None:
        if self._process.stdout is None:
            return
        for line in self._process.stdout:
            line = line.rstrip("\n")
            self._recent_lines.append(line)
            if self._log_handler:
                self._log_handler(line)

    def poll(self) -> int | None:
        return self._process.poll()

    def is_running(self) -> bool:
        return self.poll() is None

    def wait(self, timeout: float | None = None) -> int:
        return self._process.wait(timeout=timeout)

    def send_command(self, command: str) -> None:
        if self._process.stdin is None:
            return
        if not command.endswith("\n"):
            command += "\n"
        self._process.stdin.write(command)
        self._process.stdin.flush()

    def stop(self, graceful_timeout: float = 30.0) -> int:
        if not self.is_running():
            code = self.poll()
            return code if code is not None else 0
        try:
            self.send_command("stop")
            return self.wait(timeout=graceful_timeout)
        except subprocess.TimeoutExpired:
            self._process.terminate()
            try:
                return self.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
                return self.wait(timeout=5)

    @property
    def recent_lines(self) -> list[str]:
        return list(self._recent_lines)

    @property
    def pid(self) -> int:
        return self._process.pid

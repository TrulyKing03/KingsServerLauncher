from __future__ import annotations

from pathlib import Path
import json
import queue
import threading
import traceback
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import webbrowser

try:
    from .catalog import VersionCatalog
    from .manager import ServerManager
    from .models import InstallRequest, InstallResult
    from .process import ServerProcess
except ImportError:  # pragma: no cover - fallback for direct/frozen entry
    from mcserverlib.catalog import VersionCatalog
    from mcserverlib.manager import ServerManager
    from mcserverlib.models import InstallRequest, InstallResult
    from mcserverlib.process import ServerProcess

DISCORD_URL = "https://discord.gg/AqUmRUshhK"
WEBSITE_URL = "https://TrulyKing.dev"


class LauncherApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("KingsServerLauncher")
        self.geometry("1180x780")
        self.minsize(1020, 700)

        self.manager = ServerManager()
        self.catalog = VersionCatalog(http_client=self.manager.http_client)

        self._ui_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._server_process: ServerProcess | None = None
        self._settings_path = Path.home() / ".kingsserverlauncher" / "settings.json"
        initial_instance_dir = self._load_saved_instance_dir()
        self._storage_selected = bool(initial_instance_dir)

        self.instance_dir_var = tk.StringVar(value=initial_instance_dir)
        self.loader_var = tk.StringVar(value="paper")
        self.mc_version_var = tk.StringVar(value="latest")
        self.loader_version_var = tk.StringVar(value="")
        self.build_var = tk.StringVar(value="")
        self.java_path_var = tk.StringVar(value="java")
        self.accept_eula_var = tk.BooleanVar(value=True)
        self.xms_var = tk.StringVar(value="2G")
        self.xmx_var = tk.StringVar(value="4G")
        self.console_command_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Ready")

        self._configure_style()
        self._build_menu()
        self._build_ui()
        self._bind_events()
        self._sync_optional_fields()
        self._update_console_controls()
        self._enqueue_log(
            "Welcome to KingsServerLauncher. Choose your folder, loader, and version."
        )

        self.after(100, self._poll_ui_queue)
        self.after(1000, self._poll_process_state)
        self.after(150, self._ensure_storage_selected_on_startup)
        self._refresh_versions()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        available_themes = set(style.theme_names())
        for candidate in ("vista", "winnative", "clam"):
            if candidate in available_themes:
                style.theme_use(candidate)
                break

        available_fonts = set(tkfont.families(self))
        base_font = "Segoe UI" if "Segoe UI" in available_fonts else "TkDefaultFont"
        mono_font = "Cascadia Code" if "Cascadia Code" in available_fonts else "Consolas"
        if mono_font not in available_fonts:
            mono_font = "TkFixedFont"
        semibold_font = "Segoe UI Semibold" if "Segoe UI Semibold" in available_fonts else base_font
        title_font = "Bahnschrift SemiBold" if "Bahnschrift SemiBold" in available_fonts else semibold_font

        self.option_add("*Font", f"{base_font} 10")
        self._mono_font = mono_font
        self.configure(bg="#E9EEF8")

        style.configure("App.TFrame", background="#E9EEF8")
        style.configure("Card.TFrame", background="#FFFFFF", relief="flat")
        style.configure("Accent.TFrame", background="#0F172A")
        style.configure(
            "Header.TLabel",
            background="#0F172A",
            foreground="#F8FAFF",
            font=(title_font, 23),
        )
        style.configure(
            "SubHeader.TLabel",
            background="#0F172A",
            foreground="#B7C8E8",
            font=(base_font, 10),
        )
        style.configure(
            "FieldLabel.TLabel",
            background="#FFFFFF",
            foreground="#1E293B",
            font=(semibold_font, 10),
        )
        style.configure(
            "Status.TLabel",
            background="#FFFFFF",
            foreground="#0F172A",
            font=(semibold_font, 10),
        )
        style.configure(
            "Meta.TLabel",
            background="#FFFFFF",
            foreground="#5B6B86",
            font=(base_font, 9),
        )
        style.configure(
            "TEntry",
            fieldbackground="#F7FAFF",
            foreground="#0F172A",
            borderwidth=1,
            relief="solid",
            padding=(8, 6),
        )
        style.map(
            "TEntry",
            fieldbackground=[("readonly", "#EEF3FF"), ("disabled", "#F1F5FC")],
            foreground=[("disabled", "#7A869E")],
        )
        style.configure(
            "TCombobox",
            fieldbackground="#F7FAFF",
            foreground="#0F172A",
            arrowsize=16,
            borderwidth=1,
            padding=(8, 6),
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "#EEF3FF"), ("disabled", "#F1F5FC")],
            foreground=[("readonly", "#0F172A"), ("disabled", "#7A869E")],
        )
        style.configure(
            "Primary.TButton",
            font=(semibold_font, 10),
            padding=(14, 10),
            background="#2563EB",
            foreground="#FFFFFF",
            borderwidth=0,
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#1D4ED8"), ("disabled", "#A8B5CC")],
            foreground=[("disabled", "#E8ECF4")],
        )
        style.configure(
            "Secondary.TButton",
            font=(semibold_font, 9),
            padding=(12, 9),
            background="#E2E8F4",
            foreground="#1E293B",
            borderwidth=0,
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#D2DBED"), ("disabled", "#EEF2F9")],
            foreground=[("disabled", "#8A97B0")],
        )
        style.configure(
            "Action.TButton",
            font=(semibold_font, 10),
            padding=(14, 10),
            background="#16A34A",
            foreground="#FFFFFF",
            borderwidth=0,
        )
        style.map(
            "Action.TButton",
            background=[("active", "#15803D"), ("disabled", "#A8B5CC")],
            foreground=[("disabled", "#E8ECF4")],
        )
        style.configure(
            "Warn.TButton",
            font=(semibold_font, 10),
            padding=(14, 10),
            background="#DC2626",
            foreground="#FFFFFF",
            borderwidth=0,
        )
        style.map(
            "Warn.TButton",
            background=[("active", "#B91C1C"), ("disabled", "#A8B5CC")],
            foreground=[("disabled", "#E8ECF4")],
        )
        style.configure(
            "TCheckbutton",
            background="#FFFFFF",
            foreground="#1E293B",
            font=(base_font, 10),
        )
        style.map(
            "TCheckbutton",
            background=[("active", "#FFFFFF"), ("disabled", "#FFFFFF")],
            foreground=[("disabled", "#8A97B0")],
        )

    def _build_menu(self) -> None:
        menu = tk.Menu(self)
        help_menu = tk.Menu(menu, tearoff=0)
        help_menu.add_command(label="Join Discord", command=self._open_discord)
        help_menu.add_command(label="Open Website", command=self._open_website)
        help_menu.add_separator()
        help_menu.add_command(label="About KingsServerLauncher", command=self._show_about)
        menu.add_cascade(label="Help", menu=help_menu)
        self.configure(menu=menu)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="App.TFrame", padding=18)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=3)
        root.rowconfigure(2, weight=1)

        banner = ttk.Frame(root, style="Accent.TFrame", padding=(22, 18))
        banner.grid(row=0, column=0, sticky="ew")
        banner.columnconfigure(0, weight=1)
        ttk.Label(banner, text="KingsServerLauncher", style="Header.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            banner,
            text="Set up and control Minecraft servers with one launcher",
            style="SubHeader.TLabel",
        ).grid(row=1, column=0, sticky="w")
        link_row = ttk.Frame(banner, style="Accent.TFrame")
        link_row.grid(row=0, column=1, rowspan=2, sticky="e")
        ttk.Button(link_row, text="Discord", style="Secondary.TButton", command=self._open_discord).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(link_row, text="Website", style="Secondary.TButton", command=self._open_website).grid(
            row=0, column=1
        )

        body = ttk.Frame(root, style="App.TFrame")
        body.grid(row=2, column=0, sticky="nsew", pady=(14, 0))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(1, weight=1)

        left = ttk.Frame(body, style="Card.TFrame", padding=18)
        left.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10))
        left.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(left, text="Server Setup", style="FieldLabel.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        row += 1
        ttk.Label(
            left,
            text="Choose storage, loader, and runtime options.",
            style="Meta.TLabel",
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(2, 10))

        row += 1
        ttk.Label(left, text="Server Storage", style="FieldLabel.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        row += 1
        ttk.Entry(left, textvariable=self.instance_dir_var).grid(
            row=row, column=0, sticky="ew", pady=(6, 8)
        )
        ttk.Button(
            left,
            text="Choose Folder",
            style="Secondary.TButton",
            command=self._browse_instance_dir,
        ).grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=(6, 8))

        row += 1
        ttk.Label(left, text="Loader", style="FieldLabel.TLabel").grid(row=row, column=0, sticky="w")
        ttk.Label(left, text="Minecraft Version", style="FieldLabel.TLabel").grid(
            row=row, column=1, sticky="w", padx=(8, 0)
        )
        row += 1
        self.loader_combo = ttk.Combobox(
            left,
            textvariable=self.loader_var,
            values=list(self.manager.supported_loaders),
            state="readonly",
            width=20,
        )
        self.loader_combo.grid(row=row, column=0, sticky="ew", pady=(6, 8))
        self.mc_version_combo = ttk.Combobox(left, textvariable=self.mc_version_var, values=["latest"])
        self.mc_version_combo.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=(6, 8))

        row += 1
        self.refresh_versions_btn = ttk.Button(
            left,
            text="Refresh Versions",
            style="Secondary.TButton",
            command=self._refresh_versions,
        )
        self.refresh_versions_btn.grid(row=row, column=0, columnspan=2, sticky="ew")

        row += 1
        ttk.Label(left, text="Loader Version (Optional)", style="FieldLabel.TLabel").grid(
            row=row, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Label(left, text="Build (Optional)", style="FieldLabel.TLabel").grid(
            row=row, column=1, sticky="w", padx=(8, 0), pady=(10, 0)
        )
        row += 1
        self.loader_version_combo = ttk.Combobox(left, textvariable=self.loader_version_var)
        self.loader_version_combo.grid(row=row, column=0, sticky="ew", pady=(6, 8))
        self.build_entry = ttk.Entry(left, textvariable=self.build_var)
        self.build_entry.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=(6, 8))

        row += 1
        self.refresh_loader_versions_btn = ttk.Button(
            left,
            text="Refresh Loader Versions",
            style="Secondary.TButton",
            command=self._refresh_loader_versions,
        )
        self.refresh_loader_versions_btn.grid(row=row, column=0, columnspan=2, sticky="ew")

        row += 1
        ttk.Label(left, text="Java Path", style="FieldLabel.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )
        row += 1
        ttk.Entry(left, textvariable=self.java_path_var).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(6, 8)
        )

        row += 1
        memory = ttk.Frame(left, style="Card.TFrame")
        memory.grid(row=row, column=0, columnspan=2, sticky="ew")
        ttk.Label(memory, text="Xms", style="FieldLabel.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(memory, textvariable=self.xms_var, width=12).grid(row=0, column=1, padx=(8, 24))
        ttk.Label(memory, text="Xmx", style="FieldLabel.TLabel").grid(row=0, column=2, sticky="w")
        ttk.Entry(memory, textvariable=self.xmx_var, width=12).grid(row=0, column=3, padx=(8, 0))

        row += 1
        ttk.Checkbutton(left, text="Accept EULA", variable=self.accept_eula_var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )

        row += 1
        actions = ttk.Frame(left, style="Card.TFrame")
        actions.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.columnconfigure(2, weight=1)
        self.install_btn = ttk.Button(actions, text="Install", style="Primary.TButton", command=self._install)
        self.install_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.start_btn = ttk.Button(actions, text="Start", style="Action.TButton", command=self._start)
        self.start_btn.grid(row=0, column=1, sticky="ew", padx=6)
        self.stop_btn = ttk.Button(actions, text="Stop", style="Warn.TButton", command=self._stop)
        self.stop_btn.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        row += 1
        util_row = ttk.Frame(left, style="Card.TFrame")
        util_row.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        util_row.columnconfigure(0, weight=1)
        util_row.columnconfigure(1, weight=1)
        ttk.Button(
            util_row,
            text="Open Folder",
            style="Secondary.TButton",
            command=self._open_instance_dir,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            util_row,
            text="Clear Log",
            style="Secondary.TButton",
            command=self._clear_log,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        right_top = ttk.Frame(body, style="Card.TFrame", padding=14)
        right_top.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        right_top.columnconfigure(0, weight=1)
        ttk.Label(right_top, textvariable=self.status_var, style="Status.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.progress = ttk.Progressbar(right_top, mode="indeterminate")
        self.progress.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        right = ttk.Frame(body, style="Card.TFrame", padding=14)
        right.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(10, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)
        ttk.Label(right, text="Server Console", style="FieldLabel.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            right,
            text="Live output and command input while the server is running.",
            style="Meta.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.log_area = ScrolledText(
            right,
            wrap=tk.WORD,
            height=16,
            bg="#0B1220",
            fg="#E7EFFD",
            insertbackground="#E7EFFD",
            relief=tk.FLAT,
            padx=8,
            pady=8,
            borderwidth=0,
            font=(self._mono_font, 10),
        )
        self.log_area.grid(row=2, column=0, sticky="nsew", pady=(8, 8))
        self.log_area.configure(state=tk.DISABLED)

        console = ttk.Frame(right, style="Card.TFrame")
        console.grid(row=3, column=0, sticky="ew")
        console.columnconfigure(1, weight=1)
        ttk.Label(console, text="Console Command", style="FieldLabel.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.console_entry = ttk.Entry(console, textvariable=self.console_command_var)
        self.console_entry.grid(row=0, column=1, sticky="ew", padx=8)
        self.send_command_btn = ttk.Button(
            console,
            text="Send",
            style="Primary.TButton",
            command=self._send_console_command,
        )
        self.send_command_btn.grid(row=0, column=2, sticky="ew")

    def _bind_events(self) -> None:
        self.loader_combo.bind("<<ComboboxSelected>>", self._on_loader_changed)
        self.mc_version_combo.bind("<<ComboboxSelected>>", self._on_minecraft_version_changed)
        self.console_entry.bind("<Return>", self._send_console_command)

    def _open_discord(self) -> None:
        self._open_url(DISCORD_URL)

    def _open_website(self) -> None:
        self._open_url(WEBSITE_URL)

    def _open_url(self, url: str) -> None:
        webbrowser.open_new_tab(url)

    def _show_about(self) -> None:
        messagebox.showinfo(
            "KingsServerLauncher",
            "KingsServerLauncher\n\n"
            "Install and control Minecraft servers across major loaders.",
        )

    def _on_loader_changed(self, _event: object = None) -> None:
        self.loader_version_var.set("")
        self.build_var.set("")
        self._sync_optional_fields()
        self._refresh_versions()

    def _on_minecraft_version_changed(self, _event: object = None) -> None:
        self._refresh_loader_versions()

    def _sync_optional_fields(self) -> None:
        loader = self.loader_var.get()
        loader_version_supported = loader in {"fabric", "quilt", "forge", "neoforge"}
        build_supported = loader in {"paper", "folia", "purpur"}

        self.loader_version_combo.configure(
            state="normal" if loader_version_supported else "disabled"
        )
        self.refresh_loader_versions_btn.configure(
            state="normal" if loader_version_supported else "disabled"
        )
        self.build_entry.configure(state="normal" if build_supported else "disabled")

    def _browse_instance_dir(self) -> None:
        initial_dir = self.instance_dir_var.get().strip()
        if not initial_dir:
            initial_dir = str((Path.cwd() / "servers").resolve())
        selected = filedialog.askdirectory(
            title="Choose where server files should be stored",
            initialdir=initial_dir,
        )
        if selected:
            self.instance_dir_var.set(selected)
            self._storage_selected = True
            self._save_settings()

    def _ensure_storage_selected_on_startup(self) -> None:
        if self._storage_selected:
            return
        self._enqueue_log("Choose where server files should be stored before running installs.")
        chosen = self._choose_storage_folder()
        if not chosen:
            fallback = str((Path.cwd() / "servers" / "my-server").resolve())
            self.instance_dir_var.set(fallback)
            self._enqueue_log(
                f"No storage folder selected. Using temporary default: {fallback}"
            )

    def _ensure_storage_before_action(self) -> bool:
        current = self.instance_dir_var.get().strip()
        if current:
            return True
        return self._choose_storage_folder()

    def _choose_storage_folder(self) -> bool:
        selected = filedialog.askdirectory(
            title="Choose where server files should be stored",
            initialdir=str((Path.cwd() / "servers").resolve()),
        )
        if not selected:
            return False
        self.instance_dir_var.set(selected)
        self._storage_selected = True
        self._save_settings()
        self._enqueue_log(f"Server storage folder set to: {selected}")
        return True

    def _open_instance_dir(self) -> None:
        if not self._ensure_storage_before_action():
            self._set_status("Choose a folder first.")
            return
        path = Path(self.instance_dir_var.get()).resolve()
        path.mkdir(parents=True, exist_ok=True)
        try:
            self._launch_folder(str(path))
            self._set_status(f"Opened folder: {path}")
        except Exception as exc:
            self._set_status(f"Could not open folder: {exc}")

    def _clear_log(self) -> None:
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.delete("1.0", tk.END)
        self.log_area.configure(state=tk.DISABLED)

    def _refresh_versions(self) -> None:
        loader = self.loader_var.get()
        self._run_background_task(
            "refresh_versions",
            lambda: self.catalog.list_minecraft_versions(loader=loader),
        )

    def _refresh_loader_versions(self) -> None:
        loader = self.loader_var.get()
        mc_version = (self.mc_version_var.get() or "latest").strip()
        if mc_version.lower() == "latest":
            self.loader_version_combo["values"] = []
            return
        self._run_background_task(
            "refresh_loader_versions",
            lambda: self.catalog.list_loader_versions(
                loader=loader,
                minecraft_version=mc_version,
            ),
        )

    def _install(self) -> None:
        if not self._ensure_storage_before_action():
            self._set_status("Install cancelled: choose a storage folder first.")
            return

        loader = self.loader_var.get().strip()
        minecraft_version = (self.mc_version_var.get() or "latest").strip()
        loader_version = self.loader_version_var.get().strip() or None
        build = self.build_var.get().strip() or None
        instance_dir = Path(self.instance_dir_var.get().strip()).resolve()
        java_path = self.java_path_var.get().strip() or "java"
        accept_eula = bool(self.accept_eula_var.get())

        request = InstallRequest(
            loader=loader,
            instance_dir=instance_dir,
            minecraft_version=minecraft_version,
            loader_version=loader_version,
            build=build,
            java_path=java_path,
            accept_eula=accept_eula,
        )
        self._run_background_task("install", lambda: self.manager.install(request))

    def _start(self) -> None:
        if not self._ensure_storage_before_action():
            self._set_status("Start cancelled: choose a storage folder first.")
            return

        if self._server_process and self._server_process.is_running():
            self._set_status("Server is already running.")
            return

        instance_dir = Path(self.instance_dir_var.get().strip()).resolve()
        java_path = self.java_path_var.get().strip() or "java"
        xms = self.xms_var.get().strip() or None
        xmx = self.xmx_var.get().strip() or None

        def _start_server() -> ServerProcess:
            return self.manager.start(
                instance_dir=instance_dir,
                java_path=java_path,
                xms=xms,
                xmx=xmx,
                log_handler=self._enqueue_log,
            )

        self._run_background_task("start", _start_server)

    def _stop(self) -> None:
        process = self._server_process
        if not process or not process.is_running():
            self._set_status("No running server process.")
            return
        self._run_background_task("stop", lambda: process.stop(graceful_timeout=45.0))

    def _set_controls_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.install_btn.configure(state=state)
        self.start_btn.configure(state=state)
        if hasattr(self, "refresh_versions_btn"):
            self.refresh_versions_btn.configure(state=state)
        if (
            hasattr(self, "refresh_loader_versions_btn")
            and self.loader_var.get() in {"fabric", "quilt", "forge", "neoforge"}
        ):
            self.refresh_loader_versions_btn.configure(state=state)
        self._update_console_controls()

    def _update_console_controls(self) -> None:
        process_running = bool(self._server_process and self._server_process.is_running())
        console_state = "normal" if process_running else "disabled"
        self.console_entry.configure(state=console_state)
        self.send_command_btn.configure(state=console_state)

    def _run_background_task(self, task_name: str, fn) -> None:
        if self._worker and self._worker.is_alive():
            self._set_status("Another task is already running.")
            return

        def _runner() -> None:
            try:
                result = fn()
                self._ui_queue.put(("task_done", (task_name, result)))
            except Exception as exc:
                details = "".join(traceback.format_exception(exc))
                self._ui_queue.put(("task_error", (task_name, str(exc), details)))

        worker = threading.Thread(target=_runner, daemon=True)
        worker.start()
        self._worker = worker
        self._set_controls_enabled(False)
        self.progress.start(10)
        self._set_status(f"Running: {task_name}")

    def _poll_ui_queue(self) -> None:
        while True:
            try:
                event, payload = self._ui_queue.get_nowait()
            except queue.Empty:
                break

            if event == "log":
                self._append_log(str(payload))
                continue

            if event == "task_done":
                task_name, result = payload  # type: ignore[misc]
                self._handle_task_done(str(task_name), result)
                continue

            if event == "task_error":
                task_name, short_error, full_error = payload  # type: ignore[misc]
                self._append_log(full_error)
                self._set_status(f"{task_name} failed: {short_error}")
                messagebox.showerror("Task Failed", f"{task_name} failed:\n{short_error}")
                self.progress.stop()
                self._set_controls_enabled(True)

        self.after(100, self._poll_ui_queue)

    def _handle_task_done(self, task_name: str, result: object) -> None:
        if task_name == "refresh_versions":
            versions = ["latest"] + [str(v) for v in result]  # type: ignore[arg-type]
            self.mc_version_combo["values"] = versions
            if self.mc_version_var.get() not in versions:
                self.mc_version_var.set("latest")
            self._set_status("Version list refreshed.")
            self.progress.stop()
            self._set_controls_enabled(True)
            return

        if task_name == "refresh_loader_versions":
            versions = [str(v) for v in result]  # type: ignore[arg-type]
            self.loader_version_combo["values"] = versions
            self._set_status("Loader version list refreshed.")
            self.progress.stop()
            self._set_controls_enabled(True)
            return

        if task_name == "install":
            install_result = result  # type: ignore[assignment]
            if isinstance(install_result, InstallResult):
                self._append_log(
                    "Installed "
                    f"{install_result.manifest.loader} "
                    f"{install_result.manifest.minecraft_version} "
                    f"at {install_result.instance_dir}"
                )
            self._set_status("Install completed.")
            self.progress.stop()
            self._set_controls_enabled(True)
            return

        if task_name == "start":
            process = result  # type: ignore[assignment]
            if isinstance(process, ServerProcess):
                self._server_process = process
                self._append_log(f"Server started (PID {process.pid}).")
                self._set_status("Server running.")
                self._update_console_controls()
            self.progress.stop()
            self._set_controls_enabled(True)
            return

        if task_name == "stop":
            exit_code = int(result)
            self._append_log(f"Server stopped with exit code {exit_code}.")
            self._server_process = None
            self._set_status("Server stopped.")
            self._update_console_controls()
            self.progress.stop()
            self._set_controls_enabled(True)
            return

    def _launch_folder(self, path: str) -> None:
        import os
        import subprocess
        import sys

        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
            return
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
            return
        subprocess.Popen(["xdg-open", path])

    def _poll_process_state(self) -> None:
        if self._server_process and not self._server_process.is_running():
            code = self._server_process.poll()
            self._append_log(f"Server exited with code {code}.")
            self._set_status("Server not running.")
            self._server_process = None
            self._update_console_controls()
        self.after(1000, self._poll_process_state)

    def _enqueue_log(self, line: str) -> None:
        self._ui_queue.put(("log", line))

    def _send_console_command(self, _event: object = None) -> None:
        command = self.console_command_var.get().strip()
        if not command:
            return
        process = self._server_process
        if not process or not process.is_running():
            self._set_status("Cannot send command: server is not running.")
            self._update_console_controls()
            return
        process.send_command(command)
        self._append_log(f"> {command}")
        self.console_command_var.set("")

    def _append_log(self, line: str) -> None:
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.insert(tk.END, line.rstrip() + "\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state=tk.DISABLED)

    def _set_status(self, status: str) -> None:
        self.status_var.set(status)

    def _load_saved_instance_dir(self) -> str:
        payload = self._load_settings()
        instance_dir = str(payload.get("instance_dir", "")).strip()
        return instance_dir

    def _load_settings(self) -> dict[str, str]:
        if not self._settings_path.exists():
            return {}
        try:
            with self._settings_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                return {str(k): str(v) for k, v in payload.items()}
        except Exception:
            return {}
        return {}

    def _save_settings(self) -> None:
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"instance_dir": self.instance_dir_var.get().strip()}
        with self._settings_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")


def main() -> int:
    app = LauncherApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

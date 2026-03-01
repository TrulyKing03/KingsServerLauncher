from __future__ import annotations

from pathlib import Path
import json
import queue
import socket
import sys
import threading
import traceback
import tkinter as tk
import tkinter.font as tkfont
import urllib.parse
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import webbrowser

try:
    from .catalog import VersionCatalog
    from .manager import ServerManager
    from .models import InstallRequest, InstallResult
    from .process import ServerProcess
    from .utils import read_server_endpoint
except ImportError:  # pragma: no cover - fallback for direct/frozen entry
    from mcserverlib.catalog import VersionCatalog
    from mcserverlib.manager import ServerManager
    from mcserverlib.models import InstallRequest, InstallResult
    from mcserverlib.process import ServerProcess
    from mcserverlib.utils import read_server_endpoint

DISCORD_URL = "https://discord.gg/AqUmRUshhK"
WEBSITE_URL = "https://TrulyKing.dev"
ALLOWED_EXTERNAL_HOSTS = {"discord.gg", "trulyking.dev", "www.trulyking.dev"}
ASSETS_DIRNAME = "assets"
LOGO_CANDIDATE_NAMES = (
    "logo.png",
    "logo.jpg",
    "logo.jpeg",
    "kings-logo.png",
)
ICON_CANDIDATE_NAMES = (
    "icon.png",
    "kings-icon.png",
    "logo.png",
)


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
        self.server_endpoint_var = tk.StringVar(value="Choose a folder")
        self.console_state_var = tk.StringVar(value="Offline")
        self._controls_busy = False
        self._command_placeholder = "Type a command..."
        self._command_placeholder_active = False
        self._logo_image: tk.PhotoImage | None = None
        self._window_icon_image: tk.PhotoImage | None = None

        self._load_brand_assets()
        self._apply_window_icon()
        self._configure_style()
        self._build_menu()
        self._build_ui()
        self._bind_events()
        self._sync_optional_fields()
        self._update_console_controls()
        self._update_runtime_controls()
        self._refresh_server_endpoint()
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
        for candidate in ("clam", "vista", "winnative"):
            if candidate in available_themes:
                style.theme_use(candidate)
                break

        available_fonts = set(tkfont.families(self))
        for candidate in ("Inter", "Segoe UI Variable Text", "Segoe UI"):
            if candidate in available_fonts:
                base_font = candidate
                break
        else:
            base_font = "TkDefaultFont"
        mono_font = "JetBrains Mono" if "JetBrains Mono" in available_fonts else "Cascadia Code"
        if mono_font not in available_fonts:
            mono_font = "Consolas" if "Consolas" in available_fonts else "TkFixedFont"
        semibold_font = (
            "Inter SemiBold"
            if "Inter SemiBold" in available_fonts
            else ("Segoe UI Semibold" if "Segoe UI Semibold" in available_fonts else base_font)
        )
        title_font = (
            "Inter SemiBold"
            if "Inter SemiBold" in available_fonts
            else ("Segoe UI Semibold" if "Segoe UI Semibold" in available_fonts else base_font)
        )

        self.option_add("*Font", f"{{{base_font}}} 10")
        self._mono_font = mono_font

        self._colors = {
            "app_bg": "#080D18",
            "header_bg": "#0E1528",
            "card_bg": "#10192C",
            "input_bg": "#131F35",
            "console_bg": "#0B0F17",
            "text_primary": "#EAF1FF",
            "text_secondary": "#A2B2D2",
            "text_muted": "#7D8DAF",
            "accent": "#3C7BFF",
            "accent_hover": "#4D89FF",
            "accent_pressed": "#2F67DD",
            "danger": "#D84F5B",
            "danger_hover": "#E0636E",
            "danger_pressed": "#B8404A",
            "neutral": "#1A2641",
            "neutral_hover": "#213152",
            "neutral_pressed": "#17253F",
            "banner_bg": "#2A1217",
            "banner_fg": "#FF7A86",
            "progress_trough": "#0E1628",
            "progress_fill": "#4D93FF",
            "state_online": "#3FC272",
            "state_offline": "#6A7794",
        }
        colors = self._colors

        self.configure(bg=colors["app_bg"])

        style.configure("App.TFrame", background=colors["app_bg"])
        style.configure("HeaderCard.TFrame", background=colors["header_bg"], relief="flat")
        style.configure("Card.TFrame", background=colors["card_bg"], relief="flat")
        style.configure("Banner.TFrame", background=colors["banner_bg"], relief="flat")
        style.configure("Logo.TLabel", background=colors["header_bg"])
        style.configure(
            "HeaderTitle.TLabel",
            background=colors["header_bg"],
            foreground=colors["text_primary"],
            font=(title_font, 19),
        )
        style.configure(
            "HeaderSub.TLabel",
            background=colors["header_bg"],
            foreground=colors["text_secondary"],
            font=(base_font, 11),
        )
        style.configure(
            "Banner.TLabel",
            background=colors["banner_bg"],
            foreground=colors["banner_fg"],
            font=(semibold_font, 10),
        )
        style.configure(
            "CardTitle.TLabel",
            background=colors["card_bg"],
            foreground=colors["text_primary"],
            font=(semibold_font, 15),
        )
        style.configure(
            "CardSub.TLabel",
            background=colors["card_bg"],
            foreground=colors["text_secondary"],
            font=(base_font, 12),
        )
        style.configure(
            "FieldLabel.TLabel",
            background=colors["card_bg"],
            foreground=colors["text_primary"],
            font=(semibold_font, 10),
        )
        style.configure(
            "Meta.TLabel",
            background=colors["card_bg"],
            foreground=colors["text_secondary"],
            font=(base_font, 9),
        )
        style.configure(
            "StatusKey.TLabel",
            background=colors["card_bg"],
            foreground=colors["text_muted"],
            font=(semibold_font, 11),
        )
        style.configure(
            "StatusValue.TLabel",
            background=colors["card_bg"],
            foreground=colors["text_primary"],
            font=(base_font, 11),
        )
        style.configure(
            "ConsoleState.TLabel",
            background=colors["card_bg"],
            foreground=colors["text_secondary"],
            font=(semibold_font, 10),
        )
        style.configure(
            "Input.TEntry",
            fieldbackground=colors["input_bg"],
            foreground=colors["text_primary"],
            borderwidth=0,
            relief="flat",
            padding=(12, 9),
        )
        style.map(
            "Input.TEntry",
            fieldbackground=[
                ("focus", "#1A2A46"),
                ("readonly", "#17253E"),
                ("disabled", "#121A2C"),
            ],
            foreground=[("disabled", "#6D7C9A")],
        )
        style.configure(
            "Placeholder.TEntry",
            fieldbackground=colors["input_bg"],
            foreground=colors["text_muted"],
            borderwidth=0,
            relief="flat",
            padding=(12, 9),
        )
        style.configure(
            "Input.TCombobox",
            fieldbackground=colors["input_bg"],
            foreground=colors["text_primary"],
            arrowsize=16,
            borderwidth=0,
            relief="flat",
            padding=(12, 9),
        )
        style.map(
            "Input.TCombobox",
            fieldbackground=[
                ("readonly", "#17253E"),
                ("focus", "#1A2A46"),
                ("disabled", "#121A2C"),
            ],
            foreground=[("readonly", colors["text_primary"]), ("disabled", "#6D7C9A")],
        )
        style.configure(
            "Primary.TButton",
            font=(semibold_font, 10),
            padding=(12, 10),
            background=colors["accent"],
            foreground="#FFFFFF",
            borderwidth=0,
        )
        style.map(
            "Primary.TButton",
            background=[
                ("pressed", colors["accent_pressed"]),
                ("active", colors["accent_hover"]),
                ("disabled", "#27314C"),
            ],
            foreground=[("disabled", "#8FA1C5")],
        )
        style.configure(
            "Secondary.TButton",
            font=(semibold_font, 10),
            padding=(12, 10),
            background=colors["neutral"],
            foreground=colors["text_primary"],
            borderwidth=0,
        )
        style.map(
            "Secondary.TButton",
            background=[
                ("pressed", colors["neutral_pressed"]),
                ("active", colors["neutral_hover"]),
                ("disabled", "#1C263D"),
            ],
            foreground=[("disabled", "#7486AB")],
        )
        style.configure(
            "Danger.TButton",
            font=(semibold_font, 10),
            padding=(12, 10),
            background=colors["danger"],
            foreground="#FFFFFF",
            borderwidth=0,
        )
        style.map(
            "Danger.TButton",
            background=[
                ("pressed", colors["danger_pressed"]),
                ("active", colors["danger_hover"]),
                ("disabled", "#3B2A35"),
            ],
            foreground=[("disabled", "#B6979E")],
        )
        style.configure(
            "Link.TButton",
            font=(semibold_font, 10),
            padding=(12, 9),
            background=colors["neutral"],
            foreground=colors["text_primary"],
            borderwidth=0,
        )
        style.map(
            "Link.TButton",
            background=[
                ("pressed", colors["neutral_pressed"]),
                ("active", colors["neutral_hover"]),
                ("disabled", "#1C263D"),
            ],
            foreground=[("disabled", "#7486AB")],
        )
        style.configure(
            "TCheckbutton",
            background=colors["card_bg"],
            foreground=colors["text_primary"],
            font=(base_font, 10),
        )
        style.map(
            "TCheckbutton",
            background=[("active", colors["card_bg"]), ("disabled", colors["card_bg"])],
            foreground=[("disabled", "#6A80A8")],
        )
        style.configure(
            "Launch.Horizontal.TProgressbar",
            troughcolor=colors["progress_trough"],
            background=colors["progress_fill"],
            lightcolor=colors["progress_fill"],
            darkcolor=colors["progress_fill"],
            bordercolor=colors["progress_trough"],
        )

    @staticmethod
    def _project_root() -> Path:
        return Path(__file__).resolve().parent.parent

    def _asset_search_roots(self) -> list[Path]:
        roots: list[Path] = []
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                roots.append(Path(meipass))
            roots.append(Path(sys.executable).resolve().parent)
        roots.append(self._project_root())
        return roots

    def _resolve_brand_asset(self, candidates: tuple[str, ...]) -> Path | None:
        for root in self._asset_search_roots():
            assets_dir = root / ASSETS_DIRNAME
            for name in candidates:
                candidate = assets_dir / name
                if candidate.exists():
                    return candidate
        return None

    @staticmethod
    def _load_scaled_photo(path: Path, max_width: int) -> tk.PhotoImage | None:
        try:
            image = tk.PhotoImage(file=str(path))
        except tk.TclError:
            return None
        width = image.width() or 1
        sample = max(1, (width + max_width - 1) // max_width)
        if sample > 1:
            image = image.subsample(sample, sample)
        return image

    def _load_brand_assets(self) -> None:
        logo_path = self._resolve_brand_asset(LOGO_CANDIDATE_NAMES)
        if logo_path:
            self._logo_image = self._load_scaled_photo(logo_path, max_width=84)

        icon_path = self._resolve_brand_asset(ICON_CANDIDATE_NAMES)
        if not icon_path:
            icon_path = logo_path
        if icon_path:
            self._window_icon_image = self._load_scaled_photo(icon_path, max_width=128)

    def _apply_window_icon(self) -> None:
        if self._window_icon_image is None:
            return
        try:
            self.iconphoto(True, self._window_icon_image)
        except tk.TclError:
            return

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
        outer_padding = 24
        card_padding = 24
        section_gap = 16
        row_gap = 8
        col_gap = 12

        root = ttk.Frame(self, style="App.TFrame", padding=(outer_padding, outer_padding))
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        header = ttk.Frame(root, style="HeaderCard.TFrame", padding=card_padding)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        text_col = 1
        if self._logo_image is not None:
            ttk.Label(header, image=self._logo_image, style="Logo.TLabel").grid(
                row=0,
                column=0,
                rowspan=2,
                sticky="w",
                padx=(0, section_gap),
            )
        else:
            text_col = 0
        ttk.Label(header, text="KingsServerLauncher", style="HeaderTitle.TLabel").grid(
            row=0,
            column=text_col,
            sticky="w",
        )
        ttk.Label(
            header,
            text="Launch, install, and control Minecraft servers from one client dashboard.",
            style="HeaderSub.TLabel",
        ).grid(row=1, column=text_col, sticky="w", pady=(6, 0))

        links = ttk.Frame(header, style="HeaderCard.TFrame")
        links.grid(row=0, column=text_col + 1, rowspan=2, sticky="e", padx=(section_gap, 0))
        self.discord_btn = ttk.Button(
            links,
            text="Discord",
            style="Link.TButton",
            command=self._open_discord,
        )
        self.discord_btn.grid(row=0, column=0, sticky="ew", padx=(0, col_gap))
        self.website_btn = ttk.Button(
            links,
            text="Website",
            style="Link.TButton",
            command=self._open_website,
        )
        self.website_btn.grid(row=0, column=1, sticky="ew")

        banner = ttk.Frame(root, style="Banner.TFrame", padding=(16, 10))
        banner.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        ttk.Label(
            banner,
            text="Whitelist is ON by default after install. Turn it off and save in server.properties if needed.",
            style="Banner.TLabel",
        ).grid(row=0, column=0, sticky="w")

        body = ttk.Frame(root, style="App.TFrame")
        body.grid(row=2, column=0, sticky="nsew", pady=(section_gap, 0))
        body.columnconfigure(0, weight=11)
        body.columnconfigure(1, weight=12)
        body.rowconfigure(1, weight=1)

        left = ttk.Frame(body, style="Card.TFrame", padding=card_padding)
        left.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, section_gap))
        left.columnconfigure(0, weight=1)
        left.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(left, text="Server Setup", style="CardTitle.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        row += 1
        ttk.Label(
            left,
            text="Pick storage, loader, version, and runtime settings.",
            style="CardSub.TLabel",
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(6, section_gap))

        row += 1
        ttk.Label(left, text="Server Storage", style="FieldLabel.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        row += 1
        self.instance_dir_entry = ttk.Entry(left, textvariable=self.instance_dir_var, style="Input.TEntry")
        self.instance_dir_entry.grid(row=row, column=0, sticky="ew")
        self.browse_folder_btn = ttk.Button(
            left,
            text="Choose Folder",
            style="Secondary.TButton",
            command=self._browse_instance_dir,
        )
        self.browse_folder_btn.grid(row=row, column=1, sticky="ew", padx=(col_gap, 0))

        row += 1
        ttk.Label(left, text="Loader", style="FieldLabel.TLabel").grid(
            row=row, column=0, sticky="w", pady=(section_gap, 6)
        )
        ttk.Label(left, text="Minecraft Version", style="FieldLabel.TLabel").grid(
            row=row, column=1, sticky="w", padx=(col_gap, 0), pady=(section_gap, 6)
        )
        row += 1
        self.loader_combo = ttk.Combobox(
            left,
            textvariable=self.loader_var,
            values=list(self.manager.supported_loaders),
            style="Input.TCombobox",
            state="readonly",
            width=20,
        )
        self.loader_combo.grid(row=row, column=0, sticky="ew")
        self.mc_version_combo = ttk.Combobox(
            left,
            textvariable=self.mc_version_var,
            values=["latest"],
            style="Input.TCombobox",
            state="readonly",
        )
        self.mc_version_combo.grid(row=row, column=1, sticky="ew", padx=(col_gap, 0))

        row += 1
        self.refresh_versions_btn = ttk.Button(
            left,
            text="Refresh Versions",
            style="Secondary.TButton",
            command=self._refresh_versions,
        )
        self.refresh_versions_btn.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(row_gap, 0),
        )

        row += 1
        ttk.Label(left, text="Loader Version (Optional)", style="FieldLabel.TLabel").grid(
            row=row, column=0, sticky="w", pady=(section_gap, 6)
        )
        ttk.Label(left, text="Build (Optional)", style="FieldLabel.TLabel").grid(
            row=row, column=1, sticky="w", padx=(col_gap, 0), pady=(section_gap, 6)
        )
        row += 1
        self.loader_version_combo = ttk.Combobox(
            left,
            textvariable=self.loader_version_var,
            style="Input.TCombobox",
        )
        self.loader_version_combo.grid(row=row, column=0, sticky="ew")
        self.build_entry = ttk.Entry(left, textvariable=self.build_var, style="Input.TEntry")
        self.build_entry.grid(row=row, column=1, sticky="ew", padx=(col_gap, 0))

        row += 1
        self.refresh_loader_versions_btn = ttk.Button(
            left,
            text="Refresh Loader Versions",
            style="Secondary.TButton",
            command=self._refresh_loader_versions,
        )
        self.refresh_loader_versions_btn.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(row_gap, 0),
        )

        row += 1
        ttk.Label(left, text="Java Path", style="FieldLabel.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(section_gap, 6)
        )
        row += 1
        self.java_path_entry = ttk.Entry(left, textvariable=self.java_path_var, style="Input.TEntry")
        self.java_path_entry.grid(row=row, column=0, columnspan=2, sticky="ew")

        row += 1
        memory = ttk.Frame(left, style="Card.TFrame")
        memory.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(section_gap, 0))
        memory.columnconfigure(1, weight=1)
        memory.columnconfigure(3, weight=1)
        ttk.Label(memory, text="Xms", style="FieldLabel.TLabel").grid(row=0, column=0, sticky="w")
        self.xms_entry = ttk.Entry(memory, textvariable=self.xms_var, style="Input.TEntry", width=12)
        self.xms_entry.grid(row=0, column=1, sticky="ew", padx=(8, 20))
        ttk.Label(memory, text="Xmx", style="FieldLabel.TLabel").grid(row=0, column=2, sticky="w")
        self.xmx_entry = ttk.Entry(memory, textvariable=self.xmx_var, style="Input.TEntry", width=12)
        self.xmx_entry.grid(row=0, column=3, sticky="ew", padx=(8, 0))

        row += 1
        self.accept_eula_checkbox = ttk.Checkbutton(
            left,
            text="Accept EULA",
            variable=self.accept_eula_var,
        )
        self.accept_eula_checkbox.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(section_gap, 0),
        )

        row += 1
        actions = ttk.Frame(left, style="Card.TFrame")
        actions.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(section_gap, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.columnconfigure(2, weight=1)
        self.install_btn = ttk.Button(
            actions,
            text="Install",
            style="Secondary.TButton",
            command=self._install,
        )
        self.install_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.start_btn = ttk.Button(actions, text="Start", style="Primary.TButton", command=self._start)
        self.start_btn.grid(row=0, column=1, sticky="ew", padx=6)
        self.stop_btn = ttk.Button(actions, text="Stop", style="Danger.TButton", command=self._stop)
        self.stop_btn.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        row += 1
        util_row = ttk.Frame(left, style="Card.TFrame")
        util_row.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(row_gap, 0))
        util_row.columnconfigure(0, weight=1)
        util_row.columnconfigure(1, weight=1)
        self.open_folder_btn = ttk.Button(
            util_row,
            text="Open Folder",
            style="Secondary.TButton",
            command=self._open_instance_dir,
        )
        self.open_folder_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.clear_log_btn = ttk.Button(
            util_row,
            text="Clear Log",
            style="Secondary.TButton",
            command=self._clear_log,
        )
        self.clear_log_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        status_card = ttk.Frame(body, style="Card.TFrame", padding=card_padding)
        status_card.grid(row=0, column=1, sticky="ew")
        status_card.columnconfigure(0, weight=1)
        ttk.Label(status_card, text="Status", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            status_card,
            text="Install and runtime state for the selected server.",
            style="CardSub.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(6, section_gap))

        status_grid = ttk.Frame(status_card, style="Card.TFrame")
        status_grid.grid(row=2, column=0, sticky="ew")
        status_grid.columnconfigure(1, weight=1)
        ttk.Label(status_grid, text="Status", style="StatusKey.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, col_gap)
        )
        ttk.Label(status_grid, textvariable=self.status_var, style="StatusValue.TLabel").grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(status_grid, text="Address", style="StatusKey.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, col_gap), pady=(8, 0)
        )
        ttk.Label(status_grid, textvariable=self.server_endpoint_var, style="StatusValue.TLabel").grid(
            row=1, column=1, sticky="w", pady=(8, 0)
        )

        self.progress = ttk.Progressbar(
            status_card,
            mode="indeterminate",
            style="Launch.Horizontal.TProgressbar",
        )
        self.progress.grid(row=3, column=0, sticky="ew", pady=(section_gap, 0), ipady=1)

        console_card = ttk.Frame(body, style="Card.TFrame", padding=card_padding)
        console_card.grid(row=1, column=1, sticky="nsew", pady=(section_gap, 0))
        console_card.columnconfigure(0, weight=1)
        console_card.rowconfigure(2, weight=1)

        console_header = ttk.Frame(console_card, style="Card.TFrame")
        console_header.grid(row=0, column=0, sticky="ew")
        console_header.columnconfigure(0, weight=1)
        ttk.Label(console_header, text="Server Console", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        state_wrap = ttk.Frame(console_header, style="Card.TFrame")
        state_wrap.grid(row=0, column=1, sticky="e")
        self.console_state_dot = tk.Canvas(
            state_wrap,
            width=10,
            height=10,
            bg=self._colors["card_bg"],
            highlightthickness=0,
            bd=0,
        )
        self.console_state_dot.grid(row=0, column=0, padx=(0, 6))
        self.console_state_dot_item = self.console_state_dot.create_oval(
            1, 1, 9, 9, fill=self._colors["state_offline"], outline=""
        )
        ttk.Label(state_wrap, textvariable=self.console_state_var, style="ConsoleState.TLabel").grid(
            row=0, column=1, sticky="e"
        )
        ttk.Label(
            console_card,
            text="Live output stream and command input while the server is online.",
            style="CardSub.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(6, section_gap))

        self.log_area = ScrolledText(
            console_card,
            wrap=tk.WORD,
            height=16,
            bg=self._colors["console_bg"],
            fg=self._colors["text_primary"],
            insertbackground=self._colors["text_primary"],
            relief=tk.FLAT,
            padx=10,
            pady=10,
            borderwidth=0,
            font=(self._mono_font, 10),
        )
        self.log_area.grid(row=2, column=0, sticky="nsew")
        self.log_area.configure(state=tk.DISABLED)

        command_row = ttk.Frame(console_card, style="Card.TFrame")
        command_row.grid(row=3, column=0, sticky="ew", pady=(section_gap, 0))
        command_row.columnconfigure(0, weight=1)
        self.console_entry = ttk.Entry(
            command_row,
            textvariable=self.console_command_var,
            style="Input.TEntry",
        )
        self.console_entry.grid(row=0, column=0, sticky="ew", padx=(0, col_gap))
        self.send_command_btn = ttk.Button(
            command_row,
            text="Send",
            style="Primary.TButton",
            command=self._send_console_command,
        )
        self.send_command_btn.grid(row=0, column=1, sticky="ew")
        self._apply_command_placeholder()

    def _bind_events(self) -> None:
        self.loader_combo.bind("<<ComboboxSelected>>", self._on_loader_changed)
        self.mc_version_combo.bind("<<ComboboxSelected>>", self._on_minecraft_version_changed)
        self.console_entry.bind("<Return>", self._send_console_command)
        self.console_entry.bind("<FocusIn>", self._on_console_focus_in)
        self.console_entry.bind("<FocusOut>", self._on_console_focus_out)
        self.instance_dir_var.trace_add("write", self._on_instance_dir_changed)

    def _apply_command_placeholder(self) -> None:
        if self.console_command_var.get().strip():
            return
        self._command_placeholder_active = True
        self.console_command_var.set(self._command_placeholder)
        self.console_entry.configure(style="Placeholder.TEntry")

    def _on_console_focus_in(self, _event: object = None) -> None:
        if self._command_placeholder_active:
            self.console_command_var.set("")
            self._command_placeholder_active = False
            self.console_entry.configure(style="Input.TEntry")

    def _on_console_focus_out(self, _event: object = None) -> None:
        if not self.console_command_var.get().strip():
            self._apply_command_placeholder()

    def _on_instance_dir_changed(self, *_args: object) -> None:
        self._refresh_server_endpoint()

    def _open_discord(self) -> None:
        self._open_url(DISCORD_URL)

    def _open_website(self) -> None:
        self._open_url(WEBSITE_URL)

    def _open_url(self, url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme.lower() != "https" or host not in ALLOWED_EXTERNAL_HOSTS:
            self._set_status("Blocked unsafe external link.")
            return
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
        if self._controls_busy:
            self.loader_version_combo.configure(state="disabled")
            self.refresh_loader_versions_btn.configure(state="disabled")
            self.build_entry.configure(state="disabled")
            return

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
            self._refresh_server_endpoint()

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
        self._refresh_server_endpoint()
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
        self._controls_busy = not enabled
        entry_state = "normal" if enabled else "disabled"
        combo_state = "readonly" if enabled else "disabled"

        self.instance_dir_entry.configure(state=entry_state)
        self.java_path_entry.configure(state=entry_state)
        self.xms_entry.configure(state=entry_state)
        self.xmx_entry.configure(state=entry_state)
        self.build_entry.configure(state=entry_state)
        self.loader_combo.configure(state=combo_state)
        self.mc_version_combo.configure(state=combo_state)
        self.browse_folder_btn.configure(state=entry_state)
        self.refresh_versions_btn.configure(state=entry_state)
        self.accept_eula_checkbox.configure(state=entry_state)
        self.open_folder_btn.configure(state=entry_state)
        self.discord_btn.configure(state=entry_state)
        self.website_btn.configure(state=entry_state)

        self._sync_optional_fields()
        self._update_runtime_controls()
        self._update_console_controls()

    def _update_runtime_controls(self) -> None:
        process_running = bool(self._server_process and self._server_process.is_running())
        self.start_btn.configure(
            state="disabled" if self._controls_busy or process_running else "normal"
        )
        self.install_btn.configure(
            state="disabled" if self._controls_busy or process_running else "normal"
        )
        self.stop_btn.configure(
            state="normal" if process_running and not self._controls_busy else "disabled"
        )

    def _update_console_controls(self) -> None:
        process_running = bool(self._server_process and self._server_process.is_running())
        console_state = "normal" if process_running and not self._controls_busy else "disabled"
        self._update_console_state_indicator(process_running)
        self.console_entry.configure(state=console_state)
        self.send_command_btn.configure(state=console_state)
        if console_state == "normal":
            if self._command_placeholder_active:
                self.console_entry.configure(style="Placeholder.TEntry")
            else:
                self.console_entry.configure(style="Input.TEntry")
                if not self.console_command_var.get().strip():
                    self._apply_command_placeholder()
        else:
            self.console_entry.configure(style="Input.TEntry")

    def _update_console_state_indicator(self, running: bool) -> None:
        if not hasattr(self, "console_state_dot"):
            return
        color = self._colors["state_online"] if running else self._colors["state_offline"]
        text = "Online" if running else "Offline"
        self.console_state_dot.itemconfigure(self.console_state_dot_item, fill=color)
        self.console_state_var.set(text)

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
            self._refresh_server_endpoint()
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
            self._update_runtime_controls()
            self._update_console_controls()
        self.after(1000, self._poll_process_state)

    def _enqueue_log(self, line: str) -> None:
        self._ui_queue.put(("log", line))

    def _send_console_command(self, _event: object = None) -> None:
        command = self.console_command_var.get().strip()
        if not command or self._command_placeholder_active:
            return
        process = self._server_process
        if not process or not process.is_running():
            self._set_status("Cannot send command: server is not running.")
            self._update_console_controls()
            return
        process.send_command(command)
        self._append_log(f"> {command}")
        self.console_command_var.set("")
        self._command_placeholder_active = False
        self._apply_command_placeholder()

    def _append_log(self, line: str) -> None:
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.insert(tk.END, line.rstrip() + "\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state=tk.DISABLED)

    def _set_status(self, status: str) -> None:
        self.status_var.set(status)

    def _refresh_server_endpoint(self) -> None:
        instance_value = self.instance_dir_var.get().strip()
        if not instance_value:
            self.server_endpoint_var.set("Choose a folder")
            return

        instance_dir = Path(instance_value).resolve()
        properties_path = instance_dir / "server.properties"
        if not properties_path.exists():
            self.server_endpoint_var.set("Pending (server.properties not found)")
            return

        configured_host, port = read_server_endpoint(instance_dir)
        if configured_host:
            endpoint = self._format_host_port(configured_host, port)
            self.server_endpoint_var.set(endpoint)
            return

        detected_host = self._detect_lan_ip() or "0.0.0.0"
        endpoint = self._format_host_port(detected_host, port)
        self.server_endpoint_var.set(f"{endpoint} (server-ip empty; using LAN/default)")

    @staticmethod
    def _detect_lan_ip() -> str | None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.connect(("8.8.8.8", 80))
                candidate = probe.getsockname()[0].strip()
                if candidate and not candidate.startswith("127."):
                    return candidate
        except OSError:
            pass
        try:
            fallback = socket.gethostbyname(socket.gethostname()).strip()
            if fallback and not fallback.startswith("127."):
                return fallback
        except OSError:
            pass
        return None

    @staticmethod
    def _format_host_port(host: str, port: int) -> str:
        if ":" in host and not host.startswith("["):
            return f"[{host}]:{port}"
        return f"{host}:{port}"

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

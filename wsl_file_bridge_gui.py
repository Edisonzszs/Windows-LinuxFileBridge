import json
import os
import shutil
import subprocess
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from uuid import uuid4

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore
except Exception:
    DND_FILES = None
    TkinterDnD = None


FILE_TYPE_OPTIONS = {
    "全部文件": None,
    "文件夹": "folders_only",
    "常用文档": {".doc", ".docx", ".pdf", ".txt", ".md", ".rtf", ".xls", ".xlsx", ".ppt", ".pptx"},
    "图片": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"},
    "压缩包": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
    "代码文件": {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".cpp", ".h", ".hpp",
        ".go", ".rs", ".sh", ".ps1", ".json", ".yaml", ".yml", ".toml", ".xml", ".html", ".css",
    },
    "媒体文件": {".mp3", ".wav", ".mp4", ".mkv", ".avi", ".mov", ".flac"},
    "数据文件": {".csv", ".tsv", ".parquet", ".db", ".sqlite", ".sql"},
    "安装与镜像": {".exe", ".msi", ".apk", ".iso", ".img"},
}
SORT_OPTIONS = ["名称 A-Z", "名称 Z-A", "最新修改", "最早修改", "文件夹优先"]
SHORTCUT_SUFFIXES = {".lnk", ".url"}

COLORS = {
    "bg": "#F0FDFA",
    "bg_alt": "#ECFDF5",
    "surface": "#FFFFFF",
    "border": "#CDEFE9",
    "text": "#134E4A",
    "muted": "#52736F",
    "primary": "#0D9488",
    "primary_dark": "#0F766E",
    "accent": "#F97316",
    "accent_soft": "#FFF7ED",
    "success": "#16A34A",
    "warning": "#D97706",
    "danger": "#DC2626",
    "hero": "#115E59",
}


def linux_to_unc(linux_path: str, distro: str) -> str:
    normalized = linux_path.strip()
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    tail = normalized.strip("/").replace("/", "\\")
    if tail:
        return f"\\\\wsl$\\{distro}\\{tail}"
    return f"\\\\wsl$\\{distro}\\"


def unc_to_linux(path: str, distro: str) -> str:
    prefix = f"\\\\wsl$\\{distro}\\"
    if path.lower().startswith(prefix.lower()):
        rest = path[len(prefix):].replace("\\", "/").strip("/")
        return "/" + rest if rest else "/"
    return path


def safe_summary(paths):
    if not paths:
        return "-"
    if len(paths) == 1:
        return Path(paths[0]).name
    return f"{Path(paths[0]).name} +{len(paths) - 1} 项"


def format_bytes(size: int) -> str:
    value = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def icon_token(name: str, is_dir: bool) -> str:
    if is_dir:
        return "[DIR]"
    suffix = Path(name).suffix.lower()
    if suffix in {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"}:
        return "[ZIP]"
    if suffix in {".doc", ".docx", ".pdf", ".txt", ".md", ".rtf", ".xls", ".xlsx", ".ppt", ".pptx"}:
        return "[DOC]"
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}:
        return "[IMG]"
    if suffix in {".mp3", ".wav", ".mp4", ".mkv", ".avi", ".mov", ".flac"}:
        return "[MED]"
    if suffix in {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".cpp", ".h", ".hpp",
        ".go", ".rs", ".sh", ".ps1", ".json", ".yaml", ".yml", ".toml", ".xml", ".html", ".css",
    }:
        return "[DEV]"
    if suffix in {".exe", ".msi", ".apk", ".iso", ".img"}:
        return "[APP]"
    return "[FILE]"


def path_tail(path: str) -> str:
    raw = path.rstrip("\\/")
    if not raw:
        return path
    return Path(raw).name or raw

class FileBridgeApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Windows-Linux File Bridge")
        self.root.geometry("1440x900")
        self.root.minsize(1200, 760)

        self.history_path = Path(__file__).with_name("transfer_history.json")
        self.history = []
        self.windows_entries = []
        self.linux_entries = []
        self.windows_menu = None
        self.linux_menu = None
        self.history_window = None
        self.history_tree = None

        self.distro_var = tk.StringVar(value="Ubuntu-24.04")
        self.windows_dir_var = tk.StringVar(value=str(Path.home() / "Desktop"))
        self.linux_dir_var = tk.StringVar(value="/home/shengz")
        self.drag_direction = tk.StringVar(value="win_to_linux")
        self.windows_filter_var = tk.StringVar(value="全部文件")
        self.linux_filter_var = tk.StringVar(value="全部文件")
        self.windows_search_var = tk.StringVar()
        self.linux_search_var = tk.StringVar()
        self.windows_sort_var = tk.StringVar(value="名称 A-Z")
        self.linux_sort_var = tk.StringVar(value="名称 A-Z")
        self.status_var = tk.StringVar(value="准备就绪")
        self.windows_hint_var = tk.StringVar(value="等待载入目录")
        self.linux_hint_var = tk.StringVar(value="等待载入目录")
        self.selection_summary_var = tk.StringVar(value="当前未选择任何文件")
        self.drag_hint_var = tk.StringVar(value="把文件或文件夹拖到这里，目标目录由上方两侧面板决定。")
        self.metric_distro_var = tk.StringVar(value=self.distro_var.get())
        self.metric_windows_var = tk.StringVar(value="-")
        self.metric_linux_var = tk.StringVar(value="-")
        self.metric_last_var = tk.StringVar(value="尚未执行")

        self._configure_style()
        self._build_ui()
        self._load_history()
        self.refresh_panels()

    def _configure_style(self):
        self.root.configure(bg=COLORS["bg"])
        self.root.option_add("*Font", "{Segoe UI} 10")
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=COLORS["bg"], foreground=COLORS["text"])
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
        style.configure("TEntry", fieldbackground=COLORS["surface"], bordercolor=COLORS["border"], lightcolor=COLORS["border"], darkcolor=COLORS["border"], padding=6)
        style.configure("TCombobox", fieldbackground=COLORS["surface"], background=COLORS["surface"], foreground=COLORS["text"], bordercolor=COLORS["border"], lightcolor=COLORS["border"], darkcolor=COLORS["border"], padding=5)
        style.map("TCombobox", fieldbackground=[("readonly", COLORS["surface"])])
        style.configure("Treeview", background=COLORS["surface"], fieldbackground=COLORS["surface"], foreground=COLORS["text"], bordercolor=COLORS["border"], rowheight=30, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=COLORS["bg_alt"], foreground=COLORS["text"], bordercolor=COLORS["border"], relief="flat", font=("Segoe UI Semibold", 10), padding=(10, 8))
        style.map("Treeview", background=[("selected", "#CCFBF1")], foreground=[("selected", COLORS["hero"])])

        style.configure("Primary.TButton", background=COLORS["primary"], foreground="white", borderwidth=0, focusthickness=0, padding=(14, 10), font=("Segoe UI Semibold", 10))
        style.map("Primary.TButton", background=[("active", COLORS["primary_dark"])])
        style.configure("Accent.TButton", background=COLORS["accent"], foreground="white", borderwidth=0, focusthickness=0, padding=(14, 10), font=("Segoe UI Semibold", 10))
        style.map("Accent.TButton", background=[("active", "#EA580C")])
        style.configure("Soft.TButton", background=COLORS["surface"], foreground=COLORS["text"], bordercolor=COLORS["border"], lightcolor=COLORS["border"], darkcolor=COLORS["border"], padding=(10, 8))
        style.map("Soft.TButton", background=[("active", COLORS["bg_alt"])])

    def _create_scrollbar(self, parent, command):
        return tk.Scrollbar(
            parent,
            orient="vertical",
            command=command,
            width=14,
            bd=0,
            relief="flat",
            highlightthickness=0,
            bg="#D7F3EE",
            activebackground="#9EDFD4",
            troughcolor="#F5FBFA",
        )

    def _center_child_window(self, child: tk.Toplevel, width: int, height: int):
        self.root.update_idletasks()
        child.update_idletasks()
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        x = parent_x + max((parent_width - width) // 2, 0)
        y = parent_y + max((parent_height - height) // 2, 0)
        child.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self):
        shell = tk.Frame(self.root, bg=COLORS["bg"])
        shell.pack(fill=tk.BOTH, expand=True)
        self._build_hero(shell)
        self._build_dashboard(shell)

    def _build_hero(self, parent):
        hero = tk.Frame(parent, bg=COLORS["hero"], padx=24, pady=20)
        hero.pack(fill=tk.X, padx=20, pady=(20, 14))

        top = tk.Frame(hero, bg=COLORS["hero"])
        top.pack(fill=tk.X)
        left = tk.Frame(top, bg=COLORS["hero"])
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(left, text="Windows ↔ Linux 文件桥", bg=COLORS["hero"], fg="#F4FFFE", font=("Segoe UI Semibold", 24)).pack(anchor="w")
        tk.Label(left, text="双栏浏览、批量传输、目录管理和历史重试，一屏完成常用跨系统操作。", bg=COLORS["hero"], fg="#CFFAF4", font=("Segoe UI", 10)).pack(anchor="w", pady=(6, 0))

        right = tk.Frame(top, bg=COLORS["hero"])
        right.pack(side=tk.RIGHT, anchor="ne")
        control_row = tk.Frame(right, bg=COLORS["hero"])
        control_row.pack(anchor="e")
        tk.Label(control_row, text="WSL 发行版", bg=COLORS["hero"], fg="#F4FFFE", font=("Segoe UI", 10)).pack(side=tk.LEFT)
        ttk.Entry(control_row, textvariable=self.distro_var, width=18).pack(side=tk.LEFT, padx=(10, 10))
        ttk.Button(control_row, text="刷新全部面板", style="Soft.TButton", command=self.refresh_panels).pack(side=tk.LEFT)

        self.status_badge = tk.Label(right, textvariable=self.status_var, bg="#0F766E", fg="white", padx=12, pady=7, font=("Segoe UI Semibold", 9))
        self.status_badge.pack(anchor="e", pady=(12, 0))

        stats = tk.Frame(hero, bg=COLORS["hero"])
        stats.pack(fill=tk.X, pady=(18, 0))
        self._build_metric_card(stats, "当前发行版", self.metric_distro_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self._build_metric_card(stats, "Windows 面板", self.metric_windows_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self._build_metric_card(stats, "Linux 面板", self.metric_linux_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self._build_metric_card(stats, "最近结果", self.metric_last_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

    def _build_metric_card(self, parent, label_text: str, variable: tk.StringVar):
        card = tk.Frame(parent, bg="#F8FFFE", highlightbackground="#2BB6A9", highlightthickness=1, padx=14, pady=12)
        tk.Label(card, text=label_text, bg="#F8FFFE", fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(card, textvariable=variable, bg="#F8FFFE", fg=COLORS["text"], font=("Consolas", 13, "bold")).pack(anchor="w", pady=(8, 0))
        return card

    def _build_dashboard(self, parent):
        body = tk.Frame(parent, bg=COLORS["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        upper = tk.Frame(body, bg=COLORS["bg"])
        upper.pack(fill=tk.BOTH, expand=True)
        left_panel = self._create_card(upper)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        action_panel = self._create_card(upper, width=250)
        action_panel.pack(side=tk.LEFT, fill=tk.Y, padx=4)
        action_panel.pack_propagate(False)
        right_panel = self._create_card(upper)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))

        self._build_side_panel(left_panel, is_windows=True)
        self._build_action_panel(action_panel)
        self._build_side_panel(right_panel, is_windows=False)

        lower = tk.Frame(body, bg=COLORS["bg"])
        lower.pack(fill=tk.BOTH, expand=False, pady=(14, 0))
        drag_card = self._create_card(lower)
        drag_card.pack(fill=tk.BOTH, expand=True)
        self._build_drag_panel(drag_card)

    def _create_card(self, parent, width=None):
        return tk.Frame(parent, bg=COLORS["surface"], highlightbackground=COLORS["border"], highlightthickness=1, bd=0, padx=14, pady=14, width=width)

    def _build_side_panel(self, card, is_windows: bool):
        title = "Windows 工作区" if is_windows else "Linux 工作区"
        subtitle = "本机目录直接访问" if is_windows else "通过 WSL 共享路径访问"
        tk.Label(card, text=title, bg=COLORS["surface"], fg=COLORS["text"], font=("Segoe UI Semibold", 14)).pack(anchor="w")
        tk.Label(card, text=subtitle, bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 12))

        path_var = self.windows_dir_var if is_windows else self.linux_dir_var
        path_row = tk.Frame(card, bg=COLORS["surface"])
        path_row.pack(fill=tk.X)
        ttk.Entry(path_row, textvariable=path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        if is_windows:
            ttk.Button(path_row, text="选择目录", style="Soft.TButton", command=self.pick_windows_dir).pack(side=tk.LEFT, padx=(8, 6))
            ttk.Button(path_row, text="上级", style="Soft.TButton", command=self.win_up).pack(side=tk.LEFT)
        else:
            ttk.Button(path_row, text="选择目录", style="Soft.TButton", command=self.pick_linux_dir).pack(side=tk.LEFT, padx=(8, 6))
            ttk.Button(path_row, text="上级", style="Soft.TButton", command=self.linux_up).pack(side=tk.LEFT)

        tools = tk.Frame(card, bg=COLORS["surface"])
        tools.pack(fill=tk.X, pady=(12, 0))
        filter_var = self.windows_filter_var if is_windows else self.linux_filter_var
        sort_var = self.windows_sort_var if is_windows else self.linux_sort_var
        search_var = self.windows_search_var if is_windows else self.linux_search_var
        ttk.Label(tools, text="类型").pack(side=tk.LEFT)
        filter_box = ttk.Combobox(tools, textvariable=filter_var, values=list(FILE_TYPE_OPTIONS.keys()), state="readonly", width=12)
        filter_box.pack(side=tk.LEFT, padx=(6, 12))
        filter_box.bind("<<ComboboxSelected>>", lambda _event: self.refresh_panels())
        ttk.Label(tools, text="排序").pack(side=tk.LEFT)
        sort_box = ttk.Combobox(tools, textvariable=sort_var, values=SORT_OPTIONS, state="readonly", width=12)
        sort_box.pack(side=tk.LEFT, padx=(6, 0))
        sort_box.bind("<<ComboboxSelected>>", lambda _event: self.refresh_panels())

        quick_actions = tk.Frame(card, bg=COLORS["surface"])
        quick_actions.pack(fill=tk.X, pady=(12, 0))
        ttk.Label(quick_actions, text="搜索").pack(side=tk.LEFT)
        search_entry = ttk.Entry(quick_actions, textvariable=search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 12))
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_panels())
        ttk.Button(quick_actions, text="新建文件夹", style="Soft.TButton", command=self.create_windows_folder if is_windows else self.create_linux_folder).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(quick_actions, text="删除所选", style="Soft.TButton", command=self.delete_windows_selected if is_windows else self.delete_linux_selected).pack(side=tk.RIGHT)

        table_wrap = tk.Frame(card, bg=COLORS["surface"])
        table_wrap.pack(fill=tk.BOTH, expand=True, pady=(14, 0))
        tree = ttk.Treeview(table_wrap, columns=("type", "modified", "size"), show="tree headings", selectmode="extended")
        tree.heading("#0", text="名称")
        tree.heading("type", text="类型")
        tree.heading("modified", text="修改时间")
        tree.heading("size", text="大小")
        tree.column("#0", width=320, minwidth=240, anchor="w")
        tree.column("type", width=120, minwidth=100, anchor="center")
        tree.column("modified", width=160, minwidth=150, anchor="center")
        tree.column("size", width=100, minwidth=90, anchor="e")
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree.bind("<Double-1>", lambda _event, side=is_windows: self.open_selected_dir(side))
        tree.bind("<Button-3>", lambda event, side=is_windows: self.show_context_menu(event, side))
        tree.bind("<<TreeviewSelect>>", lambda _event: self._update_selection_summary())
        scrollbar = self._create_scrollbar(table_wrap, tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))
        tree.configure(yscrollcommand=scrollbar.set)

        hint_var = self.windows_hint_var if is_windows else self.linux_hint_var
        tk.Label(card, textvariable=hint_var, bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 0))
        if is_windows:
            self.windows_tree = tree
        else:
            self.linux_tree = tree
        self._build_context_menu(is_windows)

    def _build_action_panel(self, card):
        tk.Label(card, text="传输中心", bg=COLORS["surface"], fg=COLORS["text"], font=("Segoe UI Semibold", 14)).pack(anchor="w")
        tk.Label(card, text="把左右两侧当成源和目标，主按钮只负责传输，不混合管理动作。", bg=COLORS["surface"], fg=COLORS["muted"], justify="left", wraplength=210, font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 14))

        flow = tk.Frame(card, bg=COLORS["bg_alt"], highlightbackground=COLORS["border"], highlightthickness=1, padx=12, pady=12)
        flow.pack(fill=tk.X, pady=(0, 14))
        tk.Label(flow, text="Windows  →  Linux", bg=COLORS["bg_alt"], fg=COLORS["text"], font=("Consolas", 11, "bold")).pack(anchor="w")
        ttk.Button(flow, text="发送到 Linux", style="Accent.TButton", command=self.copy_windows_to_linux).pack(fill=tk.X, pady=(10, 0))

        flow_back = tk.Frame(card, bg=COLORS["bg_alt"], highlightbackground=COLORS["border"], highlightthickness=1, padx=12, pady=12)
        flow_back.pack(fill=tk.X)
        tk.Label(flow_back, text="Linux  →  Windows", bg=COLORS["bg_alt"], fg=COLORS["text"], font=("Consolas", 11, "bold")).pack(anchor="w")
        ttk.Button(flow_back, text="发送到 Windows", style="Primary.TButton", command=self.copy_linux_to_windows).pack(fill=tk.X, pady=(10, 0))

        summary = tk.Frame(card, bg=COLORS["surface"], pady=10)
        summary.pack(fill=tk.X, pady=(14, 0))
        tk.Label(summary, text="当前选择", bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(summary, textvariable=self.selection_summary_var, bg=COLORS["surface"], fg=COLORS["text"], justify="left", wraplength=210, font=("Segoe UI Semibold", 10)).pack(anchor="w", pady=(6, 0))

        history_actions = tk.Frame(card, bg=COLORS["surface"])
        history_actions.pack(fill=tk.X, pady=(18, 0))
        ttk.Button(history_actions, text="查看操作记录", style="Soft.TButton", command=self.open_history_window).pack(fill=tk.X)

    def _build_history_panel(self, card):
        head = tk.Frame(card, bg=COLORS["surface"])
        head.pack(fill=tk.X)
        tk.Label(head, text="任务与历史", bg=COLORS["surface"], fg=COLORS["text"], font=("Segoe UI Semibold", 14)).pack(side=tk.LEFT)
        tk.Label(head, text="失败记录可直接重试", bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(12, 0))

        table_wrap = tk.Frame(card, bg=COLORS["surface"])
        table_wrap.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        cols = ("time", "direction", "status", "summary")
        self.history_tree = ttk.Treeview(table_wrap, columns=cols, show="headings", height=8)
        self.history_tree.heading("time", text="时间")
        self.history_tree.heading("direction", text="方向")
        self.history_tree.heading("status", text="状态")
        self.history_tree.heading("summary", text="内容")
        self.history_tree.column("time", width=170, anchor="center")
        self.history_tree.column("direction", width=120, anchor="center")
        self.history_tree.column("status", width=90, anchor="center")
        self.history_tree.column("summary", width=720, anchor="w")
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = self._create_scrollbar(table_wrap, self.history_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        actions = tk.Frame(card, bg=COLORS["surface"])
        actions.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(actions, text="重试所选", style="Primary.TButton", command=self.retry_selected).pack(side=tk.LEFT)
        ttk.Button(actions, text="刷新历史", style="Soft.TButton", command=self.render_history).pack(side=tk.LEFT, padx=(8, 8))
        ttk.Button(actions, text="清空历史", style="Soft.TButton", command=self.clear_history).pack(side=tk.LEFT)

    def open_history_window(self):
        if self.history_window is not None and self.history_window.winfo_exists():
            self.history_window.deiconify()
            self._center_child_window(self.history_window, self.history_window.winfo_width(), self.history_window.winfo_height())
            self.history_window.lift()
            self.history_window.focus_force()
            self.render_history()
            return

        self.history_window = tk.Toplevel(self.root)
        self.history_window.title("操作记录")
        self.history_window.minsize(900, 420)
        self.history_window.configure(bg=COLORS["bg"])
        self.history_window.transient(self.root)
        self.history_window.protocol("WM_DELETE_WINDOW", self.close_history_window)
        self._center_child_window(self.history_window, 1080, 520)

        container = self._create_card(self.history_window)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        self._build_history_panel(container)
        self.render_history()

    def close_history_window(self):
        if self.history_window is not None and self.history_window.winfo_exists():
            self.history_window.destroy()
        self.history_window = None
        self.history_tree = None

    def _build_drag_panel(self, card):
        tk.Label(card, text="拖拽投递", bg=COLORS["surface"], fg=COLORS["text"], font=("Segoe UI Semibold", 14)).pack(anchor="w")
        tk.Label(card, text="当你从资源管理器里直接拖文件时，这里就是快捷投递区。", bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 12))

        mode_box = tk.Frame(card, bg=COLORS["surface"])
        mode_box.pack(fill=tk.X)
        ttk.Radiobutton(mode_box, text="拖到 Linux", variable=self.drag_direction, value="win_to_linux").pack(side=tk.LEFT)
        ttk.Radiobutton(mode_box, text="拖到 Windows", variable=self.drag_direction, value="linux_to_win").pack(side=tk.LEFT, padx=(14, 0))

        drop_zone = tk.Frame(card, bg=COLORS["bg_alt"], highlightbackground=COLORS["border"], highlightthickness=1, padx=16, pady=16)
        drop_zone.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        tk.Label(drop_zone, text="DROP AREA", bg=COLORS["bg_alt"], fg=COLORS["primary"], font=("Consolas", 16, "bold")).pack(anchor="center", pady=(20, 8))
        self.drop_label = tk.Label(drop_zone, textvariable=self.drag_hint_var, bg=COLORS["bg_alt"], fg=COLORS["text"], justify="center", wraplength=250, font=("Segoe UI", 10))
        self.drop_label.pack(fill=tk.BOTH, expand=True)
        if TkinterDnD is not None and DND_FILES is not None:
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind("<<Drop>>", self.handle_drop)
        else:
            self.drag_hint_var.set("当前未启用系统拖拽。安装 tkinterdnd2 后，这里可直接接收文件或文件夹。")

    def _build_context_menu(self, is_windows: bool):
        menu = tk.Menu(self.root, tearoff=0, bg=COLORS["surface"], fg=COLORS["text"], activebackground=COLORS["bg_alt"])
        menu.add_command(label="重命名", command=self.rename_windows_selected if is_windows else self.rename_linux_selected)
        menu.add_command(label="打开所在位置", command=self.open_windows_location if is_windows else self.open_linux_location)
        menu.add_command(label="查看属性", command=self.show_windows_properties if is_windows else self.show_linux_properties)
        menu.add_command(label="新建文件夹", command=self.create_windows_folder if is_windows else self.create_linux_folder)
        menu.add_separator()
        menu.add_command(label="删除所选", command=self.delete_windows_selected if is_windows else self.delete_linux_selected)
        if is_windows:
            self.windows_menu = menu
        else:
            self.linux_menu = menu

    def _load_history(self):
        if self.history_path.exists():
            try:
                self.history = json.loads(self.history_path.read_text(encoding="utf-8"))
            except Exception:
                self.history = []
        self.render_history()

    def _save_history(self):
        self.history_path.write_text(json.dumps(self.history, ensure_ascii=False, indent=2), encoding="utf-8")

    def render_history(self):
        if self.history_tree is not None and self.history_tree.winfo_exists():
            for row in self.history_tree.get_children():
                self.history_tree.delete(row)
            for rec in reversed(self.history[-200:]):
                self.history_tree.insert("", tk.END, iid=rec["id"], values=(rec.get("time", ""), rec.get("direction", ""), rec.get("status", ""), rec.get("summary", "")))
        self._update_metrics()

    def set_status(self, text: str, level: str = "neutral"):
        self.status_var.set(text)
        palette = {
            "neutral": ("#0F766E", "white"),
            "success": (COLORS["success"], "white"),
            "warning": (COLORS["warning"], "white"),
            "danger": (COLORS["danger"], "white"),
        }
        bg, fg = palette.get(level, palette["neutral"])
        self.status_badge.configure(bg=bg, fg=fg)
        self._update_metrics()

    def _update_metrics(self):
        self.metric_distro_var.set(self.distro_var.get().strip() or "-")
        self.metric_windows_var.set(f"{len(self.windows_entries)} 项 · {path_tail(self.windows_dir_var.get())}")
        self.metric_linux_var.set(f"{len(self.linux_entries)} 项 · {path_tail(self.linux_dir_var.get())}")
        if self.history:
            last = self.history[-1]
            self.metric_last_var.set(f"{last.get('status', '-')} · {last.get('direction', '-')}")
        else:
            self.metric_last_var.set("尚未执行")

    def clear_history(self):
        if not messagebox.askyesno("确认", "确定清空历史记录吗？"):
            return
        self.history = []
        self._save_history()
        self.render_history()
        self.set_status("历史记录已清空", "warning")

    def pick_windows_dir(self):
        selected = filedialog.askdirectory(initialdir=self.windows_dir_var.get() or str(Path.home()))
        if selected:
            self.windows_dir_var.set(selected)
            self.refresh_windows()

    def pick_linux_dir(self):
        base = self.linux_dir_var.get().strip() or "/home/shengz"
        unc_base = linux_to_unc(base, self.distro_var.get().strip())
        selected = filedialog.askdirectory(initialdir=unc_base)
        if selected:
            self.linux_dir_var.set(unc_to_linux(selected, self.distro_var.get().strip()))
            self.refresh_linux()

    def win_up(self):
        current = Path(self.windows_dir_var.get())
        if current.parent != current:
            self.windows_dir_var.set(str(current.parent))
            self.refresh_windows()

    def linux_up(self):
        current = self.linux_dir_var.get().rstrip("/") or "/"
        parent = "/" if current == "/" else str(Path(current).parent).replace("\\", "/")
        self.linux_dir_var.set(parent)
        self.refresh_linux()

    def refresh_panels(self):
        self.refresh_windows()
        self.refresh_linux()
        self.set_status("面板已刷新")

    def refresh_windows(self):
        self.windows_entries = self.read_dir_entries(self.windows_dir_var.get(), False, self.windows_filter_var.get(), self.windows_search_var.get(), self.windows_sort_var.get())
        self.render_entries(self.windows_tree, self.windows_entries)
        self.windows_hint_var.set(self._panel_hint("Windows", self.windows_entries, self.windows_filter_var.get()))
        self._update_selection_summary()
        self._update_metrics()

    def refresh_linux(self):
        linux_real = linux_to_unc(self.linux_dir_var.get(), self.distro_var.get().strip())
        self.linux_entries = self.read_dir_entries(linux_real, True, self.linux_filter_var.get(), self.linux_search_var.get(), self.linux_sort_var.get())
        self.render_entries(self.linux_tree, self.linux_entries)
        self.linux_hint_var.set(self._panel_hint("Linux", self.linux_entries, self.linux_filter_var.get()))
        self._update_selection_summary()
        self._update_metrics()

    def _panel_hint(self, side_name: str, entries, filter_name: str) -> str:
        if entries:
            folders = sum(1 for item in entries if item["is_dir"])
            files = len(entries) - folders
            return f"{side_name} 面板已载入 {len(entries)} 项，其中 {folders} 个文件夹、{files} 个文件。"
        if filter_name == "全部文件":
            return f"{side_name} 面板当前目录为空，或内容被默认规则过滤。"
        return f"{side_name} 面板当前没有匹配“{filter_name}”的结果。"

    def read_dir_entries(self, path: str, is_linux_view: bool, filter_name: str, search_text: str, sort_mode: str):
        entries = []
        base = Path(path)
        allowed = FILE_TYPE_OPTIONS.get(filter_name)
        keyword = search_text.strip().lower()
        try:
            for child in base.iterdir():
                if child.name.startswith("~$"):
                    continue
                if child.name.lower() == "desktop.ini":
                    continue
                if not child.is_dir() and child.suffix.lower() in SHORTCUT_SUFFIXES:
                    continue
                if allowed == "folders_only":
                    if not child.is_dir():
                        continue
                elif allowed is None:
                    pass
                else:
                    if child.is_dir() or child.suffix.lower() not in allowed:
                        continue
                if keyword and keyword not in child.name.lower():
                    continue
                try:
                    stat = child.stat()
                    mtime = stat.st_mtime
                    size = stat.st_size if child.is_file() else None
                except Exception:
                    mtime = 0
                    size = None
                entries.append({
                    "id": str(uuid4()),
                    "name": child.name,
                    "is_dir": child.is_dir(),
                    "full_path": str(child),
                    "is_linux_view": is_linux_view,
                    "mtime": mtime,
                    "size": size,
                    "type_label": self._type_label(child),
                    "modified_label": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M") if mtime else "-",
                    "size_label": "-" if size is None else format_bytes(size),
                })
        except Exception:
            pass
        return self.sort_entries(entries, sort_mode)

    def _type_label(self, path_obj: Path) -> str:
        if path_obj.is_dir():
            return "文件夹"
        suffix = path_obj.suffix.lower()
        if suffix in {".doc", ".docx", ".pdf", ".txt", ".md", ".rtf", ".xls", ".xlsx", ".ppt", ".pptx"}:
            return "文档"
        if suffix in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}:
            return "图片"
        if suffix in {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"}:
            return "压缩包"
        if suffix in {".mp3", ".wav", ".mp4", ".mkv", ".avi", ".mov", ".flac"}:
            return "媒体"
        if suffix in {".csv", ".tsv", ".parquet", ".db", ".sqlite", ".sql"}:
            return "数据"
        if suffix in {".exe", ".msi", ".apk", ".iso", ".img"}:
            return "安装/镜像"
        return suffix.replace(".", "").upper() if suffix else "文件"

    @staticmethod
    def sort_entries(entries, sort_mode: str):
        if sort_mode == "名称 Z-A":
            return sorted(entries, key=lambda item: item["name"].lower(), reverse=True)
        if sort_mode == "最新修改":
            return sorted(entries, key=lambda item: item["mtime"], reverse=True)
        if sort_mode == "最早修改":
            return sorted(entries, key=lambda item: item["mtime"])
        if sort_mode == "文件夹优先":
            return sorted(entries, key=lambda item: (not item["is_dir"], item["name"].lower()))
        return sorted(entries, key=lambda item: item["name"].lower())

    def render_entries(self, tree: ttk.Treeview, entries):
        for row in tree.get_children():
            tree.delete(row)
        for item in entries:
            tree.insert("", tk.END, iid=item["id"], text=f"{icon_token(item['name'], item['is_dir'])} {item['name']}", values=(item["type_label"], item["modified_label"], item["size_label"]))

    def _entry_by_id(self, is_windows: bool, item_id: str):
        entries = self.windows_entries if is_windows else self.linux_entries
        return next((entry for entry in entries if entry["id"] == item_id), None)

    def show_context_menu(self, event, is_windows: bool):
        tree = self.windows_tree if is_windows else self.linux_tree
        row_id = tree.identify_row(event.y)
        if row_id:
            tree.selection_set(row_id)
            tree.focus(row_id)
        else:
            current_selection = tree.selection()
            if current_selection:
                tree.selection_remove(*current_selection)
            tree.focus("")
        menu = self.windows_menu if is_windows else self.linux_menu
        if menu is None:
            return
        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()
        self._update_selection_summary()

    def get_selected_entries(self, is_windows: bool):
        tree = self.windows_tree if is_windows else self.linux_tree
        selected = []
        for item_id in tree.selection():
            entry = self._entry_by_id(is_windows, item_id)
            if entry is not None:
                selected.append(entry)
        return selected

    def get_single_selected_entry(self, is_windows: bool, action_name: str):
        selected = self.get_selected_entries(is_windows)
        side_name = "Windows" if is_windows else "Linux"
        if not selected:
            messagebox.showinfo("提示", f"请先在 {side_name} 面板选择项目。")
            return None
        if len(selected) != 1:
            messagebox.showinfo("提示", f"{action_name} 需要只选择 1 个项目。")
            return None
        return selected[0]

    def _update_selection_summary(self):
        win_selected = self.get_selected_entries(True)
        linux_selected = self.get_selected_entries(False)
        if win_selected:
            self.selection_summary_var.set(f"Windows 已选 {len(win_selected)} 项\n目标：{path_tail(self.linux_dir_var.get())}")
            return
        if linux_selected:
            self.selection_summary_var.set(f"Linux 已选 {len(linux_selected)} 项\n目标：{path_tail(self.windows_dir_var.get())}")
            return
        self.selection_summary_var.set("当前未选择任何文件")

    def open_selected_dir(self, is_windows: bool):
        selected = self.get_selected_entries(is_windows)
        if not selected:
            return
        item = selected[0]
        if not item["is_dir"]:
            return
        if is_windows:
            self.windows_dir_var.set(item["full_path"])
        else:
            self.linux_dir_var.set(unc_to_linux(item["full_path"], self.distro_var.get().strip()))
        self.refresh_panels()

    def copy_windows_to_linux(self):
        selected = self.get_selected_entries(True)
        if not selected:
            messagebox.showinfo("提示", "请先在 Windows 面板选择文件或文件夹。")
            return
        self.transfer([item["full_path"] for item in selected], linux_to_unc(self.linux_dir_var.get(), self.distro_var.get().strip()), "win_to_linux")

    def copy_linux_to_windows(self):
        selected = self.get_selected_entries(False)
        if not selected:
            messagebox.showinfo("提示", "请先在 Linux 面板选择文件或文件夹。")
            return
        self.transfer([item["full_path"] for item in selected], self.windows_dir_var.get(), "linux_to_win")

    def handle_drop(self, event):
        try:
            dropped = list(self.root.tk.splitlist(event.data))
        except Exception:
            dropped = [event.data]
        dropped = [path for path in dropped if path.strip()]
        if not dropped:
            return
        if self.drag_direction.get() == "win_to_linux":
            self.transfer(dropped, linux_to_unc(self.linux_dir_var.get(), self.distro_var.get().strip()), "win_to_linux")
        else:
            self.transfer(dropped, self.windows_dir_var.get(), "linux_to_win")

    @staticmethod
    def unique_target(path_obj: Path) -> Path:
        if not path_obj.exists():
            return path_obj
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        stem = path_obj.stem
        suffix = path_obj.suffix
        candidate = path_obj.parent / f"{stem} (copy {timestamp}){suffix}"
        index = 1
        while candidate.exists():
            candidate = path_obj.parent / f"{stem} (copy {timestamp}-{index}){suffix}"
            index += 1
        return candidate

    def transfer(self, sources, dst_root, direction):
        dst_path = Path(dst_root)
        if not dst_path.exists():
            messagebox.showerror("错误", f"目标目录不存在：{dst_root}")
            return

        copied = []
        errors = []
        skipped = []
        for src in sources:
            src_path = Path(src)
            if not src_path.exists():
                errors.append(f"源不存在：{src}")
                continue
            if not src_path.is_dir() and src_path.suffix.lower() in SHORTCUT_SUFFIXES:
                skipped.append(src_path.name)
                continue
            target = self.unique_target(dst_path / src_path.name)
            try:
                if src_path.is_dir():
                    shutil.copytree(src_path, target)
                else:
                    shutil.copy2(src_path, target)
                copied.append({"source": str(src_path), "target": str(target)})
            except Exception as exc:
                errors.append(f"{src_path.name}: {exc}")

        status = "success" if not errors else "failed"
        summary = safe_summary([item["source"] for item in copied]) if copied else safe_summary(sources)
        if skipped:
            summary = f"{summary}，已跳过快捷方式 {len(skipped)} 项"
        self._append_history(direction, status, summary if not errors else f"{summary}（部分失败）", list(sources), str(dst_path), copied, errors)
        self.refresh_panels()

        if errors:
            lines = []
            if skipped:
                lines.append("已跳过快捷方式：" + ", ".join(skipped[:8]))
            lines.extend(errors[:8])
            self.set_status("传输部分失败", "danger")
            messagebox.showwarning("完成（部分失败）", "\n".join(lines))
        else:
            self.set_status(f"已成功复制 {len(copied)} 项", "success")
            message = f"已成功复制 {len(copied)} 项。"
            if skipped:
                message += "\n\n已自动跳过快捷方式文件。"
            messagebox.showinfo("完成", message)

    def _append_history(self, direction: str, status: str, summary: str, sources=None, dst_root="", copied=None, errors=None):
        self.history.append({
            "id": str(uuid4()),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "direction": direction,
            "status": status,
            "summary": summary,
            "sources": sources or [],
            "dst_root": dst_root,
            "copied": copied or [],
            "errors": errors or [],
        })
        self._save_history()
        self.render_history()

    def delete_windows_selected(self):
        self.delete_selected(True)

    def delete_linux_selected(self):
        self.delete_selected(False)

    def delete_selected(self, is_windows: bool):
        selected = self.get_selected_entries(is_windows)
        side_name = "Windows" if is_windows else "Linux"
        if not selected:
            messagebox.showinfo("提示", f"请先在 {side_name} 面板选择文件或文件夹。")
            return

        summary = safe_summary([item["name"] for item in selected])
        if not messagebox.askyesno("删除确认", f"确定删除 {side_name} 面板中选中的 {len(selected)} 项吗？\n\n{summary}\n\n此操作不可撤销。"):
            return

        deleted = []
        errors = []
        for item in selected:
            target = Path(item["full_path"])
            try:
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
                deleted.append(item["full_path"])
            except Exception as exc:
                errors.append(f"{item['name']}: {exc}")

        self._append_history(f"delete_{side_name.lower()}", "success" if not errors else "failed", safe_summary(deleted) if deleted else summary, deleted, errors=errors)
        self.refresh_windows() if is_windows else self.refresh_linux()
        if errors:
            self.set_status("删除部分失败", "danger")
            messagebox.showwarning("删除完成（部分失败）", "\n".join(errors[:8]))
        else:
            self.set_status(f"已删除 {len(deleted)} 项", "warning")
            messagebox.showinfo("删除完成", f"已删除 {len(deleted)} 项。")

    def create_windows_folder(self):
        self.create_folder(True)

    def create_linux_folder(self):
        self.create_folder(False)

    def create_folder(self, is_windows: bool):
        parent_dir = self.windows_dir_var.get() if is_windows else linux_to_unc(self.linux_dir_var.get(), self.distro_var.get().strip())
        folder_name = simpledialog.askstring("新建文件夹", "请输入文件夹名称：", parent=self.root)
        if not folder_name:
            return
        folder_name = folder_name.strip()
        if not folder_name or folder_name in {".", ".."}:
            messagebox.showerror("错误", "文件夹名称无效。")
            return

        new_dir = Path(parent_dir) / folder_name
        if new_dir.exists():
            messagebox.showerror("错误", "同名文件夹已存在。")
            return
        try:
            new_dir.mkdir(parents=False, exist_ok=False)
        except Exception as exc:
            messagebox.showerror("错误", f"创建文件夹失败：{exc}")
            return

        self._append_history(f"mkdir_{'windows' if is_windows else 'linux'}", "success", f"新建文件夹 {folder_name}", dst_root=str(new_dir.parent), copied=[{"source": "", "target": str(new_dir)}])
        self.refresh_panels()
        self.set_status(f"已新建文件夹 {folder_name}", "success")

    def rename_windows_selected(self):
        self.rename_selected(True)

    def rename_linux_selected(self):
        self.rename_selected(False)

    def rename_selected(self, is_windows: bool):
        item = self.get_single_selected_entry(is_windows, "重命名")
        if item is None:
            return
        old_path = Path(item["full_path"])
        new_name = simpledialog.askstring("重命名", "请输入新名称：", initialvalue=item["name"], parent=self.root)
        if not new_name:
            return
        new_name = new_name.strip()
        if not new_name or new_name in {".", ".."}:
            messagebox.showerror("错误", "文件名无效。")
            return

        new_path = old_path.with_name(new_name)
        if new_path.exists():
            messagebox.showerror("错误", "目标名称已存在。")
            return
        try:
            old_path.rename(new_path)
        except Exception as exc:
            messagebox.showerror("错误", f"重命名失败：{exc}")
            return

        self._append_history(f"rename_{'windows' if is_windows else 'linux'}", "success", f"{old_path.name} -> {new_path.name}", [str(old_path)], str(new_path.parent), [{"source": str(old_path), "target": str(new_path)}], [])
        self.refresh_panels()
        self.set_status(f"已重命名为 {new_path.name}", "success")

    def open_windows_location(self):
        self.open_selected_location(True)

    def open_linux_location(self):
        self.open_selected_location(False)

    def open_selected_location(self, is_windows: bool):
        item = self.get_single_selected_entry(is_windows, "打开所在位置")
        if item is None:
            return
        target = Path(item["full_path"])
        try:
            if target.exists() and target.is_file():
                subprocess.Popen(["explorer", "/select,", str(target)])
            else:
                os.startfile(str(target))
        except Exception:
            try:
                os.startfile(str(target.parent if target.is_file() else target))
            except Exception as exc:
                messagebox.showerror("错误", f"打开位置失败：{exc}")

    def show_windows_properties(self):
        self.show_selected_properties(True)

    def show_linux_properties(self):
        self.show_selected_properties(False)

    def show_selected_properties(self, is_windows: bool):
        item = self.get_single_selected_entry(is_windows, "查看属性")
        if item is None:
            return
        target = Path(item["full_path"])
        try:
            stat = target.stat()
        except Exception as exc:
            messagebox.showerror("错误", f"读取属性失败：{exc}")
            return

        lines = [
            f"名称：{target.name}",
            f"类型：{'文件夹' if target.is_dir() else '文件'}",
            f"大小：{'-' if target.is_dir() else format_bytes(stat.st_size)}",
            f"修改时间：{datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}",
            f"路径：{target}",
        ]
        if not is_windows:
            lines.append(f"Linux 路径：{unc_to_linux(str(target), self.distro_var.get().strip())}")
        messagebox.showinfo("属性", "\n\n".join(lines))

    def retry_selected(self):
        if self.history_tree is None or not self.history_tree.winfo_exists():
            self.open_history_window()
            return
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择一条历史记录。")
            return
        record = next((item for item in self.history if item["id"] == selected[0]), None)
        if not record:
            return
        sources = record.get("sources", [])
        dst_root = record.get("dst_root", "")
        if not sources or not dst_root:
            messagebox.showerror("错误", "该记录缺少重试信息。")
            return
        self.transfer(sources, dst_root, record.get("direction", "retry"))


def main():
    root = TkinterDnD.Tk() if TkinterDnD is not None else tk.Tk()
    FileBridgeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

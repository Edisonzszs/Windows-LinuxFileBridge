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
    return f"{Path(paths[0]).name} +{len(paths) - 1} items"


def format_bytes(size: int) -> str:
    value = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def get_entry_icon(name: str, is_dir: bool) -> str:
    if is_dir:
        return "📁"

    suffix = Path(name).suffix.lower()
    if suffix in {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"}:
        return "🗜"
    if suffix in {".doc", ".docx", ".pdf", ".txt", ".md", ".rtf", ".xls", ".xlsx", ".ppt", ".pptx"}:
        return "📄"
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}:
        return "🖼"
    if suffix in {".mp3", ".wav", ".mp4", ".mkv", ".avi", ".mov", ".flac"}:
        return "🎞"
    if suffix in {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".cpp", ".h", ".hpp", ".go", ".rs", ".sh", ".ps1", ".json", ".yaml", ".yml", ".toml", ".xml", ".html", ".css"}:
        return "⌘"
    if suffix in {".exe", ".msi", ".apk", ".iso", ".img"}:
        return "⚙"
    if suffix in {".lnk", ".url"}:
        return "↗"
    return "•"


class FileBridgeApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Windows-Linux 文件桥")
        self.root.geometry("1280x800")

        self.history_path = Path(__file__).with_name("transfer_history.json")
        self.history = []

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

        self.windows_entries = []
        self.linux_entries = []
        self.windows_menu = None
        self.linux_menu = None

        self._build_ui()
        self._load_history()
        self.refresh_panels()

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="WSL 发行版").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.distro_var, width=20).grid(row=0, column=1, padx=6)
        ttk.Button(top, text="刷新面板", command=self.refresh_panels).grid(row=0, column=2, padx=6)
        ttk.Label(top, text="同步模式：手动传输").grid(row=0, column=3, sticky="w", padx=8)

        status_bar = ttk.Frame(self.root, padding=(10, 0, 10, 8))
        status_bar.pack(fill=tk.X)
        ttk.Label(status_bar, textvariable=self.status_var).pack(side=tk.LEFT)

        main = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(main, text="Windows 目录", padding=8)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        right = ttk.LabelFrame(main, text="Linux 目录", padding=8)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        self._build_side(left, True, self.windows_dir_var, self.windows_filter_var)
        self._build_side(right, False, self.linux_dir_var, self.linux_filter_var)

        transfer_bar = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        transfer_bar.pack(fill=tk.X)
        ttk.Button(transfer_bar, text="发送到 Linux", command=self.copy_windows_to_linux).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(transfer_bar, text="发送到 Windows", command=self.copy_linux_to_windows).pack(side=tk.LEFT)

        drag_box = ttk.LabelFrame(self.root, text="拖拽传输", padding=10)
        drag_box.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Radiobutton(drag_box, text="拖到 Linux", variable=self.drag_direction, value="win_to_linux").pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(drag_box, text="拖到 Windows", variable=self.drag_direction, value="linux_to_win").pack(side=tk.LEFT, padx=(0, 12))
        self.drop_label = ttk.Label(drag_box, text="把文件或文件夹拖到这里。目标目录按左右面板当前路径决定。")
        self.drop_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        if TkinterDnD is not None and DND_FILES is not None:
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind("<<Drop>>", self.handle_drop)
        else:
            self.drop_label.configure(text="当前未启用系统拖拽（可安装 tkinterdnd2 后启用）")

        hist = ttk.LabelFrame(self.root, text="历史记录（失败可重试）", padding=10)
        hist.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))

        cols = ("time", "direction", "status", "summary")
        self.history_tree = ttk.Treeview(hist, columns=cols, show="headings", height=6)
        self.history_tree.heading("time", text="时间")
        self.history_tree.heading("direction", text="方向")
        self.history_tree.heading("status", text="状态")
        self.history_tree.heading("summary", text="内容")
        self.history_tree.column("time", width=180, anchor="w")
        self.history_tree.column("direction", width=140, anchor="center")
        self.history_tree.column("status", width=80, anchor="center")
        self.history_tree.column("summary", width=820, anchor="w")
        self.history_tree.pack(fill=tk.X)

        hist_btns = ttk.Frame(hist)
        hist_btns.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(hist_btns, text="重试所选", command=self.retry_selected).pack(side=tk.LEFT)
        ttk.Button(hist_btns, text="刷新历史", command=self.render_history).pack(side=tk.LEFT, padx=8)
        ttk.Button(hist_btns, text="清空历史", command=self.clear_history).pack(side=tk.LEFT)

    def _build_side(self, frame, is_windows: bool, path_var: tk.StringVar, filter_var: tk.StringVar):
        row = ttk.Frame(frame)
        row.pack(fill=tk.X)
        entry = ttk.Entry(row, textvariable=path_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        if is_windows:
            ttk.Button(row, text="选择目录", command=self.pick_windows_dir).pack(side=tk.LEFT, padx=6)
            ttk.Button(row, text="上级", command=self.win_up).pack(side=tk.LEFT)
        else:
            ttk.Button(row, text="选择目录", command=self.pick_linux_dir).pack(side=tk.LEFT, padx=6)
            ttk.Button(row, text="上级", command=self.linux_up).pack(side=tk.LEFT)

        tools = ttk.Frame(frame)
        tools.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(tools, text="类型").pack(side=tk.LEFT)
        filter_box = ttk.Combobox(tools, textvariable=filter_var, values=list(FILE_TYPE_OPTIONS.keys()), state="readonly", width=14)
        filter_box.pack(side=tk.LEFT, padx=(6, 10))
        filter_box.bind("<<ComboboxSelected>>", lambda _: self.refresh_panels())
        new_folder_command = self.create_windows_folder if is_windows else self.create_linux_folder
        ttk.Button(tools, text="新建文件夹", command=new_folder_command).pack(side=tk.RIGHT, padx=(0, 8))
        delete_command = self.delete_windows_selected if is_windows else self.delete_linux_selected
        ttk.Button(tools, text="删除所选", command=delete_command).pack(side=tk.RIGHT)

        search_row = ttk.Frame(frame)
        search_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(search_row, text="搜索").pack(side=tk.LEFT)
        search_var = self.windows_search_var if is_windows else self.linux_search_var
        search_entry = ttk.Entry(search_row, textvariable=search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 10))
        search_entry.bind("<KeyRelease>", lambda _: self.refresh_panels())
        ttk.Label(search_row, text="排序").pack(side=tk.LEFT)
        sort_var = self.windows_sort_var if is_windows else self.linux_sort_var
        sort_box = ttk.Combobox(search_row, textvariable=sort_var, values=SORT_OPTIONS, state="readonly", width=12)
        sort_box.pack(side=tk.LEFT)
        sort_box.bind("<<ComboboxSelected>>", lambda _: self.refresh_panels())

        listbox = tk.Listbox(frame, selectmode=tk.EXTENDED)
        listbox.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        listbox.bind("<Double-Button-1>", lambda _: self.open_selected_dir(is_windows))
        listbox.bind("<Button-3>", lambda event: self.show_context_menu(event, is_windows))
        if is_windows:
            self.windows_listbox = listbox
        else:
            self.linux_listbox = listbox

        self._build_context_menu(is_windows)

    def _build_context_menu(self, is_windows: bool):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="重命名", command=(self.rename_windows_selected if is_windows else self.rename_linux_selected))
        menu.add_command(label="打开所在位置", command=(self.open_windows_location if is_windows else self.open_linux_location))
        menu.add_command(label="查看属性", command=(self.show_windows_properties if is_windows else self.show_linux_properties))
        menu.add_command(label="新建文件夹", command=(self.create_windows_folder if is_windows else self.create_linux_folder))
        menu.add_separator()
        menu.add_command(label="删除所选", command=(self.delete_windows_selected if is_windows else self.delete_linux_selected))
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
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        for rec in reversed(self.history[-200:]):
            self.history_tree.insert("", tk.END, iid=rec["id"], values=(rec.get("time", ""), rec.get("direction", ""), rec.get("status", ""), rec.get("summary", "")))

    def set_status(self, text: str):
        self.status_var.set(text)

    def clear_history(self):
        if not messagebox.askyesno("确认", "确定清空历史记录吗？"):
            return
        self.history = []
        self._save_history()
        self.render_history()
        self.set_status("历史记录已清空")

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
        p = Path(self.windows_dir_var.get())
        if p.parent != p:
            self.windows_dir_var.set(str(p.parent))
            self.refresh_windows()

    def linux_up(self):
        p = self.linux_dir_var.get().rstrip("/")
        if not p:
            p = "/"
        parent = "/" if p == "/" else str(Path(p).parent).replace("\\", "/")
        self.linux_dir_var.set(parent)
        self.refresh_linux()

    def refresh_panels(self):
        self.refresh_windows()
        self.refresh_linux()
        self.set_status("面板已刷新")

    def refresh_windows(self):
        self.windows_entries = self.read_dir_entries(self.windows_dir_var.get(), False, self.windows_filter_var.get(), self.windows_search_var.get(), self.windows_sort_var.get())
        self.render_entries(self.windows_listbox, self.windows_entries)

    def refresh_linux(self):
        linux_real = linux_to_unc(self.linux_dir_var.get(), self.distro_var.get().strip())
        self.linux_entries = self.read_dir_entries(linux_real, True, self.linux_filter_var.get(), self.linux_search_var.get(), self.linux_sort_var.get())
        self.render_entries(self.linux_listbox, self.linux_entries)

    @staticmethod
    def read_dir_entries(path: str, is_linux_view: bool, filter_name: str, search_text: str, sort_mode: str):
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
                    if child.is_dir():
                        continue
                    if child.suffix.lower() not in allowed:
                        continue

                if keyword and keyword not in child.name.lower():
                    continue

                try:
                    mtime = child.stat().st_mtime
                except Exception:
                    mtime = 0

                entries.append(
                    {
                        "name": child.name,
                        "is_dir": child.is_dir(),
                        "full_path": str(child),
                        "is_linux_view": is_linux_view,
                        "mtime": mtime,
                    }
                )
        except Exception:
            pass
        return FileBridgeApp.sort_entries(entries, sort_mode)

    @staticmethod
    def sort_entries(entries, sort_mode: str):
        if sort_mode == "名称 Z-A":
            return sorted(entries, key=lambda x: x["name"].lower(), reverse=True)
        if sort_mode == "最新修改":
            return sorted(entries, key=lambda x: x["mtime"], reverse=True)
        if sort_mode == "最早修改":
            return sorted(entries, key=lambda x: x["mtime"])
        if sort_mode == "文件夹优先":
            return sorted(entries, key=lambda x: (not x["is_dir"], x["name"].lower()))
        return sorted(entries, key=lambda x: x["name"].lower())

    @staticmethod
    def render_entries(listbox: tk.Listbox, entries):
        listbox.delete(0, tk.END)
        for item in entries:
            icon = get_entry_icon(item["name"], item["is_dir"])
            listbox.insert(tk.END, f"{icon} {item['name']}")

    def show_context_menu(self, event, is_windows: bool):
        listbox = self.windows_listbox if is_windows else self.linux_listbox
        index = listbox.nearest(event.y)
        if index < 0:
            return
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(index)
        listbox.activate(index)
        menu = self.windows_menu if is_windows else self.linux_menu
        if menu is None:
            return
        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()

    def get_selected_entries(self, is_windows: bool):
        listbox = self.windows_listbox if is_windows else self.linux_listbox
        entries = self.windows_entries if is_windows else self.linux_entries
        indexes = listbox.curselection()
        return [entries[i] for i in indexes]

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

    def open_selected_dir(self, is_windows: bool):
        if is_windows:
            listbox = self.windows_listbox
            entries = self.windows_entries
            path_var = self.windows_dir_var
            distro = ""
        else:
            listbox = self.linux_listbox
            entries = self.linux_entries
            path_var = self.linux_dir_var
            distro = self.distro_var.get().strip()

        selected = listbox.curselection()
        if not selected:
            return
        item = entries[selected[0]]
        if not item["is_dir"]:
            return
        full = item["full_path"]
        if is_windows:
            path_var.set(full)
        else:
            path_var.set(unc_to_linux(full, distro))
        self.refresh_panels()

    def copy_windows_to_linux(self):
        indexes = self.windows_listbox.curselection()
        if not indexes:
            messagebox.showinfo("提示", "请先在 Windows 面板选择文件或文件夹。")
            return
        sources = [self.windows_entries[i]["full_path"] for i in indexes]
        dst_root = linux_to_unc(self.linux_dir_var.get(), self.distro_var.get().strip())
        self.transfer(sources, dst_root, "win_to_linux")

    def copy_linux_to_windows(self):
        indexes = self.linux_listbox.curselection()
        if not indexes:
            messagebox.showinfo("提示", "请先在 Linux 面板选择文件或文件夹。")
            return
        sources = [self.linux_entries[i]["full_path"] for i in indexes]
        dst_root = self.windows_dir_var.get()
        self.transfer(sources, dst_root, "linux_to_win")

    def handle_drop(self, event):
        try:
            dropped = list(self.root.tk.splitlist(event.data))
        except Exception:
            dropped = [event.data]
        dropped = [p for p in dropped if p.strip()]
        if not dropped:
            return
        if self.drag_direction.get() == "win_to_linux":
            dst_root = linux_to_unc(self.linux_dir_var.get(), self.distro_var.get().strip())
            direction = "win_to_linux"
        else:
            dst_root = self.windows_dir_var.get()
            direction = "linux_to_win"
        self.transfer(dropped, dst_root, direction)

    @staticmethod
    def unique_target(path_obj: Path) -> Path:
        if not path_obj.exists():
            return path_obj
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        stem = path_obj.stem
        suffix = path_obj.suffix
        parent = path_obj.parent
        candidate = parent / f"{stem} (copy {timestamp}){suffix}"
        n = 1
        while candidate.exists():
            candidate = parent / f"{stem} (copy {timestamp}-{n}){suffix}"
            n += 1
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
                errors.append(f"源不存在: {src}")
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
        summary = safe_summary([c["source"] for c in copied]) if copied else safe_summary(sources)
        if skipped:
            summary = f"{summary}，已跳过快捷方式 {len(skipped)} 项"
        rec = {
            "id": str(uuid4()),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "direction": direction,
            "status": status,
            "summary": summary if not errors else f"{summary} (部分失败)",
            "sources": list(sources),
            "dst_root": str(dst_path),
            "copied": copied,
            "errors": errors,
        }
        self.history.append(rec)
        self._save_history()
        self.render_history()
        self.refresh_panels()

        notices = []
        if skipped:
            notices.append("已跳过快捷方式：" + ", ".join(skipped[:8]))
        if errors:
            self.set_status("传输部分失败")
            notices.extend(errors[:8])
            messagebox.showwarning("完成（部分失败）", "\n".join(notices))
        else:
            self.set_status(f"已成功复制 {len(copied)} 项")
            message = f"已成功复制 {len(copied)} 项。"
            if skipped:
                message += "\n\n已自动跳过快捷方式文件。"
            messagebox.showinfo("完成", message)

    def delete_windows_selected(self):
        self.delete_selected(self.windows_listbox, self.windows_entries, "Windows", self.refresh_windows)

    def delete_linux_selected(self):
        self.delete_selected(self.linux_listbox, self.linux_entries, "Linux", self.refresh_linux)

    def delete_selected(self, listbox, entries, side_name: str, refresh_callback):
        indexes = listbox.curselection()
        if not indexes:
            messagebox.showinfo("提示", f"请先在 {side_name} 面板选择文件或文件夹。")
            return

        selected_entries = [entries[i] for i in indexes]
        names = [item["name"] for item in selected_entries]
        summary = safe_summary(names)
        confirmed = messagebox.askyesno("删除确认", f"确定删除 {side_name} 面板中选中的 {len(selected_entries)} 项吗？\n\n{summary}\n\n此操作不可撤销。")
        if not confirmed:
            return

        deleted = []
        errors = []
        for item in selected_entries:
            target = Path(item["full_path"])
            try:
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
                deleted.append(item["full_path"])
            except Exception as exc:
                errors.append(f"{item['name']}: {exc}")

        status = "success" if not errors else "failed"
        self.history.append(
            {
                "id": str(uuid4()),
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "direction": f"delete_{side_name.lower()}",
                "status": status,
                "summary": safe_summary(deleted) if deleted else summary,
                "sources": deleted,
                "dst_root": "",
                "copied": [],
                "errors": errors,
            }
        )
        self._save_history()
        self.render_history()
        refresh_callback()

        if errors:
            self.set_status("删除部分失败")
            messagebox.showwarning("删除完成（部分失败）", "\n".join(errors[:8]))
        else:
            self.set_status(f"已删除 {len(deleted)} 项")
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

        side_name = "windows" if is_windows else "linux"
        self.history.append(
            {
                "id": str(uuid4()),
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "direction": f"mkdir_{side_name}",
                "status": "success",
                "summary": f"新建文件夹 {folder_name}",
                "sources": [],
                "dst_root": str(new_dir.parent),
                "copied": [{"source": "", "target": str(new_dir)}],
                "errors": [],
            }
        )
        self._save_history()
        self.render_history()
        self.refresh_panels()
        self.set_status(f"已新建文件夹 {folder_name}")

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

        side_name = "windows" if is_windows else "linux"
        self.history.append(
            {
                "id": str(uuid4()),
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "direction": f"rename_{side_name}",
                "status": "success",
                "summary": f"{old_path.name} -> {new_path.name}",
                "sources": [str(old_path)],
                "dst_root": str(new_path.parent),
                "copied": [{"source": str(old_path), "target": str(new_path)}],
                "errors": [],
            }
        )
        self._save_history()
        self.render_history()
        self.refresh_panels()
        self.set_status(f"已重命名为 {new_path.name}")

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
            if is_windows and target.exists():
                subprocess.Popen(["explorer", "/select,", str(target)])
            else:
                path_to_open = str(target if target.is_dir() else target.parent)
                os.startfile(path_to_open)
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

        file_type = "文件夹" if target.is_dir() else "文件"
        size_text = "-"
        if target.is_file():
            size_text = format_bytes(stat.st_size)

        lines = [
            f"名称：{target.name}",
            f"类型：{file_type}",
            f"大小：{size_text}",
            f"修改时间：{datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}",
            f"路径：{target}",
        ]
        if not is_windows:
            lines.append(f"Linux 路径：{unc_to_linux(str(target), self.distro_var.get().strip())}")

        messagebox.showinfo("属性", "\n\n".join(lines))

    def retry_selected(self):
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择一条历史记录。")
            return
        rec_id = selected[0]
        rec = next((x for x in self.history if x["id"] == rec_id), None)
        if not rec:
            return
        sources = rec.get("sources", [])
        dst_root = rec.get("dst_root", "")
        direction = rec.get("direction", "retry")
        if not sources or not dst_root:
            messagebox.showerror("错误", "该记录缺少重试信息。")
            return
        self.transfer(sources, dst_root, direction)


def main():
    if TkinterDnD is not None:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = FileBridgeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

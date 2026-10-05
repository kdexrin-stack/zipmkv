from __future__ import annotations

import contextlib
import os
from pathlib import Path
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from .archive_tools import find_archive_tools
from .file_selection import InputFileCollection
from .theme import BASE_FONT_SIZE, COLORS, FONT_FAMILY, configure_listbox


class LogFrame(ttk.Frame):
    """Modern asynchronous console log panel with automatic memory truncation."""

    def __init__(self, master, height: int = 5, max_lines: int = 2500):
        super().__init__(master, style="Surface.TFrame")
        self.max_lines = max_lines
        self.text = scrolledtext.ScrolledText(self, height=height, wrap=tk.WORD)
        self.text.configure(
            bg=COLORS["console"],
            fg=COLORS["console_text"],
            insertbackground=COLORS["text"],
            selectbackground=COLORS["selection"],
            selectforeground=COLORS["primary_hover"],
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=COLORS["console_border"],
            highlightcolor=COLORS["primary"],
            font=(FONT_FAMILY, BASE_FONT_SIZE),
            padx=10,
            pady=8,
        )
        self.text.pack(fill=tk.BOTH, expand=True)
        self._pending: queue.Queue[str] = queue.Queue()
        self._drain_after_id: str | None = None
        self.bind("<Destroy>", self._cancel_drain, add="+")

    def _cancel_drain(self, event=None) -> None:
        if event is not None and event.widget is not self:
            return
        if self._drain_after_id is not None:
            try:
                self.after_cancel(self._drain_after_id)
            except tk.TclError:
                pass
            self._drain_after_id = None

    def _append(self, text: str) -> None:
        self.text.insert(tk.END, text + "\n")
        self._enforce_line_limit()
        self.text.see(tk.END)

    def _enforce_line_limit(self) -> None:
        try:
            line_count = int(float(self.text.index("end-1c").split(".")[0]))
            if line_count > self.max_lines:
                delete_to = f"{line_count - self.max_lines + 200}.0"
                self.text.delete("1.0", delete_to)
        except Exception:
            pass

    def _schedule_drain(self) -> None:
        if self._drain_after_id is None:
            try:
                self._drain_after_id = self.after(20, self._drain_pending)
            except tk.TclError:
                pass

    def _drain_pending(self) -> None:
        self._drain_after_id = None
        lines = []
        try:
            while len(lines) < 120:
                lines.append(self._pending.get_nowait())
        except queue.Empty:
            pass
        if lines:
            self.text.insert(tk.END, "\n".join(lines) + "\n")
            self._enforce_line_limit()
            self.text.see(tk.END)
        if not self._pending.empty():
            try:
                self._drain_after_id = self.after(20, self._drain_pending)
            except tk.TclError:
                pass

    def write(self, message: str) -> None:
        text = str(message).rstrip()
        if not text:
            return

        if threading.current_thread() is threading.main_thread():
            self._append(text)
        else:
            self._pending.put(text)
            self._schedule_drain()

    def clear(self) -> None:
        self.text.delete("1.0", tk.END)


class _LogStream:
    def __init__(self, writer):
        self.writer = writer
        self.buffer = ""

    def write(self, value: str) -> int:
        self.buffer += value
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line.strip():
                self.writer(line)
        return len(value)

    def flush(self) -> None:
        if self.buffer.strip():
            self.writer(self.buffer)
        self.buffer = ""


def bind_listbox_delete_menu(
    listbox: tk.Listbox,
    delete_selected,
    clear_all=None,
    delete_label: str = "删除所选",
) -> None:
    configure_listbox(listbox)
    menu = tk.Menu(
        listbox,
        tearoff=0,
        bg=COLORS["surface"],
        fg=COLORS["text"],
        activebackground=COLORS["primary"],
        activeforeground="#ffffff",
        relief=tk.FLAT,
        bd=1,
        font=(FONT_FAMILY, BASE_FONT_SIZE),
    )
    menu.add_command(label=delete_label, command=delete_selected)
    
    def select_all_items(_event=None) -> str:
        listbox.selection_set(0, tk.END)
        return "break"

    menu.add_command(label="全选", command=lambda: select_all_items())
    if clear_all:
        menu.add_separator()
        menu.add_command(label="清空列表", command=clear_all)

    def show_menu(event) -> str:
        index = listbox.nearest(event.y)
        if index >= 0:
            if index not in listbox.curselection():
                listbox.selection_clear(0, tk.END)
                listbox.selection_set(index)
                listbox.activate(index)
        menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def delete_event(_event=None) -> str:
        delete_selected()
        return "break"

    listbox.bind("<Button-3>", show_menu)
    listbox.bind("<Delete>", delete_event)
    listbox.bind("<BackSpace>", delete_event)
    listbox.bind("<Control-a>", select_all_items)
    listbox.bind("<Control-A>", select_all_items)


def open_folder_in_explorer(target_path: str | Path | None) -> None:
    """Open folder in Explorer, or highlight the specific file on Windows."""
    if not target_path:
        return
    path = Path(target_path).resolve()
    if os.name == "nt":
        if path.is_file() and path.exists():
            subprocess.Popen(f'explorer.exe /select,"{path}"')
        else:
            target_dir = path if path.is_dir() else path.parent
            target_dir.mkdir(parents=True, exist_ok=True)
            subprocess.Popen(f'explorer.exe "{target_dir}"')
    else:
        import webbrowser
        folder = path.parent if path.is_file() else path
        folder.mkdir(parents=True, exist_ok=True)
        webbrowser.open(f"file://{folder}")


class FileListCard(ttk.LabelFrame):
    """Reusable, high-ergonomics card component wrapping file collection, listbox, buttons, and badges."""

    def __init__(
        self,
        master,
        title: str = "Step 1 · 📁 输入素材列表",
        collection: InputFileCollection | None = None,
        filetypes: list[tuple[str, str]] | None = None,
        file_dialog_title: str = "选择素材文件",
        height: int = 4,
        padding: int | tuple[int, int] = 8,
        on_changed=None,
    ):
        super().__init__(master, text=title, style="Card.TLabelframe", padding=padding)
        self.collection = collection or InputFileCollection()
        self.filetypes = filetypes or [("所有文件", "*.*")]
        self.file_dialog_title = file_dialog_title
        self.on_changed = on_changed
        self.summary_var = tk.StringVar(value=self.collection.get_summary())
        self._build_ui(height)

    def _build_ui(self, height: int) -> None:
        button_row = ttk.Frame(self)
        button_row.pack(anchor=tk.W, pady=(0, 4))
        ttk.Button(button_row, text="+ 选择文件", command=self.choose_files).pack(side=tk.LEFT)
        ttk.Button(button_row, text="📁 扫描文件夹", command=self.choose_folder).pack(side=tk.LEFT, padx=6)
        ttk.Button(button_row, text="清空", command=self.clear).pack(side=tk.LEFT)

        self.listbox = tk.Listbox(self, height=height, exportselection=False)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=2)
        bind_listbox_delete_menu(self.listbox, self.delete_selected, self.clear)

        self.summary_label = ttk.Label(self, textvariable=self.summary_var, style="Badge.TLabel")
        self.summary_label.pack(anchor=tk.W, pady=(2, 0))

    def choose_files(self) -> None:
        from tkinter import filedialog
        paths = filedialog.askopenfilenames(title=self.file_dialog_title, filetypes=self.filetypes)
        if paths:
            self.collection.add_files(list(paths))
            self.refresh()

    def choose_folder(self) -> None:
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="选择文件夹递归扫描")
        if folder:
            self.collection.add_folder(folder)
            self.refresh()

    def delete_selected(self) -> None:
        selected = list(self.listbox.curselection())
        if selected:
            self.collection.remove_indices(selected)
            self.refresh()

    def clear(self) -> None:
        self.collection.clear()
        self.refresh()

    def refresh(self) -> None:
        self.listbox.delete(0, tk.END)
        for text, _ in self.collection.display_items:
            self.listbox.insert(tk.END, text)
        self.summary_var.set(self.collection.get_summary())
        if self.on_changed:
            self.on_changed()


class ToolFrame(ttk.Frame):
    """Base class for all functional workspace modules."""

    title = "工具"
    description = ""

    def __init__(self, master):
        super().__init__(master, padding=(14, 10), style="Workspace.TFrame")
        self.log_frame = LogFrame(self, height=5)
        self.last_output_dir: Path | None = None
        self._ui_pending: queue.Queue[object] = queue.Queue()
        self._ui_after_id: str | None = None
        self.bind("<Destroy>", self._cancel_ui_drain, add="+")

    def _cancel_ui_drain(self, event=None) -> None:
        if event is not None and event.widget is not self:
            return
        if self._ui_after_id is not None:
            try:
                self.after_cancel(self._ui_after_id)
            except tk.TclError:
                pass
            self._ui_after_id = None

    def _schedule_ui_drain(self) -> None:
        if self._ui_after_id is None:
            try:
                self._ui_after_id = self.after(20, self._drain_ui_pending)
            except tk.TclError:
                pass

    def _drain_ui_pending(self) -> None:
        self._ui_after_id = None
        try:
            while True:
                callback = self._ui_pending.get_nowait()
                callback()
        except queue.Empty:
            pass
        except tk.TclError:
            return
        if not self._ui_pending.empty():
            try:
                self._ui_after_id = self.after(20, self._drain_ui_pending)
            except tk.TclError:
                pass

    def call_in_ui(self, callback) -> None:
        if threading.current_thread() is threading.main_thread():
            callback()
        else:
            self._ui_pending.put(callback)
            self._schedule_ui_drain()

    def reveal_output_folder(self) -> None:
        if self.last_output_dir:
            open_folder_in_explorer(self.last_output_dir)

    def run_background(
        self,
        button: tk.Widget,
        job,
        done_message: str = "处理完成",
        output_dir: str | Path | None = None,
    ) -> None:
        button.config(state=tk.DISABLED)
        self._set_app_status("⏳ 正在处理中，请稍候...")
        if output_dir:
            self.last_output_dir = Path(output_dir)
        import time

        def worker():
            start_time = time.time()
            try:
                stream = _LogStream(self.log_frame.write)
                with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                    raw_msg = job()
                    message = raw_msg or done_message
                stream.flush()
                elapsed = time.time() - start_time
                status_msg = f"✓ {message} · 耗时 {elapsed:.1f}s"
                self.call_in_ui(lambda: self._set_app_status(status_msg))
                self.call_in_ui(lambda: messagebox.showinfo("完成", status_msg))
            except Exception as exc:
                error_message = str(exc)
                self.log_frame.write(f"任务执行失败: {error_message}")
                self.call_in_ui(lambda: self._set_app_status("✕ 处理失败，请查看下方日志"))
                self.call_in_ui(lambda value=error_message: messagebox.showerror("错误", value))
            finally:
                self.call_in_ui(lambda: button.config(state=tk.NORMAL))

        threading.Thread(target=worker, daemon=True).start()

    def _set_app_status(self, message: str) -> None:
        top = self.winfo_toplevel()
        status_var = getattr(top, "status_var", None)
        if status_var is not None:
            status_var.set(message)


class ArchiveToolSelector(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="内置解压引擎", style="Card.TLabelframe", padding=6)
        self.summary_var = tk.StringVar()
        self._build()
        self.refresh()

    def _build(self) -> None:
        ttk.Label(self, textvariable=self.summary_var, wraplength=700, style="Muted.TLabel").pack(fill=tk.X)

    def refresh(self) -> None:
        tools = find_archive_tools()
        if tools:
            first = tools[0]
            self.summary_var.set(f"内置引擎就绪: 7-Zip ({first.executable.name}) · 支持 zip/7z/rar/tar/epub/cbz 等完整格式解压")
        else:
            self.summary_var.set("使用 Python 原生引擎 (支持 zip/epub/tar)")

    def selected_tool(self):
        return None

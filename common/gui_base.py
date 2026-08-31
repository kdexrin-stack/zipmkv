from __future__ import annotations

import contextlib
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from .archive_tools import find_archive_tools
from .theme import BASE_FONT_SIZE, COLORS, FONT_FAMILY, configure_listbox


class LogFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, style="Surface.TFrame")
        self.text = scrolledtext.ScrolledText(self, height=11, wrap=tk.WORD)
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
            padx=12,
            pady=10,
        )
        self.text.pack(fill=tk.BOTH, expand=True)
        self._pending: queue.Queue[str] = queue.Queue()
        self._drain_after_id: str | None = self.after(30, self._drain_pending)
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
        self.text.see(tk.END)

    def _drain_pending(self) -> None:
        self._drain_after_id = None
        lines = []
        try:
            while len(lines) < 50:
                lines.append(self._pending.get_nowait())
        except queue.Empty:
            pass
        if lines:
            self.text.insert(tk.END, "\n".join(lines) + "\n")
            self.text.see(tk.END)
        try:
            self._drain_after_id = self.after(30, self._drain_pending)
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


class ToolFrame(ttk.Frame):
    title = "工具"
    description = ""

    def __init__(self, master):
        super().__init__(master, padding=18, style="Workspace.TFrame")
        self.log_frame = LogFrame(self)
        self._ui_pending: queue.Queue[object] = queue.Queue()
        self._ui_after_id: str | None = self.after(30, self._drain_ui_pending)
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
        try:
            self._ui_after_id = self.after(30, self._drain_ui_pending)
        except tk.TclError:
            pass

    def call_in_ui(self, callback) -> None:
        self._ui_pending.put(callback)

    def run_background(self, button: tk.Widget, job, done_message: str = "处理完成") -> None:
        button.config(state=tk.DISABLED)
        self._set_app_status("正在处理，请稍候...")
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
                status_msg = f"{message}（耗时 {elapsed:.1f}s）"
                self.call_in_ui(lambda: self._set_app_status(status_msg))
                self.call_in_ui(lambda: messagebox.showinfo("完成", status_msg))
            except Exception as exc:
                error_message = str(exc)
                self.log_frame.write(f"任务失败: {error_message}")
                self.call_in_ui(lambda: self._set_app_status("处理失败，请查看日志"))
                self.call_in_ui(lambda value=error_message: messagebox.showerror("错误", value))
            finally:
                self.call_in_ui(lambda: button.config(state=tk.NORMAL))

        threading.Thread(target=worker, daemon=True).start()

    def _set_app_status(self, message: str) -> None:
        status_var = getattr(self.winfo_toplevel(), "status_var", None)
        if status_var is not None:
            status_var.set(message)


class ArchiveToolSelector(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="内置压缩工具", padding=8)
        self.summary_var = tk.StringVar()
        self._build()
        self.refresh()

    def _build(self) -> None:
        ttk.Label(self, textvariable=self.summary_var, wraplength=650, style="Muted.TLabel").pack(fill=tk.X)

    def refresh(self) -> None:
        tools = find_archive_tools()
        if tools:
            first = tools[0]
            self.summary_var.set(f"使用项目内置 7-Zip: {first.executable}")
        else:
            self.summary_var.set("未找到项目内置 7-Zip；zip/epub 仍可用内置方式解压，rar/7z 需要重新打包内置工具。")

    def selected_tool(self):
        return None

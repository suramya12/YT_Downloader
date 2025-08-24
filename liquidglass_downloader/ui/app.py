from __future__ import annotations
import customtkinter as ctk
import re

from .theme import init_theme
from ..core.config import CONFIG
from ..core.downloader import DownloadManager
from .views.queue_view import QueueView
from .views.history_view import HistoryView
from .views.settings_view import SettingsView
from .notifier import toast

YOUTUBE_URL_RE = re.compile(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("LiquidGlass Downloader")
        self.geometry("1120x680")
        init_theme(CONFIG.settings.theme)

        self.dm = DownloadManager()

        root = ctk.CTkFrame(self)
        root.pack(fill="both", expand=True)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(root, width=200, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="ns")
        ctk.CTkLabel(sidebar, text="LiquidGlass", font=("Segoe UI", 18, "bold")).pack(pady=(18,10))
        self.btn_queue = ctk.CTkButton(sidebar, text="Queue", command=self._show_queue, width=160)
        self.btn_queue.pack(pady=6)
        self.btn_history = ctk.CTkButton(sidebar, text="History", command=self._show_history, width=160)
        self.btn_history.pack(pady=6)
        self.btn_settings = ctk.CTkButton(sidebar, text="Settings", command=self._show_settings, width=160)
        self.btn_settings.pack(pady=6)

        self.content = ctk.CTkFrame(root, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")

        # Status bar FIRST so methods can reference it safely
        self.status = ctk.CTkLabel(self, text="Ready")
        self.status.pack(fill="x", side="bottom", padx=8, pady=4)

        self.queue_view = QueueView(self.content, self.dm)
        self.history_view = HistoryView(self.content)
        self.settings_view = SettingsView(self.content, self.dm, self._theme_changed)

        self.queue_view.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.history_view.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.settings_view.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._show_queue()
        self._last_clipboard = ""
        self.after(1200, self._tick)

    def _theme_changed(self, mode: str):
        init_theme(mode)
        toast(self, f"Theme switched to {mode}")

    def _show_queue(self):
        self.queue_view.lift()
        if hasattr(self, "status"):
            self.status.configure(text="Queue")

    def _show_history(self):
        self.history_view.lift()
        if hasattr(self, "status"):
            self.status.configure(text="History")

    def _show_settings(self):
        self.settings_view.lift()
        if hasattr(self, "status"):
            self.status.configure(text="Settings")

    def _tick(self):
        try:
            if CONFIG.settings.clipboard_watch:
                self.after_idle(self._check_clipboard)
        except Exception as e:
            print(f"Error in tick: {e}")
        finally:
            self.after(2000, self._tick)
    
    def _check_clipboard(self):
        try:
            data = self.clipboard_get()
            if data and data != self._last_clipboard and YOUTUBE_URL_RE.search(data):
                self._last_clipboard = data
                self._handle_clipboard_url(data)
        except Exception:
            # Ignore clipboard errors
            pass
    
    def _handle_clipboard_url(self, url):
        toast(self, "YouTube link detected. Click 'Add' in Queue.")
        self.queue_view.url_entry.delete(0, "end")
        self.queue_view.url_entry.insert(0, url)

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()

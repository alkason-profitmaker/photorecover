"""
PhotoRecover 2.0 - Native Lightweight Desktop Application (Tkinter)
Zero-browser native desktop GUI for local, private photo recovery and preview.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from .recovery import SDCardRecovery


class PhotoRecoverDesktopApp(tk.Tk):
    """Native Tkinter desktop window for PhotoRecover."""

    def __init__(self) -> None:
        super().__init__()
        self.title("PhotoRecover 2.0 - Permanent Photo Rescue Vault")
        self.geometry("980x700")
        self.minsize(860, 600)
        self.configure(bg="#0f172a")

        self.source = tk.StringVar()
        default_out = str(Path.home() / "Pictures" / "PhotoRecover")
        self.output = tk.StringVar(value=default_out)
        self.status = tk.StringVar(value="Select a storage drive or disk image to begin recovery.")
        self.count = tk.StringVar(value="—")
        self.thumb_refs: list[ImageTk.PhotoImage] = []

        self._build_ui()

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background="#0f172a")
        style.configure("TLabelframe", background="#0f172a", foreground="#38bdf8")
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"), background="#0f172a", foreground="#38bdf8")
        style.configure("TLabel", background="#0f172a", foreground="#f8fafc", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 20, "bold"), foreground="#38bdf8")
        style.configure("Sub.TLabel", font=("Segoe UI", 10), foreground="#94a3b8")
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"), background="#0284c7", foreground="#ffffff")
        style.configure("Secondary.TButton", font=("Segoe UI", 10))

        root = ttk.Frame(self, padding=24)
        root.pack(fill="both", expand=True)

        header_frame = ttk.Frame(root)
        header_frame.pack(fill="x", pady=(0, 16))
        ttk.Label(header_frame, text="PhotoRecover 2.0", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header_frame,
            text="Local & Private Photo Rescue • Never writes to source • Guaranteed permanent preservation",
            style="Sub.TLabel"
        ).pack(anchor="w")

        # Source Selection Card
        source_card = ttk.LabelFrame(root, text=" 1 · Source Storage Device or Disk Image ", padding=14)
        source_card.pack(fill="x", pady=(0, 12))
        source_row = ttk.Frame(source_card)
        source_row.pack(fill="x")
        ttk.Entry(source_row, textvariable=self.source, font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True)
        ttk.Button(source_row, text="Browse Image…", command=self.choose_source_file).pack(side="left", padx=(8, 0))
        ttk.Button(source_row, text="Select Drive…", command=self.choose_source_drive).pack(side="left", padx=(6, 0))

        # Destination Selection Card
        out_card = ttk.LabelFrame(root, text=" 2 · Permanent Recovery Vault Folder ", padding=14)
        out_card.pack(fill="x", pady=(0, 14))
        out_row = ttk.Frame(out_card)
        out_row.pack(fill="x")
        ttk.Entry(out_row, textvariable=self.output, font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True)
        ttk.Button(out_row, text="Choose Folder…", command=self.choose_output).pack(side="left", padx=(8, 0))
        ttk.Button(out_row, text="Open in Explorer", command=self.open_explorer).pack(side="left", padx=(6, 0))

        # Action Bar
        action_bar = ttk.Frame(root)
        action_bar.pack(fill="x", pady=(0, 10))
        self.scan_button = ttk.Button(
            action_bar,
            text="🚀 Scan & Recover Photos",
            style="Accent.TButton",
            command=self.start_recovery
        )
        self.scan_button.pack(side="left")
        ttk.Label(action_bar, textvariable=self.count, font=("Segoe UI", 11, "bold")).pack(side="right")

        ttk.Label(root, textvariable=self.status, font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 6))
        self.progress = ttk.Progressbar(root, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 14))

        # Gallery Results Area
        results_card = ttk.LabelFrame(root, text=" Rescued Photos (Permanent Vault) ", padding=10)
        results_card.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(results_card, bg="#0b1120", highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(results_card, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.grid_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.grid_frame.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

    def choose_source_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Disk Image File",
            filetypes=[("Disk Images & Media", "*.img *.raw *.dd *.bin *.iso"), ("All Files", "*.*")]
        )
        if path:
            self.source.set(path)

    def choose_source_drive(self) -> None:
        if sys.platform == "win32":
            import string
            drives = [f"{d}:\\" for d in string.ascii_uppercase if Path(f"{d}:\\").exists()]
            path = filedialog.askdirectory(title="Select Mounted Storage Card Drive")
            if path:
                self.source.set(path)
        else:
            path = filedialog.askdirectory(title="Select Storage Mount Point")
            if path:
                self.source.set(path)

    def choose_output(self) -> None:
        path = filedialog.askdirectory(title="Select Permanent Recovery Folder")
        if path:
            self.output.set(path)

    def open_explorer(self) -> None:
        folder = self.output.get().strip()
        if not folder:
            return
        p = Path(folder)
        p.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                import os
                os.startfile(str(p))
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", str(p)])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(p)])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def start_recovery(self) -> None:
        src = self.source.get().strip()
        dest = self.output.get().strip()
        if not src or not dest:
            messagebox.showwarning("PhotoRecover", "Please select both a source media and a destination folder.")
            return

        self.scan_button.configure(state="disabled")
        self.status.set("Scanning source media sectors safely (Read-Only)...")
        self.progress.configure(value=0, maximum=100)
        self.count.set("Scanning...")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        def on_progress(p: dict) -> None:
            bytes_scanned = p.get("bytes_scanned", 0)
            total = p.get("total_bytes", 1) or 1
            percent = int((bytes_scanned / total) * 100)
            self.after(0, lambda: self.progress.configure(value=percent, maximum=100))

        try:
            engine = SDCardRecovery(
                validate_images=True,
                deduplicate=True,
                attempt_repair=True,
                verbose=False
            )
            items = engine.recover(
                source_path=self.source.get().strip(),
                output_dir=self.output.get().strip(),
                progress_callback=on_progress
            )
            self.after(0, lambda: self._on_success(items))
        except Exception as e:
            self.after(0, lambda: self._on_failure(str(e)))

    def _on_failure(self, err: str) -> None:
        self.scan_button.configure(state="normal")
        self.status.set("Recovery failed.")
        self.count.set("Error")
        messagebox.showerror("PhotoRecover Error", err)

    def _on_success(self, items: list) -> None:
        self.scan_button.configure(state="normal")
        self.count.set(f"{len(items)} Rescued")
        self.status.set("✓ Complete! All photos permanently stored in vault. Nothing was deleted.")

        # Clear existing
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        self.thumb_refs.clear()

        cols = 4
        for idx, it in enumerate(items[:60]):
            try:
                if it.thumbnail_bytes:
                    img = Image.open(it.thumbnail_bytes)
                else:
                    img = Image.open(it.path)
                img.thumbnail((160, 120))
                photo = ImageTk.PhotoImage(img)
                self.thumb_refs.append(photo)

                card = ttk.Frame(self.grid_frame, padding=6)
                card.grid(row=idx // cols, column=idx % cols, padx=8, pady=8)
                lbl_img = ttk.Label(card, image=photo)
                lbl_img.pack()
                ttk.Label(card, text=it.filename, font=("Segoe UI", 8), width=22).pack(pady=(4, 0))
            except Exception:
                continue


def launch_desktop() -> None:
    app = PhotoRecoverDesktopApp()
    app.mainloop()


if __name__ == "__main__":
    launch_desktop()

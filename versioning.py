import customtkinter as ctk
from tkinter import filedialog
from datetime import datetime
import shutil
from pathlib import Path
import json

# === App Setup ===
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class BackupApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("File Versioning Backup Tool")
        self.geometry("600x400")

        # --- Variables ---
        self.source_dir = ctk.StringVar()
        self.dest_dir = ctk.StringVar()

        # --- UI Layout ---
        self.create_widgets()

    def create_widgets(self):
        ctk.CTkLabel(self, text="Source Folder:").pack(pady=5)
        ctk.CTkEntry(self, textvariable=self.source_dir, width=400).pack(pady=5)
        ctk.CTkButton(self, text="Browse", command=self.select_source).pack()

        ctk.CTkLabel(self, text="Destination Folder:").pack(pady=5)
        ctk.CTkEntry(self, textvariable=self.dest_dir, width=400).pack(pady=5)
        ctk.CTkButton(self, text="Browse", command=self.select_dest).pack()

        ctk.CTkButton(self, text="Run Backup", command=self.run_backup).pack(pady=20)
        self.status_label = ctk.CTkLabel(self, text="")
        self.status_label.pack()

    def select_source(self):
        path = filedialog.askdirectory()
        if path:
            self.source_dir.set(path)

    def select_dest(self):
        path = filedialog.askdirectory()
        if path:
            self.dest_dir.set(path)

    def run_backup(self):
        src = Path(self.source_dir.get())
        dest_base = Path(self.dest_dir.get())
        if not src.exists() or not dest_base.exists():
            self.status_label.configure(text="Invalid folder paths.", text_color="red")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        zip_name = f"backup_{timestamp}"
        temp_zip_path = src.parent / zip_name
        log_file = dest_base / "backup_log.txt"

        try:
            zip_file = Path(shutil.make_archive(str(temp_zip_path), 'zip', src))
            dest_path = dest_base / zip_file.name
            shutil.move(str(zip_file), dest_path)

            # Log success
            with open(log_file, "a") as log:
                log.write(f"[{timestamp}] SUCCESS: {zip_file.name} -> {dest_path}\n")

            self.status_label.configure(text=f"Backup completed: {dest_path}", text_color="green")
        except Exception as e:
            with open(log_file, "a") as log:
                log.write(f"[{timestamp}] ERROR: {e}\n")
            self.status_label.configure(text=f"Backup failed: {e}", text_color="red")

if __name__ == "__main__":
    app = BackupApp()
    app.mainloop()

import customtkinter as ctk
from tkinter import filedialog
from datetime import datetime
import shutil
from pathlib import Path
import json

# === Settings ===
SETTINGS_FILE = Path("backup_settings.json")

# === App Setup ===
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("dark-blue")


class BackupApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("File Versioning Backup Tool")
        self.geometry("725x250")

        self.source_dir = ctk.StringVar()
        self.dest_dir = ctk.StringVar()

        self.load_settings()
        self.create_widgets()

    def create_widgets(self):
        # --- Frames ---
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(padx=20, pady=20, fill="x")

        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(padx=20, pady=10, fill="x")

        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.pack(padx=20, pady=10, fill="x")

        # === Input Frame ===
        # Source
        ctk.CTkLabel(self.input_frame, text="Source Folder:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ctk.CTkEntry(self.input_frame, textvariable=self.source_dir, width=400).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(self.input_frame, text="Browse", command=self.select_source).grid(row=0, column=2, padx=5, pady=5)

        # Destination
        ctk.CTkLabel(self.input_frame, text="Destination Folder:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ctk.CTkEntry(self.input_frame, textvariable=self.dest_dir, width=400).grid(row=1, column=1, padx=5, pady=5)
        ctk.CTkButton(self.input_frame, text="Browse", command=self.select_dest).grid(row=1, column=2, padx=5, pady=5)

        # === Button Frame ===
        ctk.CTkButton(self.button_frame, text="Run Backup", command=self.run_backup, height=40).pack(pady=10)

        # === Status Frame ===
        self.status_label = ctk.CTkLabel(self.status_frame, text="", text_color="gray")
        self.status_label.pack()

    def load_settings(self):
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    self.source_dir.set(data.get("source_dir", ""))
                    self.dest_dir.set(data.get("dest_dir", ""))
            except Exception as e:
                print(f"Failed to load settings: {e}")

    def save_settings(self):
        data = {
            "source_dir": self.source_dir.get(),
            "dest_dir": self.dest_dir.get()
        }
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def select_source(self):
        path = filedialog.askdirectory()
        if path:
            self.source_dir.set(path)
            self.save_settings()

    def select_dest(self):
        path = filedialog.askdirectory()
        if path:
            self.dest_dir.set(path)
            self.save_settings()

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
            # Create zip
            zip_file = Path(shutil.make_archive(str(temp_zip_path), 'zip', src))

            # Move to destination
            dest_path = dest_base / zip_file.name
            shutil.move(str(zip_file), dest_path)

            # Log success
            with open(log_file, "a") as log:
                log.write(f"[{timestamp}] SUCCESS: {zip_file.name} -> {dest_path}\n")

            self.status_label.configure(text=f"Backup completed: {dest_path}", text_color="green")

        except Exception as e:
            # Log failure
            with open(log_file, "a") as log:
                log.write(f"[{timestamp}] ERROR: {e}\n")

            self.status_label.configure(text=f"Backup failed: {e}", text_color="red")


if __name__ == "__main__":
    app = BackupApp()
    app.mainloop()

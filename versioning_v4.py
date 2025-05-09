import customtkinter as ctk
from tkinter import filedialog
from datetime import datetime
import shutil
from pathlib import Path
import json
import zipfile


# === Settings ===
SETTINGS_FILE = Path("backup_settings.json")

# === App Setup ===
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("dark-blue")


class BackupApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("File Versioning Backup Tool")
        self.geometry("725x300")

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

        self.progress_bar = ctk.CTkProgressBar(self.status_frame, mode="indeterminate")
        self.progress_bar.pack(pady=5, fill="x", padx=10)
        self.progress_bar.stop()  # Start inactive

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

    # Prepare UI
    self.status_label.configure(text="Backing up...", text_color="gray")
    self.progress_bar.configure(mode="determinate", progress_color="blue")
    self.progress_bar.set(0)
    self.update_idletasks()

    self.button_frame.pack_forget()
    self.button_frame.update()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    zip_name = f"backup_{timestamp}.zip"
    zip_path = src.parent / zip_name
    log_file = dest_base / "backup_log.txt"

    try:
        # Count files
        all_files = list(src.rglob('*'))
        total_files = len([f for f in all_files if f.is_file()])
        if total_files == 0:
            raise Exception("No files to back up.")

        current_file = 0

        # Create zip and add files
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in all_files:
                if file.is_file():
                    arcname = file.relative_to(src)
                    zipf.write(file, arcname)
                    current_file += 1
                    progress = current_file / total_files
                    self.progress_bar.set(progress)
                    self.update_idletasks()

        # Move zip to destination
        dest_path = dest_base / zip_path.name
        shutil.move(str(zip_path), dest_path)

        # Log success
        with open(log_file, "a") as log:
            log.write(f"[{timestamp}] SUCCESS: {zip_path.name} -> {dest_path}\n")

        self.status_label.configure(text=f"Backup completed: {dest_path}", text_color="green")

    except Exception as e:
        with open(log_file, "a") as log:
            log.write(f"[{timestamp}] ERROR: {e}\n")

        self.status_label.configure(text=f"Backup failed: {e}", text_color="red")

    # Reset progress bar and re-enable button
    self.progress_bar.set(0)
    self.button_frame.pack(padx=20, pady=10, fill="x")


if __name__ == "__main__":
    app = BackupApp()
    app.mainloop()

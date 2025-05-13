import customtkinter as ctk
from tkinter import filedialog
from datetime import datetime, timedelta
import shutil
from pathlib import Path
import json
import zipfile
import threading
import schedule
import time

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
        self.schedule_var = ctk.StringVar(value="None")
        self.next_backup_time = None

        self.load_settings()
        self.create_widgets()
        self.start_scheduler_thread()
        self.start_countdown_thread()

    def start_scheduler_thread(self):
        def scheduler_loop():
            while True:
                schedule.run_pending()
                time.sleep(1)

        threading.Thread(target=scheduler_loop, daemon=True).start()

    def start_countdown_thread(self):
        def update_countdown():
            while True:
                if self.next_backup_time:
                    now = datetime.now()
                    remaining = self.next_backup_time - now
                    if remaining.total_seconds() > 0:
                        h, rem = divmod(int(remaining.total_seconds()), 3600)
                        m, s = divmod(rem, 60)
                        countdown_text = f"Next backup in: {h:02}:{m:02}:{s:02}"
                    else:
                        countdown_text = "Next backup in: scheduling..."
                else:
                    countdown_text = "Next backup in: --:--:--"

                self.countdown_label.configure(text=countdown_text)
                time.sleep(1)

        threading.Thread(target=update_countdown, daemon=True).start()

    def create_widgets(self):
        # --- Frames ---
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(padx=20, pady=20, fill="x")

        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(padx=20, pady=10, fill="x")

        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.pack(padx=20, pady=10, fill="x")

        # === Input Frame ===
        ctk.CTkLabel(self.input_frame, text="Source Folder:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ctk.CTkEntry(self.input_frame, textvariable=self.source_dir, width=400).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(self.input_frame, text="Browse", command=self.select_source).grid(row=0, column=2, padx=5, pady=5)

        ctk.CTkLabel(self.input_frame, text="Destination Folder:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ctk.CTkEntry(self.input_frame, textvariable=self.dest_dir, width=400).grid(row=1, column=1, padx=5, pady=5)
        ctk.CTkButton(self.input_frame, text="Browse", command=self.select_dest).grid(row=1, column=2, padx=5, pady=5)

        # === Button Frame ===
        ctk.CTkButton(self.button_frame, text="Run Backup", command=self.run_backup, height=40).grid(
            row=0, column=0, pady=5, padx=(125, 10), sticky="ew", columnspan=2)

        ctk.CTkLabel(self.button_frame, text="Auto Backup Interval:").grid(
            row=0, column=2, padx=(10, 5), pady=5, sticky="w")

        ctk.CTkOptionMenu(
            self.button_frame,
            values=["None", "1 minute", "1 hour", "3 hours", "6 hours", "12 hours", "1 day"],
            variable=self.schedule_var,
            command=self.set_schedule
        ).grid(row=0, column=3, padx=(5, 10), pady=5, sticky="ew")

        # === Status Frame ===
        self.status_label = ctk.CTkLabel(self.status_frame, text="", text_color="gray")
        self.status_label.pack()
        self.progress_bar = ctk.CTkProgressBar(self.status_frame, mode="indeterminate")
        self.progress_bar.pack(pady=5, fill="x", padx=10)
        self.progress_bar.stop()

        self.countdown_label = ctk.CTkLabel(self.status_frame, text="Next backup in: --:--:--", text_color="gray")
        self.countdown_label.pack()

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

        self.status_label.configure(text="Backing up...", text_color="gray")
        self.progress_bar.configure(mode="determinate", progress_color="#FFDD57")
        self.progress_bar.set(0)
        self.update_idletasks()
        self.button_frame.pack_forget()
        self.button_frame.update()

        timestamp = datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
        zip_name = f"backup_{timestamp}.zip"
        zip_path = src.parent / zip_name
        log_file = dest_base / "backup_log.txt"

        try:
            all_files = list(src.rglob('*'))
            total_files = len([f for f in all_files if f.is_file()])
            if total_files == 0:
                raise Exception("No files to back up.")

            current_file = 0
            start_time = time.time()

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in all_files:
                    if file.is_file():
                        arcname = file.relative_to(src)
                        zipf.write(file, arcname)
                        current_file += 1

                        progress = current_file / total_files
                        self.progress_bar.set(progress)
                        self.update_idletasks()

            dest_path = dest_base / zip_path.name
            shutil.move(str(zip_path), dest_path)

            with open(log_file, "a") as log:
                log.write(f"[{timestamp}] SUCCESS: {zip_path.name} -> {dest_path}\n")

            self.status_label.configure(text=f"Backup completed: {dest_path}", text_color="#05a7f7")

        except Exception as e:
            with open(log_file, "a") as log:
                log.write(f"[{timestamp}] ERROR: {e}\n")
            self.status_label.configure(text=f"Backup failed: {e}", text_color="red")

        self.progress_bar.set(0)
        self.button_frame.pack(padx=20, pady=10, fill="x")

        # Reset next backup time if a schedule is active
        interval = self.schedule_var.get()
        if interval != "None":
            unit, amount = {
                "1 minute": ("minutes", 1),
                "1 hour": ("hours", 1),
                "3 hours": ("hours", 3),
                "6 hours": ("hours", 6),
                "12 hours": ("hours", 12),
                "1 day": ("hours", 24)
            }.get(interval, (None, None))

            if unit and amount:
                self.set_next_backup_time(amount, unit)

    def set_schedule(self, interval):
        schedule.clear()

        if interval == "None":
            self.next_backup_time = None
            self.status_label.configure(text="Auto backup disabled.", text_color="gray")
            return

        interval_map = {
            "1 minute": ("minutes", 1),
            "1 hour": ("hours", 1),
            "3 hours": ("hours", 3),
            "6 hours": ("hours", 6),
            "12 hours": ("hours", 12),
            "1 day": ("hours", 24)
        }

        unit, amount = interval_map.get(interval, (None, None))

        if unit == "minutes":
            schedule.every(amount).minutes.do(self.threaded_backup)
        elif unit == "hours":
            schedule.every(amount).hours.do(self.threaded_backup)

        self.set_next_backup_time(amount, unit)
        self.status_label.configure(text=f"Auto backup every {interval}.", text_color="gray")

    def set_next_backup_time(self, amount, unit):
        now = datetime.now()
        if unit == "minutes":
            self.next_backup_time = now + timedelta(minutes=amount)
        elif unit == "hours":
            self.next_backup_time = now + timedelta(hours=amount)
        else:
            self.next_backup_time = None

    def threaded_backup(self):
        threading.Thread(target=self.run_backup, daemon=True).start()


if __name__ == "__main__":
    app = BackupApp()
    app.mainloop()

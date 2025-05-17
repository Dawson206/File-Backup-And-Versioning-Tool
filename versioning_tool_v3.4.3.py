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
import sys

# === Settings ===
SETTINGS_FILE = Path("backup_settings.json")

# === App Setup ===
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class BackupApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        try:
            self.iconbitmap(str(self.resource_path("backup_icon.ico")))
        except Exception as e:
            print(f"Icon not set: {e}")

        self.title("FileVault | Backup & Versioning Software | V3.4.3")
        self.geometry("925x300")

        self.source_dir = ctk.StringVar()
        self.dest_dir = ctk.StringVar()
        self.schedule_var = ctk.StringVar(value="None")
        self.max_backups_var = ctk.StringVar(value="5")
        self.next_backup_time = None
        self.backup_lock = threading.Lock()

        self.create_widgets()
        self.load_settings()
        self.start_scheduler_thread()
        self.start_countdown_thread()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def resource_path(self, relative_path):
        try:
            return Path(sys._MEIPASS) / relative_path
        except AttributeError:
            return Path(__file__).parent / relative_path

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
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(padx=20, pady=20, fill="x")

        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.pack(padx=20, pady=10, fill="x")

        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(self.input_frame, text="Source Folder:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ctk.CTkEntry(self.input_frame, textvariable=self.source_dir, width=600).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(self.input_frame, text="Browse", command=self.select_source).grid(row=0, column=2, padx=5, pady=5)

        ctk.CTkLabel(self.input_frame, text="Destination Folder:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ctk.CTkEntry(self.input_frame, textvariable=self.dest_dir, width=600).grid(row=1, column=1, padx=5, pady=5)
        ctk.CTkButton(self.input_frame, text="Browse", command=self.select_dest).grid(row=1, column=2, padx=5, pady=5)

        self.run_backup_button = ctk.CTkButton(
            self.button_frame, text="Run Backup", command=self.run_backup, height=40)
        self.run_backup_button.grid(row=0, column=0, pady=5, padx=(125, 10), sticky="ew", columnspan=2)

        ctk.CTkLabel(self.button_frame, text="Auto Backup Interval:").grid(row=0, column=2, padx=(10, 5), pady=5, sticky="w")

        self.schedule_optionmenu = ctk.CTkOptionMenu(
            self.button_frame,
            values=["None", "1 minute", "5 minutes", "15 minutes", "30 minutes", "1 hour", "3 hours", "6 hours", "12 hours", "1 day"],
            variable=self.schedule_var,
            command=self.set_schedule
        )
        self.schedule_optionmenu.grid(row=0, column=3, padx=(5, 10), pady=5, sticky="ew")

        ctk.CTkLabel(self.button_frame, text="Max Backups:").grid(row=0, column=4, padx=(10, 5), pady=5, sticky="e")
        ctk.CTkOptionMenu(
            self.button_frame,
            values=["Disabled", "1", "3", "5", "10", "20", "50"],
            variable=self.max_backups_var,
            command=lambda _: self.save_settings()
        ).grid(row=0, column=5, padx=(5, 10), pady=5, sticky="w")

        self.status_label = ctk.CTkLabel(self.status_frame, text="", text_color="gray")
        self.status_label.pack()
        self.progress_bar = ctk.CTkProgressBar(self.status_frame, mode="indeterminate")
        self.progress_bar.pack(pady=5, fill="x", padx=10)
        self.progress_bar.stop()

        self.countdown_label = ctk.CTkLabel(self.status_frame, text="Next backup in: --:--:--", text_color="gray")
        self.countdown_label.pack()

        self.update_schedule_state()
        self.update_run_button_state()

    def load_settings(self):
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    self.source_dir.set(data.get("source_dir", ""))
                    self.dest_dir.set(data.get("dest_dir", ""))
                    max_backups = data.get("max_backups", 5)
                    self.max_backups_var.set("Disabled" if max_backups is None else str(max_backups))
                    self.schedule_var.set(data.get("schedule", "None"))
                    self.set_schedule(self.schedule_var.get())
            except Exception as e:
                print(f"Failed to load settings: {e}")

        self.update_schedule_state()
        self.update_run_button_state()

    def save_settings(self):
        try:
            max_backups_value = self.max_backups_var.get()
            max_backups = int(max_backups_value) if max_backups_value != "Disabled" else None

            data = {
                "source_dir": self.source_dir.get(),
                "dest_dir": self.dest_dir.get(),
                "max_backups": max_backups,
                "schedule": self.schedule_var.get()
            }

            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def select_source(self):
        path = filedialog.askdirectory()
        if path:
            self.source_dir.set(path)
            self.update_schedule_state()
            self.update_run_button_state()
            self.save_settings()

    def select_dest(self):
        path = filedialog.askdirectory()
        if path:
            self.dest_dir.set(path)
            self.update_schedule_state()
            self.update_run_button_state()
            self.save_settings()

    def update_schedule_state(self):
        if self.source_dir.get() and self.dest_dir.get():
            self.schedule_optionmenu.configure(state="normal")
        else:
            self.schedule_optionmenu.configure(state="disabled")
            self.schedule_var.set("None")
#            self.save_settings()

    def update_run_button_state(self):
        if self.source_dir.get() and self.dest_dir.get():
            self.run_backup_button.configure(state="normal")
        else:
            self.run_backup_button.configure(state="disabled")

    def run_backup(self):
        if not self.backup_lock.acquire(blocking=False):
            self.status_label.configure(text="Backup already running.", text_color="orange")
            return

        try:
            self.run_backup_button.configure(state="disabled")
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

            timestampfile = datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
            zip_name = f"backup_{timestampfile}.zip"
            zip_path = src.parent / zip_name
            log_file = dest_base / "backup_log.txt"

            try:
                all_files = list(src.rglob('*'))
                file_list = [f for f in all_files if f.is_file()]
                total_files = len(file_list)
                if total_files == 0:
                    raise Exception("No files to back up.")

                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for i, file in enumerate(file_list, start=1):
                        arcname = file.relative_to(src)
                        zipf.write(file, arcname)
                        if i % 10 == 0 or i == total_files:
                            self.progress_bar.set(i / total_files)
                            self.update_idletasks()

                dest_path = dest_base / zip_path.name
                shutil.move(str(zip_path), dest_path)

                self.enforce_backup_rotation()

                with open(log_file, "a") as log:
                    log.write(f"[{timestampfile}] SUCCESS: {zip_path.name} -> {dest_path}\n")

                timestampcompletion = datetime.now().strftime("%m-%d-%Y at %H:%M:%S")
                self.status_label.configure(text=f"Backup completed successfully on {timestampcompletion}.", text_color="#05a7f7")

            except Exception as e:
                with open(log_file, "a") as log:
                    log.write(f"[{timestampfile}] ERROR: {e}\n")
                self.status_label.configure(text=f"Backup failed: {e}", text_color="red")

            self.progress_bar.set(0)
            self.button_frame.pack(padx=20, pady=10, fill="x")
        finally:
            self.run_backup_button.configure(state="normal")
            self.backup_lock.release()

    def enforce_backup_rotation(self):
        dest_base = Path(self.dest_dir.get())
        log_file = dest_base / "backup_log.txt"
        backups = sorted(dest_base.glob("backup_*.zip"), key=lambda f: f.stat().st_mtime)
        max_backups_str = self.max_backups_var.get()

        if max_backups_str == "Disabled":
            return

        try:
            max_backups = int(max_backups_str)
        except ValueError:
            max_backups = 5

        if max_backups == 0:
            return

        if len(backups) > max_backups:
            to_delete = backups[:-max_backups]
            with open(log_file, "a") as log:
                for old_backup in to_delete:
                    try:
                        old_backup.unlink()
                        log.write(f"[{datetime.now().strftime('%m-%d-%Y %H:%M:%S')}] DELETED FOR ROLLOVER: {old_backup.name}\n")
                    except Exception as e:
                        log.write(f"[{datetime.now().strftime('%m-%d-%Y %H:%M:%S')}] DELETE FAILED: {old_backup.name} - {e}\n")

    def set_schedule(self, interval):
        schedule.clear()
        interval = self.schedule_var.get()
        interval_map = {
            "None": (None, None),
            "1 minute": ("minutes", 1),
            "5 minutes": ("minutes", 5),
            "15 minutes": ("minutes", 15),
            "30 minutes": ("minutes", 30),
            "1 hour": ("hours", 1),
            "3 hours": ("hours", 3),
            "6 hours": ("hours", 6),
            "12 hours": ("hours", 12),
            "1 day": ("hours", 24)
        }

        unit, amount = interval_map.get(interval, (None, None))

        if unit is None or amount is None:
            self.next_backup_time = None
            self.status_label.configure(text="Auto backup disabled.", text_color="gray")
            self.save_settings()
            return

        if unit == "minutes":
            schedule.every(amount).minutes.do(self.threaded_backup)
        elif unit == "hours":
            schedule.every(amount).hours.do(self.threaded_backup)

        self.set_next_backup_time(amount, unit)
        self.status_label.configure(text=f"Auto backup every {interval}.", text_color="gray")
        self.save_settings()

    def set_next_backup_time(self, amount, unit):
        now = datetime.now()
        if unit == "minutes":
            self.next_backup_time = now + timedelta(minutes=amount)
        elif unit == "hours":
            self.next_backup_time = now + timedelta(hours=amount)
        else:
            self.next_backup_time = None

    def threaded_backup(self):
        def backup_and_update_time():
            self.run_backup()
            interval = self.schedule_var.get()
            interval_map = {
                "1 minute": ("minutes", 1),
                "5 minutes": ("minutes", 5),
                "15 minutes": ("minutes", 15),
                "30 minutes": ("minutes", 30),
                "1 hour": ("hours", 1),
                "3 hours": ("hours", 3),
                "6 hours": ("hours", 6),
                "12 hours": ("hours", 12),
                "1 day": ("hours", 24)
            }

            unit, amount = interval_map.get(interval, (None, None))
            if unit and amount:
                self.set_next_backup_time(amount, unit)

        threading.Thread(target=backup_and_update_time, daemon=True).start()

    def on_closing(self):
        self.save_settings()
        self.destroy()

if __name__ == "__main__":
    app = BackupApp()
    app.mainloop()

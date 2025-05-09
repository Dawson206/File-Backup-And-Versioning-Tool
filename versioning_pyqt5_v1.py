from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QFileDialog, QVBoxLayout, QHBoxLayout, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer
from pathlib import Path
from datetime import datetime
import zipfile, shutil, json, sys
import qdarkstyle


SETTINGS_FILE = Path("backup_settings.json")


class BackupApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Versioning Backup Tool")
        self.setFixedSize(725, 300)

        self.source_dir = ""
        self.dest_dir = ""

        self.load_settings()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # --- Source Path ---
        src_layout = QHBoxLayout()
        src_layout.addWidget(QLabel("Source Folder:"))
        self.src_input = QLineEdit(self.source_dir)
        src_layout.addWidget(self.src_input)
        browse_src = QPushButton("Browse")
        browse_src.clicked.connect(self.select_source)
        src_layout.addWidget(browse_src)
        layout.addLayout(src_layout)

        # --- Destination Path ---
        dest_layout = QHBoxLayout()
        dest_layout.addWidget(QLabel("Destination Folder:"))
        self.dest_input = QLineEdit(self.dest_dir)
        dest_layout.addWidget(self.dest_input)
        browse_dest = QPushButton("Browse")
        browse_dest.clicked.connect(self.select_dest)
        dest_layout.addWidget(browse_dest)
        layout.addLayout(dest_layout)

        # --- Run Button ---
        self.run_button = QPushButton("Run Backup")
        self.run_button.clicked.connect(self.run_backup)
        layout.addWidget(self.run_button, alignment=Qt.AlignCenter)

        # --- Status ---
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # --- Progress Bar ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

    def load_settings(self):
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    self.source_dir = data.get("source_dir", "")
                    self.dest_dir = data.get("dest_dir", "")
            except Exception as e:
                print(f"Settings load error: {e}")

    def save_settings(self):
        data = {
            "source_dir": self.src_input.text(),
            "dest_dir": self.dest_input.text()
        }
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Settings save error: {e}")

    def select_source(self):
        path = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if path:
            self.src_input.setText(path)
            self.save_settings()

    def select_dest(self):
        path = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if path:
            self.dest_input.setText(path)
            self.save_settings()

    def run_backup(self):
        src = Path(self.src_input.text())
        dest_base = Path(self.dest_input.text())
        self.save_settings()

        if not src.exists() or not dest_base.exists():
            self.status_label.setText("Invalid folder paths.")
            self.status_label.setStyleSheet("color: red;")
            return

        self.status_label.setText("Backing up...")
        self.status_label.setStyleSheet("color: gray;")
        self.progress_bar.setValue(0)
        QApplication.processEvents()

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        zip_name = f"backup_{timestamp}.zip"
        zip_path = src.parent / zip_name
        log_file = dest_base / "backup_log.txt"

        try:
            all_files = list(src.rglob('*'))
            total_files = len([f for f in all_files if f.is_file()])
            if total_files == 0:
                raise Exception("No files to back up.")

            current_file = 0
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in all_files:
                    if file.is_file():
                        arcname = file.relative_to(src)
                        zipf.write(file, arcname)
                        current_file += 1
                        self.progress_bar.setValue(int((current_file / total_files) * 100))
                        QApplication.processEvents()

            dest_path = dest_base / zip_path.name
            shutil.move(str(zip_path), dest_path)

            with open(log_file, "a") as log:
                log.write(f"[{timestamp}] SUCCESS: {zip_path.name} -> {dest_path}\n")

            self.status_label.setText(f"Backup completed: {dest_path}")
            self.status_label.setStyleSheet("color: blue;")

        except Exception as e:
            with open(log_file, "a") as log:
                log.write(f"[{timestamp}] ERROR: {e}\n")

            self.status_label.setText(f"Backup failed: {e}")
            self.status_label.setStyleSheet("color: red;")

        self.progress_bar.setValue(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())  # Apply dark theme
    window = BackupApp()
    window.show()
    sys.exit(app.exec_())

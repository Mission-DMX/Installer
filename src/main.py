# coding=utf-8
"""update routine for Project-Editor"""
import argparse
import os
import subprocess
import sys
from logging import getLogger

import requests
from PySide6.QtWidgets import QProgressDialog, QApplication, QMessageBox

logger = getLogger(__name__)

__VERSION__ = "0.5.0"
software_parts = ["Fish", "Project-Editor"]
base_dir = os.path.join(os.sep, "opt", "mission-dmx")


def read_current_version(software_part: str) -> str:
    """read current version from File"""
    try:
        with open((os.path.join(base_dir, f"{software_part}_version.txt"))) as f:
            return f.read().strip()
    except:
        return ""


def get_latest_release_info(software_part: str) -> tuple[str, str | None]:
    """get latest release from GitHub"""
    url = f"https://api.github.com/repos/Mission-DMX/{software_part}/releases/latest"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        tag = data["tag_name"]
        asset = next((a for a in data["assets"] if "Project-Editor" in a["name"]), None)
        return tag, asset["browser_download_url"] if asset else None
    return None, None


def download_with_progress(url, dest_path, parent):
    """download file from url to dest_path with progress Window"""
    response = requests.get(url, stream=True)
    total = int(response.headers.get('content-length', 0))

    progress = QProgressDialog("Lade Update herunter...", "Abbrechen", 0, 100, parent)
    progress.setWindowTitle(f"Installer v{__VERSION__}")
    progress.show()
    with open(dest_path, 'wb') as f:
        downloaded = 0
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                percent = int((downloaded / total) * 100)
                progress.setValue(percent)
                QApplication.processEvents()
                if progress.wasCanceled():
                    os.remove(dest_path)
                    return False
    progress.close()
    os.chmod(dest_path, 0o755)
    return True


def run_updater(url: str, software_part: str, latest_version: str, existing: bool) -> None:
    """Run update"""
    path = os.path.join(base_dir, software_part)
    if existing:
        path += "_new"

    if not download_with_progress(url, path, None):
        QMessageBox.warning(None, "Fehler", "Update fehlgeschlagen.")
        return

    if existing:
        os.rename(path, path[:-4])

    with open(f"{path}_version.txt", "w") as f:
        f.write(latest_version)


def check_update(software_part: str) -> tuple[str, str, str]:
    """check if update of software part is needed"""
    current_version = read_current_version(software_part)
    latest_version, url = get_latest_release_info(software_part)

    if not latest_version or not url:
        return "", "", ""
    if latest_version == current_version:
        return "", "", ""

    return current_version, latest_version, url


def run_complete_update():
    """run a complete Update"""
    for software_part in software_parts:
        current_version, latest_version, url = check_update(software_part)

        if latest_version:
            if current_version:
                reply = QMessageBox.question(None, "Update verfügbar",
                                             f"Eine neue Version von {software_part} mit Version {latest_version} ist verfügbar."
                                             "\nMöchtest du jetzt aktualisieren?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

                if reply == QMessageBox.StandardButton.Yes:
                    run_updater(url, software_part, latest_version, True)
            else:
                run_updater(url, software_part, latest_version, False)


def main():
    """run Installer"""
    arguments = parse_arguments()

    if not arguments.check:
        run_complete_update()
        for software in software_parts:
            path = os.path.join(base_dir, software)
            if os.path.isfile(path):
                subprocess.Popen(path)
    else:
        for software in software_parts:
            if check_update(software)[1]:
                print(f"{software} need Update.")

    if arguments.install:
        desktop_file = os.path.join(os.path.expanduser("~"), ".local", "share", "applications", "Lichtpult.desktop")
        with open(desktop_file, 'w') as file:
            file.write("""[Desktop Entry]
            Name=Lichtpult
            Comment=Lichtpult
            Exec=/opt/mission-dmx/Installer
            Terminal=false
            Type=Application
            Categories=Utility;"""
                       )

        # Datei ausführbar machen
        os.chmod(desktop_file, 0o755)

    sys.exit(0)


def parse_arguments() -> argparse.Namespace:
    """
    Parse the start Parameters
    :return: parsed arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--install", action="store_true")

    arg_data = parser.parse_args()

    return arg_data


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main()
    sys.exit(app.exec())

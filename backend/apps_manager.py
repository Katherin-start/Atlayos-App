import os
import platform
import subprocess
from datetime import datetime
import psutil
import json
import shutil
from typing import List, Dict, Union, Optional

# Importación condicional de winreg
if platform.system() == "Windows":
    import winreg
else:
    winreg = None

class AppsManager:
    def __init__(self):
        self.system = platform.system()

    def get_installed_apps(self) -> List[Dict[str, Union[str, int]]]:
        apps = []
        if self.system == "Windows" and winreg:
            apps = self._get_windows_apps()
            apps += self._get_uwp_apps()
        elif self.system == "Linux":
            apps = self._get_linux_apps()
        elif self.system == "Darwin":
            apps = self._get_macos_apps()
        for app in apps:
            app['size_mb'] = app.get('size', 0) // (1024 * 1024)
        return apps

    def get_largest_apps(self, threshold_mb: int = 1024) -> List[Dict[str, Union[str, int]]]:
        return [app for app in self.get_installed_apps() if app.get("size_mb", 0) > threshold_mb]

    def uninstall_app(self, app_name: str) -> dict:
        if self.system == "Windows":
            return self._uninstall_windows_app(app_name)
        elif self.system == "Linux":
            return self._uninstall_linux_app(app_name)
        elif self.system == "Darwin":
            return self._uninstall_macos_app(app_name)
        return {"success": False, "message": "Sistema operativo no soportado para desinstalación."}

    def _get_windows_apps(self) -> List[Dict[str, Union[str, int]]]:
        if not winreg:
            return []
        apps = []
        reg_paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        ]
        for reg_path in reg_paths:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            app = self._parse_windows_app(subkey)
                            if app and app not in apps:
                                apps.append(app)
            except Exception:
                continue
        return apps

    def _parse_windows_app(self, subkey) -> Optional[Dict[str, Union[str, int]]]:
        def safe_query(key, value, default=""):
            try:
                return winreg.QueryValueEx(key, value)[0]
            except Exception:
                return default
        name = safe_query(subkey, "DisplayName")
        if not name:
            return None
        version = safe_query(subkey, "DisplayVersion", "N/A")
        try:
            size = int(safe_query(subkey, "EstimatedSize", 0)) * 1024
        except:
            size = 0
        return {
            "name": name,
            "version": version,
            "size": size,
            "install_date": datetime.now().strftime("%Y-%m-%d"),
            "system": "Windows"
        }

    def _get_uwp_apps(self) -> List[Dict[str, Union[str, int]]]:
        if self.system != "Windows":
            return []
        apps = []
        try:
            cmd = [
                "powershell",
                "-Command",
                "Get-AppxPackage | Select Name, PackageFullName | ConvertTo-Json"
            ]
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
            uwp_list = json.loads(output)
            if isinstance(uwp_list, dict):
                uwp_list = [uwp_list]
            for app in uwp_list:
                apps.append({
                    "name": app.get("Name", "N/A"),
                    "version": app.get("PackageFullName", "N/A"),
                    "size": 0,
                    "install_date": "N/A",
                    "system": "Windows (UWP)"
                })
        except Exception:
            pass
        return apps

    def _uninstall_windows_app(self, app_name: str) -> Dict[str, Union[bool, str]]:
        return {"success": False, "message": "Función de desinstalación para Windows no implementada."}

    def _get_linux_apps(self) -> List[Dict[str, Union[str, int]]]:
        apps = []
        try:
            output = subprocess.check_output(
                ["dpkg-query", "-W", "-f=${Package}\t${Version}\t${Installed-Size}\t${Status}\n"],
                stderr=subprocess.DEVNULL
            ).decode("utf-8")
            for line in output.splitlines():
                parts = line.split("\t")
                if len(parts) >= 4 and "installed" in parts[3]:
                    apps.append({
                        "name": parts[0],
                        "version": parts[1],
                        "size": int(parts[2]) * 1024,
                        "install_date": "N/A",
                        "system": "Linux"
                    })
        except:
            pass
        return apps

    def _uninstall_linux_app(self, app_name: str) -> Dict[str, Union[bool, str]]:
        try:
            process = subprocess.run([
                "sudo", "apt-get", "remove", "-y", app_name
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if process.returncode == 0:
                return {"success": True, "message": f"{app_name} desinstalado correctamente."}
            return {"success": False, "message": process.stderr}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _get_macos_apps(self) -> List[Dict[str, Union[str, int]]]:
        apps = []
        try:
            for app in os.listdir("/Applications"):
                if app.endswith(".app"):
                    path = os.path.join("/Applications", app)
                    size = self._get_folder_size(path)
                    apps.append({
                        "name": app.replace(".app", ""),
                        "version": "N/A",
                        "size": size,
                        "install_date": "N/A",
                        "system": "macOS"
                    })
        except:
            pass
        return apps

    def _uninstall_macos_app(self, app_name: str) -> Dict[str, Union[bool, str]]:
        try:
            path = f"/Applications/{app_name}.app"
            if os.path.exists(path):
                trash_path = os.path.expanduser("~/.Trash/")
                shutil.move(path, trash_path)
                return {"success": True, "message": f"{app_name} movida a la Papelera."}
            return {"success": False, "message": f"{app_name} no encontrada."}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _get_folder_size(self, path: str) -> int:
        total = 0
        if not os.path.exists(path):
            return 0
        for entry in os.scandir(path):
            try:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self._get_folder_size(entry.path)
            except:
                continue
        return total

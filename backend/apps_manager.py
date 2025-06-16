import os
import platform
import subprocess
from datetime import datetime
import psutil
import winreg
import json
import shutil
from typing import List, Dict, Union, Optional

class AppsManager:
    def __init__(self):
        self.system = platform.system()

    # --- Métodos principales ---

    def get_installed_apps(self) -> List[Dict[str, Union[str, int]]]:
        """Obtiene todas las aplicaciones instaladas en el sistema."""
        apps = []
        if self.system == "Windows":
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
        """Devuelve aplicaciones que superen el umbral de tamaño especificado."""
        apps = self.get_installed_apps()
        return [app for app in apps if app.get("size_mb", 0) > threshold_mb]

    def uninstall_app(self, app_name: str) -> dict:
        system = self.system
        if system == "Windows":
            return self._uninstall_windows_app(app_name)
        elif system == "Linux":
            return self._uninstall_linux_app(app_name)
        elif system == "Darwin":
            return self._uninstall_macos_app(app_name)
        else:
            return {"success": False, "message": "Sistema operativo no soportado para desinstalación."}

    def clean_app_cache(self, app_name: str) -> Dict[str, Union[bool, str, int]]:
        """Limpia la caché y datos residuales de una aplicación."""
        freed_space = 0
        message = ""
        if self.system == "Windows":
            cache_paths = [
                os.path.join(os.getenv("LOCALAPPDATA") or "", app_name),
                os.path.join(os.getenv("APPDATA") or "", app_name),
                os.path.join(os.getenv("TEMP") or "", app_name)
            ]
            for path in cache_paths:
                if os.path.exists(path):
                    try:
                        size = self._get_folder_size(path)
                        shutil.rmtree(path)
                        freed_space += size
                        message += f"Eliminado {path}. "
                    except Exception as e:
                        message += f"Error al eliminar {path}: {str(e)}. "
        elif self.system == "Linux":
            try:
                subprocess.run(["sudo", "apt-get", "clean"], check=True)
                subprocess.run(["sudo", "apt-get", "autoremove", "-y"], check=True)
                user = os.getenv("USER") or ""
                app_cache = f"/home/{user}/.cache/{app_name}"
                if os.path.exists(app_cache):
                    size = self._get_folder_size(app_cache)
                    shutil.rmtree(app_cache)
                    freed_space += size
                    message += f"Eliminado caché en {app_cache}. "
                message += "Caché del sistema limpiada. "
            except subprocess.CalledProcessError as e:
                return {"success": False, "message": f"Error al limpiar caché: {str(e)}", "freed_space": 0}
        elif self.system == "Darwin":
            try:
                app_cache = os.path.expanduser(f"~/Library/Caches/{app_name}")
                if os.path.exists(app_cache):
                    size = self._get_folder_size(app_cache)
                    shutil.rmtree(app_cache)
                    freed_space += size
                    message += f"Eliminado caché en {app_cache}. "
                prefs_dir = os.path.expanduser("~/Library/Preferences/")
                for fname in os.listdir(prefs_dir):
                    if fname.startswith(app_name):
                        try:
                            os.remove(os.path.join(prefs_dir, fname))
                            message += f"Preferencias eliminadas: {fname}. "
                        except Exception as e:
                            message += f"Error al eliminar preferencias {fname}: {str(e)}. "
            except Exception as e:
                return {"success": False, "message": f"Error al limpiar caché: {str(e)}", "freed_space": 0}
        return {
            "success": True,
            "message": message or "No se encontró caché para limpiar",
            "freed_space": freed_space // (1024 * 1024)
        }

    def check_disk_alerts(self, size_threshold_mb: int = 1024) -> Dict[str, Union[bool, List, str]]:
        """Verifica alertas de espacio en disco y aplicaciones grandes."""
        result = {
            "has_alerts": False,
            "large_apps": self.get_largest_apps(size_threshold_mb),
            "message": "",
            "disk_usage": self.get_disk_usage()
        }
        if result["large_apps"]:
            result["has_alerts"] = True
            app_names = ", ".join([app["name"] for app in result["large_apps"]])
            result["message"] += (
                f"Aplicaciones grandes (> {size_threshold_mb}MB): {app_names}. "
                f"Se recomienda desinstalar alguna de estas aplicaciones para liberar espacio. "
            )
        disk_usage = result["disk_usage"]
        if disk_usage["percent_used"] > 90:
            result["has_alerts"] = True
            result["message"] += f"¡Alerta! Disco {disk_usage['mountpoint']} con {disk_usage['percent_used']}% usado. "
        if not result["message"]:
            result["message"] = "No se encontraron alertas de espacio."
        return result

    def get_disk_usage(self) -> Dict[str, Union[str, float, int]]:
        """Obtiene información de uso del disco principal."""
        try:
            disk = psutil.disk_usage('/')
            return {
                "mountpoint": "/",
                "total_gb": disk.total // (1024**3),
                "used_gb": disk.used // (1024**3),
                "free_gb": disk.free // (1024**3),
                "percent_used": disk.percent
            }
        except:
            return {
                "mountpoint": "N/A",
                "total_gb": 0,
                "used_gb": 0,
                "free_gb": 0,
                "percent_used": 0
            }

    def is_laptop_connected(self) -> Optional[bool]:
        """Verifica si la laptop está conectada a corriente."""
        try:
            battery = psutil.sensors_battery()
            return battery.power_plugged if battery else None
        except:
            return None

    def export_to_json(self, file_path: str) -> Dict[str, Union[bool, str]]:
        """Exporta la información de apps y disco a un archivo JSON."""
        try:
            with open(file_path, "w") as f:
                json.dump(
                    {
                        "system": self.system,
                        "timestamp": datetime.now().isoformat(),
                        "disk_usage": self.get_disk_usage(),
                        "apps": self.get_installed_apps(),
                        "large_apps": self.get_largest_apps()
                    },
                    f,
                    indent=2
                )
            return {"success": True, "message": f"Datos exportados a {file_path}"}
        except Exception as e:
            return {"success": False, "message": f"Error al exportar: {str(e)}"}

    # --- Métodos internos por sistema ---

    # Windows
    def _get_windows_apps(self) -> List[Dict[str, Union[str, int]]]:
        """Obtiene aplicaciones instaladas en Windows desde el registro."""
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
            except Exception as e:
                print(f"Error reading registry {reg_path}: {e}")
        return apps

    def _parse_windows_app(self, subkey) -> Optional[Dict[str, Union[str, int]]]:
        """Parsea la información de una aplicación desde el registro de Windows de forma segura."""
        def safe_query(key, value, default=""):
            try:
                return winreg.QueryValueEx(key, value)[0]
            except FileNotFoundError:
                return default
            except Exception:
                return default
        name = safe_query(subkey, "DisplayName")
        if not name:
            return None
        version = safe_query(subkey, "DisplayVersion", "N/A")
        try:
            size = int(safe_query(subkey, "EstimatedSize", 0)) * 1024
        except Exception:
            size = 0
        install_date = safe_query(subkey, "InstallDate")
        uninstall_string = safe_query(subkey, "UninstallString")
        modify_path = safe_query(subkey, "ModifyPath")
        return {
            "name": name,
            "version": version,
            "size": size,
            "install_date": self._parse_windows_install_date(install_date) if install_date else datetime.now().strftime("%Y-%m-%d"),
            "uninstall_string": uninstall_string,
            "modify_path": modify_path,
            "system": "Windows"
        }

    def _parse_windows_install_date(self, date_str: str) -> str:
        """Convierte la fecha de instalación de Windows a formato estándar."""
        try:
            if len(date_str) == 8 and date_str.isdigit():
                return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except:
            pass
        return datetime.now().strftime("%Y-%m-%d")

    def _get_uwp_apps(self) -> List[Dict[str, Union[str, int]]]:
        """Obtiene aplicaciones UWP (Microsoft Store) usando PowerShell."""
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
        except Exception as e:
            print(f"Error obteniendo apps UWP: {e}")
        return apps

    def _uninstall_windows_app(self, app_name: str) -> Dict[str, Union[bool, str]]:
        apps = self.get_installed_apps()
        app = next((a for a in apps if a["name"].lower() == app_name.lower()), None)
        if not app:
            return {"success": False, "message": f"No se encontró {app_name} en la lista de aplicaciones."}
        if app.get("system") == "Windows (UWP)":
            package_full_name = app.get("version")
            if not package_full_name or package_full_name == "N/A":
                return {"success": False, "message": f"No se encontró el identificador de paquete para {app_name}."}
            try:
                cmd = [
                    "powershell",
                    "-Command",
                    f"Remove-AppxPackage -Package \"{package_full_name}\""
                ]
                process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if process.returncode == 0:
                    return {"success": True, "message": f"{app_name} desinstalado correctamente (UWP)."}
                else:
                    return {"success": False, "message": f"Error al desinstalar {app_name}: {process.stderr or process.stdout}"}
            except Exception as e:
                return {"success": False, "message": f"Error inesperado: {str(e)}"}
        uninstall_cmd = app.get("uninstall_string") or app.get("modify_path")
        if not uninstall_cmd:
            return {
                "success": False,
                "message": (
                    f"No se encontró comando de desinstalación para {app_name}. "
                    "Intenta desde el Panel de control o usa una herramienta como Revo Uninstaller."
                )
            }
        try:
            print(f"Comando de desinstalación para {app_name}: {uninstall_cmd}")
            process = subprocess.run(uninstall_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if process.returncode == 0:
                return {"success": True, "message": f"{app_name} desinstalado correctamente."}
            else:
                return {"success": False, "message": f"Error al desinstalar {app_name}: {process.stderr or process.stdout}"}
        except Exception as e:
            return {"success": False, "message": f"Error inesperado: {str(e)}"}

    # Linux
    def _get_linux_apps(self) -> List[Dict[str, Union[str, int]]]:
        """Obtiene aplicaciones instaladas en Linux (Debian/Ubuntu)."""
        apps = []
        try:
            output = subprocess.check_output(
                ["dpkg-query", "-W", "-f=${Package}\t${Version}\t${Installed-Size}\t${Status}\n"],
                stderr=subprocess.DEVNULL
            ).decode("utf-8")
            for line in output.splitlines():
                parts = line.split("\t")
                if len(parts) >= 3 and "installed" in parts[3]:
                    apps.append({
                        "name": parts[0],
                        "version": parts[1],
                        "size": int(parts[2]) * 1024,
                        "install_date": self._get_linux_install_date(parts[0]),
                        "system": "Linux"
                    })
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return apps

    def _get_linux_install_date(self, package_name: str) -> str:
        """Obtiene la fecha de instalación de un paquete en Linux."""
        try:
            output = subprocess.check_output(
                ["stat", "-c", "%y", f"/var/lib/dpkg/info/{package_name}.list"],
                stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
            return output.split(".")[0]
        except:
            return "N/A"

    def _uninstall_linux_app(self, app_name: str) -> Dict[str, Union[bool, str]]:
        """Desinstala una aplicación en Linux usando apt-get remove."""
        try:
            process = subprocess.run(
                ["sudo", "apt-get", "remove", "-y", app_name],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            if process.returncode == 0:
                return {"success": True, "message": f"{app_name} desinstalado correctamente."}
            else:
                return {"success": False, "message": f"Error al desinstalar {app_name}: {process.stderr or process.stdout}"}
        except Exception as e:
            return {"success": False, "message": f"Error inesperado: {str(e)}"}

    # macOS
    def _get_macos_apps(self) -> List[Dict[str, Union[str, int]]]:
        """Obtiene aplicaciones instaladas en macOS."""
        apps = []
        try:
            for app in os.listdir("/Applications"):
                if app.endswith(".app"):
                    app_path = os.path.join("/Applications", app)
                    app_name = app.replace(".app", "")
                    size = self._get_folder_size(app_path)
                    apps.append({
                        "name": app_name,
                        "version": self._get_macos_app_version(app_path),
                        "size": size,
                        "install_date": self._get_macos_install_date(app_path),
                        "system": "macOS"
                    })
        except Exception as e:
            print(f"Error getting macOS apps: {e}")
        return apps

    def _get_macos_app_version(self, app_path: str) -> str:
        """Obtiene la versión de una aplicación en macOS."""
        try:
            info_plist = os.path.join(app_path, "Contents", "Info.plist")
            if os.path.exists(info_plist):
                version = subprocess.check_output(
                    ["defaults", "read", info_plist, "CFBundleShortVersionString"],
                    stderr=subprocess.DEVNULL
                ).decode("utf-8").strip()
                return version if version else "N/A"
        except:
            pass
        return "N/A"

    def _get_macos_install_date(self, app_path: str) -> str:
        """Obtiene la fecha de instalación de una aplicación en macOS."""
        try:
            stat = os.stat(app_path)
            return datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
        except:
            return "N/A"

    def _uninstall_macos_app(self, app_name: str) -> Dict[str, Union[bool, str]]:
        """Desinstala una aplicación en macOS moviéndola a la Papelera."""
        try:
            app_path = f"/Applications/{app_name}.app"
            if os.path.exists(app_path):
                trash_path = os.path.expanduser("~/.Trash/")
                shutil.move(app_path, trash_path)
                return {"success": True, "message": f"{app_name} movida a la Papelera."}
            else:
                return {"success": False, "message": f"No se encontró {app_name} en /Applications."}
        except Exception as e:
            return {"success": False, "message": f"Error inesperado: {str(e)}"}

    # --- Utilidades ---

    def _get_folder_size(self, path: str) -> int:
        """Calcula el tamaño total de un directorio en bytes."""
        total = 0
        if not os.path.exists(path):
            return 0
        for entry in os.scandir(path):
            try:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self._get_folder_size(entry.path)
            except Exception:
                continue
        return total

# --- Funciones de compatibilidad ---

def get_installed_apps() -> List[Dict[str, Union[str, int]]]:
    """Función independiente para compatibilidad."""
    return AppsManager().get_installed_apps()

def get_large_apps(threshold_mb: int = 1024) -> List[Dict[str, Union[str, int]]]:
    """Función independiente para compatibilidad."""
    return AppsManager().get_largest_apps(threshold_mb)

def uninstall_app(app_name: str, remove_data: bool = False) -> Dict[str, Union[bool, str]]:
    """Función independiente para compatibilidad."""
    return AppsManager().uninstall_app(app_name)

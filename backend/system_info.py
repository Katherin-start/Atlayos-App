import psutil
import time
import platform
import subprocess
import os
import logging
from functools import lru_cache
import contextlib
import json
from typing import Dict, List, Tuple, Union, Optional

# Configuración avanzada de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('system_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SystemInfo')

# Constantes
TIMEOUT_COMMANDS = 3
CACHE_TTL = 300
DEFAULT_TEMP = 0.0
DEFAULT_THRESHOLDS = {
    'cpu': 90,
    'memory': 90,
    'disk': 95,
    'temperature': 85
}

class SystemInfoError(Exception):
    """Excepción personalizada para errores del sistema"""
    pass

def _run_command(cmd: Union[str, List[str]], timeout: int = TIMEOUT_COMMANDS) -> Optional[str]:
    """Ejecuta un comando y devuelve su salida"""
    try:
        result = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception as e:
        logger.debug(f"Comando fallido {cmd}: {str(e)}")
        return None

@lru_cache(maxsize=1)
def get_system_model() -> str:
    """Obtiene el modelo del sistema con caché"""
    try:
        system = platform.system()
        
        if system == "Windows":
            model = _run_command('wmic csproduct get name')
            if model and not any(x in model.lower() for x in ['name', 'to be filled']):
                return model.split('\n')[-1].strip()
            
            model = _run_command(['powershell', '(Get-CimInstance -ClassName Win32_ComputerSystem).Model'])
            if model:
                return model
                
        elif system == "Linux":
            if os.path.exists('/sys/class/dmi/id/product_name'):
                with open('/sys/class/dmi/id/product_name', 'r') as f:
                    model = f.read().strip()
                    if model:
                        return model
            
            model = _run_command(['dmidecode', '-s', 'system-product-name'])
            if model:
                return model
                
            lshw_output = _run_command(['lshw', '-json'])
            if lshw_output:
                try:
                    hw_data = json.loads(lshw_output)
                    return hw_data.get('product', '') if isinstance(hw_data, dict) else hw_data[0].get('product', '')
                except json.JSONDecodeError:
                    pass
                    
        elif system == "Darwin":
            model = _run_command(['sysctl', '-n', 'hw.model'])
            return model if model else "Mac"
        
        return platform.node() or "Desconocido"
        
    except Exception as e:
        logger.error(f"Error en get_system_model: {str(e)}", exc_info=True)
        return "Desconocido"

@lru_cache(maxsize=1)
def get_os_info() -> Dict[str, str]:
    """Obtiene información del sistema operativo"""
    try:
        system = platform.system()
        os_info = {
            'os_name': system,
            'os_version': platform.release(),
            'system': system,
            'release': platform.release(),
            'version': platform.version(),
            'architecture': platform.machine(),
        }
        
        if system == "Windows":
            os_info['os_name'] = "Windows"
            try:
                os_info['os_version'] = platform.win32_ver()[0]
            except Exception:
                pass
                
        elif system == "Linux":
            if os.path.exists('/etc/os-release'):
                try:
                    os_release = {}
                    with open('/etc/os-release') as f:
                        for line in f:
                            if '=' in line:
                                parts = line.strip().split('=', 1)
                                if len(parts) == 2:
                                    key, value = parts
                                    os_release[key.lower()] = value.strip('"')
                    
                    if 'pretty_name' in os_release:
                        os_info['os_name'] = os_release['pretty_name']
                    elif 'name' in os_release:
                        os_info['os_name'] = os_release['name']
                        
                    if 'version_id' in os_release:
                        os_info['os_version'] = os_release['version_id']
                except Exception as e:
                    logger.debug(f"No se pudo leer /etc/os-release: {str(e)}")
            
            lsb_info = _run_command(['lsb_release', '-d'])
            if lsb_info:
                os_info['os_name'] = lsb_info.split(':', 1)[1].strip()
                
        elif system == "Darwin":
            os_info['os_name'] = "macOS"
            try:
                os_info['os_version'] = platform.mac_ver()[0]
            except Exception:
                pass
                
        return os_info
        
    except Exception as e:
        logger.error(f"Error en get_os_info: {str(e)}", exc_info=True)
        return {
            'os_name': platform.system(),
            'os_version': platform.release(),
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'architecture': platform.machine()
        }

def kill_process(pid: int) -> Tuple[bool, str]:
    """Intenta terminar un proceso por su PID"""
    try:
        process = psutil.Process(pid)
        process.terminate()
        return True, f"Proceso {pid} terminado correctamente."
    except psutil.NoSuchProcess:
        return False, f"El proceso {pid} no existe."
    except psutil.AccessDenied:
        return False, f"No tienes permisos para terminar el proceso {pid}."
    except Exception as e:
        logger.error(f"Error al terminar proceso {pid}: {str(e)}", exc_info=True)
        return False, f"Error al terminar el proceso {pid}: {str(e)}"

def get_system_info() -> Dict[str, Union[dict, list, float, int, str]]:
    """Obtiene información completa del sistema"""
    try:
        # Información de CPU
        cpu_info = {
            'percent': psutil.cpu_percent(interval=1),
            'count': psutil.cpu_count(logical=True),
            'cores': psutil.cpu_count(logical=False),
            'frequency': psutil.cpu_freq().current if hasattr(psutil, 'cpu_freq') and psutil.cpu_freq() else 0,
            'temperature': _get_cpu_temperature(),
            'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else [0.0, 0.0, 0.0]
        }
        
        # Información de memoria
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        memory_info = {
            'total': mem.total,
            'available': mem.available,
            'used': mem.used,
            'free': mem.free,
            'percent': mem.percent,
            'swap_total': swap.total,
            'swap_used': swap.used,
            'swap_free': swap.free,
            'swap_percent': swap.percent
        }
        
        # Información de disco
        disk = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()
        disk_info = {
            'total': disk.total,
            'used': disk.used,
            'free': disk.free,
            'percent': disk.percent,
            'read_bytes': disk_io.read_bytes if disk_io else 0,
            'write_bytes': disk_io.write_bytes if disk_io else 0
        }
        
        # Información de red
        net_io = psutil.net_io_counters()
        network_info = {
            'bytes_sent': net_io.bytes_sent if net_io else 0,
            'bytes_recv': net_io.bytes_recv if net_io else 0,
            'packets_sent': net_io.packets_sent if net_io else 0,
            'packets_recv': net_io.packets_recv if net_io else 0
        }
        
        # Procesos
        processes_info = _get_processes_info()
        
        return {
            'cpu': cpu_info,
            'memory': memory_info,
            'disk': disk_info,
            'network': network_info,
            'processes': processes_info,
            'boot_time': psutil.boot_time(),
            'timestamp': time.time(),
            'system_model': get_system_model(),
            'os_info': get_os_info(),
            'thresholds': DEFAULT_THRESHOLDS  # Incluir umbrales por defecto
        }
        
    except Exception as e:
        logger.error(f"Error crítico en get_system_info: {str(e)}", exc_info=True)
        # Retornar estructura mínima con valores por defecto
        return {
            'cpu': {
                'percent': 0,
                'count': 0,
                'cores': 0,
                'frequency': 0,
                'temperature': DEFAULT_TEMP,
                'load_avg': [0.0, 0.0, 0.0]
            },
            'memory': {
                'total': 0,
                'available': 0,
                'used': 0,
                'free': 0,
                'percent': 0,
                'swap_total': 0,
                'swap_used': 0,
                'swap_free': 0,
                'swap_percent': 0
            },
            'disk': {
                'total': 0,
                'used': 0,
                'free': 0,
                'percent': 0,
                'read_bytes': 0,
                'write_bytes': 0
            },
            'network': {
                'bytes_sent': 0,
                'bytes_recv': 0,
                'packets_sent': 0,
                'packets_recv': 0
            },
            'processes': {
                'total': 0,
                'running': 0,
                'top_cpu': [],
                'top_mem': []
            },
            'thresholds': DEFAULT_THRESHOLDS
        }

def _get_cpu_temperature() -> float:
    """Obtiene temperatura de la CPU con manejo robusto"""
    try:
        if hasattr(psutil, 'sensors_temperatures'):
            temps = psutil.sensors_temperatures()
            if not temps:
                return DEFAULT_TEMP
                
            # Buscar en sensores comunes
            for sensor_name in ['coretemp', 'cpu_thermal', 'k10temp', 'acpitz']:
                if sensor_name in temps and temps[sensor_name]:
                    return temps[sensor_name][0].current
                    
            # Tomar el primer sensor disponible
            for sensor in temps.values():
                if sensor:
                    return sensor[0].current
    except Exception as e:
        logger.debug(f"No se pudo obtener temperatura: {str(e)}")
    return DEFAULT_TEMP

def _get_processes_info() -> Dict[str, Union[int, list]]:
    """Obtiene información de procesos con manejo de errores"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
        try:
            proc_info = proc.info
            processes.append({
                'pid': proc_info['pid'],
                'name': proc_info['name'],
                'user': proc_info.get('username', 'N/A'),
                'cpu': proc_info['cpu_percent'],
                'memory': proc_info['memory_percent'],
                'status': proc_info.get('status', 'unknown')
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            logger.debug(f"Error obteniendo info de proceso: {str(e)}")
            continue
    
    return {
        'total': len(processes),
        'running': len([p for p in processes if p.get('status') == 'running']),
        'top_cpu': sorted(processes, key=lambda p: p['cpu'], reverse=True)[:10],
        'top_mem': sorted(processes, key=lambda p: p['memory'], reverse=True)[:10]
    }

if __name__ == "__main__":
    # Prueba de funcionamiento
    print("=== Prueba de system_info.py ===")
    print(f"Modelo del sistema: {get_system_model()}")
    
    os_info = get_os_info()
    print("\nInformación del SO:")
    for key, value in os_info.items():
        print(f"{key:>15}: {value}")
    
    print("\nInformación del sistema en tiempo real:")
    try:
        sys_info = get_system_info()
        print(f"CPU: {sys_info['cpu']['percent']}% (Temp: {sys_info['cpu']['temperature']}°C)")
        print(f"Memoria: {sys_info['memory']['percent']}% usado")
        print(f"Disco: {sys_info['disk']['percent']}% usado")
        print(f"Procesos: {sys_info['processes']['total']} en ejecución")
    except SystemInfoError as e:
        print(f"Error al obtener información del sistema: {str(e)}")
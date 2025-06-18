import subprocess
import time
import socket
import sys
import os
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def resource_path(relative_path):
    """Devuelve la ruta absoluta para entorno de ejecución."""
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

def run_flask():
    try:
        ruta_app = resource_path(os.path.join("backend", "app.py"))
        logger.info(f"Iniciando Flask desde: {ruta_app}")

        if not os.path.exists(ruta_app):
            logger.error(f"Archivo app.py no encontrado: {ruta_app}")
            return False

        command = [sys.executable, ruta_app]
        subprocess.Popen(command)
        return True

    except Exception as e:
        logger.error(f"Error al iniciar Flask: {e}")
        return False

def wait_for_flask(port=5000, timeout=30):
    logger.info("Esperando que Flask se inicie...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                logger.info("Flask activo")
                return True
        except:
            time.sleep(0.5)
    return False

if __name__ == '__main__':
    logger.info("Iniciando aplicación...")

    if run_flask():
        if wait_for_flask():
            logger.info("Servidor Flask activo")
        else:
            logger.error("Flask no respondió a tiempo")
    else:
        logger.error("No se pudo iniciar Flask")

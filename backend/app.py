from flask import Flask, render_template, jsonify, send_from_directory, request, redirect, url_for, flash
from flask_socketio import SocketIO, emit
from system_info import get_system_info, kill_process, get_system_model, get_os_info
from apps_manager import AppsManager
import time
from threading import Thread
import platform
from datetime import datetime
import os
import socket
import json
import sys
import atexit
import eventlet

# --- Función para compatibilidad con PyInstaller ---
def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

# --- Rutas base ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = resource_path(os.path.join("backend", "templates"))
STATIC_DIR = resource_path(os.path.join("backend", "static"))
CONFIG_PATH = resource_path(os.path.join("backend", "config.json"))


# --- Flask App ---
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.config['SECRET_KEY'] = 'clave_super_secreta'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# --- Variables globales ---
monitoring_active = False
alert_history = []
apps_manager = AppsManager()

# --- Carga y guarda configuración ---
def cargar_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Configuración inválida. Usando valores por defecto.")
    return {
        "intervalo": 5,
        "cpu_threshold": 80,
        "ram_threshold": 75,
        "notificaciones": "on",
        "tema": "light",
        "twofa": "off"
    }

def guardar_config(data):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(data, f, indent=4)

# --- Funciones del sistema ---
def get_architecture():
    return platform.machine()

def get_system_version():
    return platform.version()

def monitor_system():
    global monitoring_active
    config = cargar_config()

    print("[INFO] Iniciando monitoreo del sistema...")

    while monitoring_active:
        try:
            system_data = get_system_info()
            system_data['hostname'] = socket.gethostname()
            system_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            socketio.emit('system_update', system_data)
            check_for_alerts(system_data, config)

            intervalo = config.get('intervalo', 5)
            time.sleep(max(1, intervalo))  # mínimo 1 segundo
        except Exception as e:
            print(f"[ERROR] monitor_system: {e}")
            time.sleep(5)  # Espera antes de reintentar


def check_for_alerts(system_data, config):
    alerts = []

    if system_data['cpu']['percent'] > config['cpu_threshold']:
        alerts.append({
            'type': 'danger',
            'title': 'Alerta de CPU',
            'message': f"Uso de CPU al {system_data['cpu']['percent']}% (Umbral: {config['cpu_threshold']}%)",
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })

    if system_data['memory']['percent'] > config['ram_threshold']:
        alerts.append({
            'type': 'danger',
            'title': 'Alerta de Memoria',
            'message': f"Uso de RAM al {system_data['memory']['percent']}% (Umbral: {config['ram_threshold']}%)",
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })

    if system_data['disk']['percent'] > 95:
        alerts.append({
            'type': 'warning',
            'title': 'Alerta de Disco',
            'message': f"Espacio en disco al {system_data['disk']['percent']}%",
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })

    if 'temperature' in system_data['cpu'] and system_data['cpu']['temperature'] > 85:
        alerts.append({
            'type': 'warning',
            'title': 'Alerta de Temperatura',
            'message': f"Temperatura CPU: {system_data['cpu']['temperature']} °C",
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })

    if alerts and config.get('notificaciones', 'on') == 'on':
        alert_history.extend(alerts)
        socketio.emit('new_alerts', alerts[-3:])

# --- Rutas ---
@app.route('/')
def menu():
    return render_template('menu.html')

@app.route('/index.html')
def index():
    return render_template('index.html',
                           system_model=get_system_model(),
                           os_info=get_os_info(),
                           architecture=get_architecture(),
                           version=get_system_version())

@app.route('/configuracion', methods=['GET', 'POST'])
def configuracion():
    if request.method == 'POST':
        nueva_config = {
            "intervalo": int(request.form.get('intervalo', 5)),
            "cpu_threshold": int(request.form.get('cpu_threshold', 80)),
            "ram_threshold": int(request.form.get('ram_threshold', 75)),
            "notificaciones": request.form.get('notificaciones', 'off'),
            "tema": request.form.get('tema', 'light'),
            "twofa": request.form.get('twofa', 'off')
        }
        guardar_config(nueva_config)
        flash("Configuración guardada con éxito.", "success")
        return redirect(url_for('configuracion'))

    config = cargar_config()
    return render_template('configuracion.html', config=config)

@app.route('/apps')
def apps_list():
    try:
        apps = apps_manager.get_installed_apps()
        return jsonify({"success": True, "apps": apps, "system": platform.system()})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/clean_cache/<app_name>', methods=['POST'])
def clean_cache(app_name):
    result = AppsManager().clean_app_cache(app_name)
    return jsonify(result)

@app.route('/apps_page')
def apps_page():
    return render_template('apps.html')

@app.route('/uninstall_app/<app_name>', methods=['POST'])
def uninstall_app(app_name):
    try:
        result = apps_manager.uninstall_app(app_name)
        message = result.get("message", f"No se pudo desinstalar {app_name}")
        return jsonify({'success': result.get("success", False), 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al desinstalar: {str(e)}"}), 500

@app.route('/apps-view')
def apps_view():
    apps = apps_manager.get_installed_apps()
    return render_template('apps.html', apps=apps)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/api/system-info')
def system_info():
    hostname = socket.gethostname()
    return jsonify({
        'model': get_system_model(),
        'hostname': hostname,
        'os': get_os_info(),
        'architecture': platform.machine(),
        'version': get_system_version()
    })

@app.route('/get-alerts')
def get_recent_alerts():
    return jsonify({'alerts': alert_history[-10:]})

# --- WebSocket Handlers ---
@socketio.on('start_monitoring')
def handle_start_monitoring():
    global monitoring_active
    if not monitoring_active:
        monitoring_active = True
        Thread(target=monitor_system, daemon=True).start()

@socketio.on('stop_monitoring')
def handle_stop_monitoring():
    global monitoring_active
    monitoring_active = False

@socketio.on('kill_process')
def handle_kill_process(data):
    pid = int(data['pid'])
    success, message = kill_process(pid)
    emit('process_killed', {'success': success, 'message': message})

@socketio.on('request_apps_list')
def handle_apps_list_request():
    try:
        apps = apps_manager.get_installed_apps()
        emit('apps_list_response', {
            'success': True,
            'apps': apps[:100],
            'os': platform.system()
        })
    except Exception as e:
        emit('apps_list_response', {
            'success': False,
            'message': str(e)
        })

# --- Finalización segura ---
@atexit.register
def goodbye():
    print(">>> Flask detenido")

# --- Ejecutar la app ---
# --- Ejecutar la app ---
# --- Ejecutar la app ---
if __name__ == '__main__':
    import eventlet
    eventlet.monkey_patch()

    TEMPLATE_DIR = resource_path(os.path.join("backend", "templates"))
    STATIC_DIR = resource_path(os.path.join("backend", "static"))

    print(f"[INFO] Plantillas en: {TEMPLATE_DIR}")
    print(f"[INFO] Archivos estáticos en: {STATIC_DIR}")

    if not os.path.exists(TEMPLATE_DIR):
        print(f"[ERROR] No se encontró la carpeta de plantillas en {TEMPLATE_DIR}")
        sys.exit(1)
    if not os.path.exists(STATIC_DIR):
        print(f"[WARNING] No se encontró la carpeta static en {STATIC_DIR}")

    debug_mode = not hasattr(sys, 'frozen')  # False si está empaquetado

socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)


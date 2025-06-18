from flask import Flask, render_template
from flask_socketio import SocketIO
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return "¡Hola desde Flask desplegado en Render sin WebView!"

@socketio.on('mensaje')
def handle_mensaje(data):
    logging.info(f"Mensaje recibido: {data}")
    # Aquí puedes procesar el mensaje, emitir, guardar, etc.

if __name__ == '__main__':
    logging.info("Iniciando aplicación Flask con SocketIO...")
    socketio.run(app, host='0.0.0.0', port=5000)

// static/js/notifications.js - Versión sin sonidos

function checkResourceAlerts(systemData) {
    // Alertas para CPU
    if (systemData.cpu.percent > 90) {
        showAlert("¡CPU al máximo!", `Uso: ${systemData.cpu.percent}%`, "danger");
    }

    // Alertas para RAM
    if (systemData.memory.percent > 90) {
        showAlert("¡RAM agotada!", `Uso: ${systemData.memory.percent}%`, "danger");
    }

    // Alertas para temperatura
    if (systemData.cpu.temperature > 85) {
        showAlert("¡Alerta de temperatura!", `CPU: ${systemData.cpu.temperature}°C`, "warning");
    }
}

function showAlert(title, message, type) {
    // Crea notificación visual
    const alertHtml = `
        <div class="alert alert-${type}">
            <strong>${title}</strong> ${message}
            <button class="close-btn">&times;</button>
        </div>
    `;
    document.getElementById('alerts-container').insertAdjacentHTML('afterbegin', alertHtml);
    
    // Agregar funcionalidad al botón de cerrar
    document.querySelector('#alerts-container .alert:first-child .close-btn')
        .addEventListener('click', (e) => {
            e.target.parentElement.remove();
        });
}
// Conectar al servidor WebSocket
const socket = io();

// Iniciar monitoreo al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    // Solicitar inicio de monitoreo
    socket.emit('start_monitoring');
    
    // Configurar gráficos
    initCharts();
    
    // Configurar manejadores de eventos
    setupEventHandlers();

      // Mostrar información inicial del sistema
    displaySystemInfo();
});

function initCharts() {
    // Gráfico de CPU
    const cpuCtx = document.getElementById('cpuChart').getContext('2d');
    window.cpuChart = new Chart(cpuCtx, {
        type: 'line',
        data: {
            labels: Array(10).fill(''),
            datasets: [{
                label: 'Uso de CPU %',
                data: Array(10).fill(0),
                borderColor: '#BB86FC',
                backgroundColor: 'rgba(187, 134, 252, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true
            }]
        },
        options: getChartOptions()
    });

    // Gráfico de Red
    const networkCtx = document.getElementById('networkChart').getContext('2d');
    window.networkChart = new Chart(networkCtx, {
        type: 'line',
        data: {
            labels: Array(10).fill(''),
            datasets: [
                {
                    label: 'Datos Enviados (MB)',
                    data: Array(10).fill(0),
                    borderColor: '#4776E6',
                    backgroundColor: 'rgba(71, 118, 230, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Datos Recibidos (MB)',
                    data: Array(10).fill(0),
                    borderColor: '#8E54E9',
                    backgroundColor: 'rgba(142, 84, 233, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: getChartOptions()
    });
}

function getChartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: { color: '#E1E1E1' }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                grid: { color: 'rgba(255, 255, 255, 0.1)' },
                ticks: { color: '#A0A0A0' }
            },
            x: {
                grid: { color: 'rgba(255, 255, 255, 0.1)' },
                ticks: { color: '#A0A0A0' }
            }
        }
    };
}

function setupEventHandlers() {
    // Escuchar actualizaciones del sistema
    socket.on('system_update', function(data) {
        updateSystemInfo(data);
        updateCharts(data);
        updateProcessTables(data.processes);
           updateSystemHardwareInfo(data); // Nueva función añadida
    });
    
    // Escuchar nuevas alertas
    socket.on('new_alerts', function(alerts) {
        showAlerts(alerts);
    });
}

function updateSystemInfo(data) {
    // Actualizar información de CPU
    document.getElementById('cpu-percent').textContent = `${data.cpu.percent}%`;
    document.getElementById('cpu-cores').textContent = data.cpu.count;
    document.getElementById('cpu-freq').textContent = (data.cpu.frequency / 1000).toFixed(2);
    document.getElementById('cpu-temp').textContent = data.cpu.temperature.toFixed(1);
    document.getElementById('cpu-percent-text').textContent = `${data.cpu.percent}%`;
    document.getElementById('cpu-progress').style.width = `${data.cpu.percent}%`;
    
    // Actualizar estado CPU
    updateStatusIndicator('cpu-status', data.cpu.percent, 80, 90);
    
    // Actualizar información de Memoria
    const memUsedGB = (data.memory.used / (1024 ** 3)).toFixed(2);
    const memTotalGB = (data.memory.total / (1024 ** 3)).toFixed(2);
    
    document.getElementById('mem-percent').textContent = `${data.memory.percent}%`;
    document.getElementById('mem-used').textContent = memUsedGB;
    document.getElementById('mem-total').textContent = memTotalGB;
    document.getElementById('mem-percent-text').textContent = `${data.memory.percent}%`;
    document.getElementById('mem-progress').style.width = `${data.memory.percent}%`;
    updateStatusIndicator('mem-status', data.memory.percent, 80, 90);
    
    // Actualizar información de Disco
    const diskUsedGB = (data.disk.used / (1024 ** 3)).toFixed(2);
    const diskTotalGB = (data.disk.total / (1024 ** 3)).toFixed(2);
    
    document.getElementById('disk-percent').textContent = `${data.disk.percent}%`;
    document.getElementById('disk-used').textContent = diskUsedGB;
    document.getElementById('disk-total').textContent = diskTotalGB;
    document.getElementById('disk-percent-text').textContent = `${data.disk.percent}%`;
    document.getElementById('disk-progress').style.width = `${data.disk.percent}%`;
    updateStatusIndicator('disk-status', data.disk.percent, 85, 95);
    
    // Actualizar información de Red
    const sentMB = (data.network.bytes_sent / (1024 ** 2)).toFixed(2);
    const recvMB = (data.network.bytes_recv / (1024 ** 2)).toFixed(2);
    const totalMB = (parseFloat(sentMB) + parseFloat(recvMB)).toFixed(2);
    
    document.getElementById('bytes-sent').textContent = sentMB;
    document.getElementById('bytes-recv').textContent = recvMB;
    document.getElementById('network-total').textContent = `${totalMB} MB`;
    
    // Actualizar timestamp
    document.getElementById('timestamp').textContent = `Actualizado: ${data.timestamp}`;
}
function displaySystemInfo() {
    // Esta información se carga inicialmente desde el template
    // y se actualiza dinámicamente con updateSystemHardwareInfo
    console.log("Mostrando información inicial del sistema...");
}

function updateCharts(data) {
    // Actualizar gráfico de CPU
    window.cpuChart.data.datasets[0].data.shift();
    window.cpuChart.data.datasets[0].data.push(data.cpu.percent);
    window.cpuChart.update();
    
    // Actualizar gráfico de Red
    const sentMB = (data.network.bytes_sent / (1024 ** 2)).toFixed(2);
    const recvMB = (data.network.bytes_recv / (1024 ** 2)).toFixed(2);
    
    window.networkChart.data.datasets[0].data.shift();
    window.networkChart.data.datasets[1].data.shift();
    window.networkChart.data.datasets[0].data.push(parseFloat(sentMB));
    window.networkChart.data.datasets[1].data.push(parseFloat(recvMB));
    window.networkChart.update();
}

function updateProcessTables(processData) {
    updateProcessTable('cpu-processes', processData.top_cpu);
    updateProcessTable('mem-processes', processData.top_mem);
}

function updateProcessTable(tableId, processes) {
    const tableBody = document.getElementById(tableId);
    tableBody.innerHTML = '';
    
    processes.forEach(proc => {
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>${proc.pid}</td>
            <td>${proc.name}</td>
            <td>${proc.cpu.toFixed(1)}%</td>
            <td>${proc.memory.toFixed(1)}%</td>
            <td><button class="kill-btn" onclick="killProcess(${proc.pid})"><i class="fas fa-skull"></i> Terminar</button></td>
        `;
        
        tableBody.appendChild(row);
    });
}

function updateStatusIndicator(elementId, value, warningThreshold, dangerThreshold) {
    const indicator = document.getElementById(elementId);
    
    if (value > dangerThreshold) {
        indicator.className = 'status-indicator status-danger';
    } else if (value > warningThreshold) {
        indicator.className = 'status-indicator status-warning';
    } else {
        indicator.className = 'status-indicator status-good';
    }
}

function showAlerts(alerts) {
    const container = document.getElementById('alerts-container');
    container.innerHTML = '';
    
    alerts.forEach(alert => {
        const alertHtml = `
            <div class="alert alert-${alert.type}">
                <strong>${alert.title}</strong> ${alert.message}
                <small>${alert.timestamp}</small>
                <button class="close-btn" onclick="this.parentElement.remove()">&times;</button>
            </div>
        `;
        container.insertAdjacentHTML('afterbegin', alertHtml);
        
        // Reproducir sonido de alerta si es crítica
        if (alert.type === 'danger') {
            playAlertSound();
        }
    });
}

function playAlertSound() {
    const audio = new Audio('/static/sounds/alert.mp3');
    audio.volume = 0.3;
    audio.play().catch(e => console.log("No se pudo reproducir sonido:", e));
}

// Función global para terminar procesos
window.killProcess = function(pid) {
    socket.emit('kill_process', { pid: pid });
};

// Escuchar respuesta de terminación de proceso
socket.on('process_killed', function(data) {
    if (data.success) {
        showAlert('Éxito', data.message, 'success');
    } else {
        showAlert('Error', data.message, 'danger');
    }
});

function showAlert(title, message, type) {
    const alertHtml = `
        <div class="alert alert-${type}">
            <strong>${title}</strong> ${message}
            <button class="close-btn" onclick="this.parentElement.remove()">&times;</button>
        </div>
    `;
    document.getElementById('alerts-container').insertAdjacentHTML('afterbegin', alertHtml);
}
// Añade esta función para mostrar la información de hardware
function updateSystemHardwareInfo(data) {
    // Actualizar información del sistema
    document.getElementById('system-model').textContent = data.system_model || data.hostname || "Desconocido";
    document.getElementById('system-arch').textContent = data.os_info?.architecture || "Desconocida";
    document.getElementById('system-os').textContent = data.os_info?.os_name || "Desconocido";
    document.getElementById('system-version').textContent = data.os_info?.os_version || "Desconocida";
    
    // Mostrar nombre del host conectado
    document.getElementById('connected-host').textContent = data.hostname || "Nombre no disponible";
}

// Modifica setupEventHandlers para asegurar que se llame a updateSystemHardwareInfo
function setupEventHandlers() {
    // Escuchar actualizaciones del sistema
    socket.on('system_update', function(data) {
        updateSystemInfo(data);
        updateCharts(data);
        updateProcessTables(data.processes);
        updateSystemHardwareInfo(data);  // Asegúrate que esta línea esté presente
    });
    
    // Escuchar nuevas alertas
    socket.on('new_alerts', function(alerts) {
        showAlerts(alerts);
    });
}

// Añade esta función para la carga inicial
function displaySystemInfo() {
    // Obtener información inicial del sistema
    fetch('/api/system-info')
        .then(response => response.json())
        .then(data => {
            updateSystemHardwareInfo(data);
        })
        .catch(error => {
            console.error('Error obteniendo información del sistema:', error);
        });
}
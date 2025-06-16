document.addEventListener('DOMContentLoaded', function() {
    // Cargar apps al iniciar
    cargarApps();

    // Botón actualizar
    document.getElementById('refresh-apps').addEventListener('click', function() {
        cargarApps();
    });

    // Agregar filtro de búsqueda
    const searchInput = document.getElementById('search-apps');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const query = this.value.trim().toLowerCase();
            const filtered = window.allApps.filter(app =>
                (app.name || '').toLowerCase().includes(query) ||
                (app.version || '').toLowerCase().includes(query)
            );
            renderApps(filtered);
        });
    }
});

// Función para cargar apps desde el backend
function cargarApps() {
    fetch('/apps')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.allApps = data.apps; // Guardar apps para filtrar
                renderApps(data.apps);
            } else {
                showError(data.message);
            }
        })
        .catch(error => showError(error));
}

function renderApps(apps) {
    const tbody = document.getElementById('apps-list');
    tbody.innerHTML = apps.map(app => `
        <tr>
            <td>${app.name || 'N/A'}</td>
            <td>${app.version || 'N/A'}</td>
            <td>${app.size ? app.size + ' MB' : 'N/A'}</td>
            <td>${app.install_date || 'N/A'}</td>
            <td>
                <button class="btn btn-danger btn-sm" 
                        onclick="showUninstallModal('${app.name.replace("'", "\\'")}')">
                    <i class="fas fa-trash-alt"></i> Desinstalar
                </button>
                <button class="btn btn-warning btn-sm" 
                        onclick="clearCache('${app.name.replace("'", "\\'")}')">
                    <i class="fas fa-broom"></i> Borrar caché
                </button>
            </td>
        </tr>
    `).join('');
}

// Function to clear cache
window.clearCache = function(appName) {
    if (confirm(`¿Seguro que quieres borrar la caché de ${appName}?`)) {
        fetch(`/api/clean_cache/${encodeURIComponent(appName)}`, { method: 'POST' })
            .then(res => res.json())
            .then(data => alert(data.message))
            .catch(() => alert('Error al borrar caché'));
    }
};

function showError(message) {
    const container = document.querySelector('.apps-container');
    container.innerHTML = `
        <div class="alert alert-danger">
            <i class="fas fa-exclamation-circle"></i>
            Error al cargar aplicaciones: ${message}
        </div>
    `;
}

// --- Lógica para desinstalar con modal y CSRF ---
let appToUninstall = null;

// Mostrar el modal de confirmación de desinstalación
window.showUninstallModal = function(appName) {
    appToUninstall = appName;
    document.getElementById('modal-message').textContent = `¿Estás seguro de querer desinstalar "${appName}"?`;
    document.getElementById('uninstall-modal').style.display = 'block';
};

// Cerrar el modal y limpiar variable
function closeModal() {
    document.getElementById('uninstall-modal').style.display = 'none';
    appToUninstall = null;
}

// Confirmar desinstalación
document.getElementById('confirm-uninstall').onclick = function() {
    if (appToUninstall) {
        fetch(`/uninstall_app/${encodeURIComponent(appToUninstall)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.getElementById('csrf-token') ? document.getElementById('csrf-token').value : ''
            }
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            cargarApps(); // Recargar la lista sin recargar la página
        })
        .catch(() => alert('Error al desinstalar la aplicación.'));
    }
    closeModal();
};

// Cancelar desinstalación
document.getElementById('cancel-uninstall').onclick = closeModal;
document.getElementById('close-modal').onclick = closeModal;

// Cerrar modal si se hace clic fuera del contenido
window.onclick = function(event) {
    const modal = document.getElementById('uninstall-modal');
    if (event.target === modal) {
        closeModal();
    }
};
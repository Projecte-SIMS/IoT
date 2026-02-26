// State management
let devices = [];
let autoRefreshInterval = null;

// DOM Elements
const devicesContainer = document.getElementById('devices');
const deviceCountEl = document.getElementById('deviceCount');
const msgContainer = document.getElementById('msg-container');
const autoRefreshToggle = document.getElementById('autoRefresh');
const deviceTemplate = document.getElementById('deviceTemplate');

/**
 * Show a toast notification
 */
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type === 'success' ? 'success' : 'danger'}`;
    toast.style.backgroundColor = type === 'success' ? 'var(--success)' : 'var(--danger)';
    toast.textContent = message;
    msgContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Fetch and render devices
 */
async function listDevices() {
    try {
        const res = await fetch('/api/devices');
        if (!res.ok) throw new Error('Error al cargar dispositivos');
        
        devices = await res.json();
        renderDevices();
        deviceCountEl.textContent = `${devices.length} dispositivo${devices.length !== 1 ? 's' : ''}`;
    } catch (err) {
        console.error(err);
        showToast('Error de conexión con el servidor', 'error');
    }
}

/**
 * Render devices using template
 */
function renderDevices() {
    devicesContainer.innerHTML = '';
    
    if (devices.length === 0) {
        devicesContainer.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 3rem; background: white; border-radius: 1rem; border: 2px dashed var(--border);">
                <div style="font-size: 3rem; margin-bottom: 1rem;">📡</div>
                <p>Esperando conexión del primer dispositivo...</p>
                <small>Inicia un agente en tu Raspberry para verlo aquí automáticamente.</small>
            </div>
        `;
        return;
    }

    devices.forEach(device => {
        const clone = deviceTemplate.content.cloneNode(true);
        
        // Fill data
        clone.querySelector('.device-name').textContent = device.name;
        clone.querySelector('.device-id').textContent = `ID: ${device.id}`;
        clone.querySelector('.vehicle-id').textContent = device.vehicle_id ? `Vehículo: ${device.vehicle_id}` : 'Sin vehículo asignado';
        
        const badge = clone.querySelector('.status-badge');
        badge.textContent = device.online ? 'ONLINE' : 'OFFLINE';
        badge.classList.add(device.online ? 'status-online' : 'status-offline');

        // Meta info (if available)
        if (device.meta && Object.keys(device.meta).length > 0) {
            const metaDiv = document.createElement('div');
            metaDiv.className = 'meta-info';
            
            let metaHtml = `
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #cbd5e1; padding-bottom: 0.5rem; margin-bottom: 0.5rem;">
                    <span style="font-weight: 700; color: var(--text-muted); text-transform: uppercase; font-size: 0.7rem;">Hardware</span>
                    <div style="display: flex; gap: 0.5rem;">`;
            
            if (device.meta.relays) {
                Object.keys(device.meta.relays).forEach(r => {
                    const active = device.meta.relays[r];
                    metaHtml += `<span title="Relay ${r}" style="width: 12px; height: 12px; border-radius: 50%; background: ${active ? 'var(--success)' : '#cbd5e1'}; display: inline-block;"></span>`;
                });
            }
            metaHtml += `</div></div>`;

            if (device.meta.sensors) {
                const s = device.meta.sensors;
                metaHtml += `
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem 1rem;">
                        <div>
                            <div style="font-size: 0.6rem; color: var(--text-muted); font-weight: 600; letter-spacing: 0.025em;">UBICACIÓN</div>
                            <div style="font-family: 'Courier New', monospace; font-size: 0.7rem; color: var(--text);">${s.gps.lat.toFixed(4)}, ${s.gps.lon.toFixed(4)}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.6rem; color: var(--text-muted); font-weight: 600; letter-spacing: 0.025em;">VELOCIDAD</div>
                            <div style="font-family: 'Courier New', monospace; font-size: 0.7rem; color: var(--text);">${s.gps.speed.toFixed(1)} km/h</div>
                        </div>
                        <div>
                            <div style="font-size: 0.6rem; color: var(--text-muted); font-weight: 600; letter-spacing: 0.025em;">MOTOR</div>
                            <div style="font-family: 'Courier New', monospace; font-size: 0.7rem; color: var(--text);">${s.engine.temp.toFixed(0)}°C | ${s.engine.rpm}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.6rem; color: var(--text-muted); font-weight: 600; letter-spacing: 0.025em;">BATERÍA</div>
                            <div style="font-family: 'Courier New', monospace; font-size: 0.7rem; color: var(--text);">${s.battery.toFixed(1)}V</div>
                        </div>
                    </div>
                `;
            }
            
            metaDiv.innerHTML = metaHtml;
            clone.querySelector('.meta-container').appendChild(metaDiv);
        }

        // Actions
        clone.querySelector('.btn-on').onclick = () => sendCommand(device.id, 'on');
        clone.querySelector('.btn-off').onclick = () => sendCommand(device.id, 'off');
        clone.querySelector('.btn-edit').onclick = () => openEditModal(device);
        clone.querySelector('.btn-delete').onclick = () => deleteDevice(device.id);

        devicesContainer.appendChild(clone);
    });
}

/**
 * Edit Modal Logic
 */
let currentEditingId = null;
const editModal = document.getElementById('editModal');
const editNameInput = document.getElementById('editName');
const editVehicleInput = document.getElementById('editVehicle');

function openEditModal(device) {
    currentEditingId = device.id;
    editNameInput.value = device.name;
    editVehicleInput.value = device.vehicle_id || '';
    editModal.style.display = 'flex';
}

document.getElementById('cancelEdit').onclick = () => {
    editModal.style.display = 'none';
};

document.getElementById('saveEdit').onclick = async () => {
    const name = editNameInput.value.trim();
    const vehicle_id = editVehicleInput.value.trim() || null;

    if (!name) return showToast('El nombre es obligatorio', 'error');

    try {
        const res = await fetch(`/api/devices/${currentEditingId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, vehicle_id })
        });

        if (res.ok) {
            showToast('Dispositivo actualizado');
            editModal.style.display = 'none';
            listDevices();
        } else {
            showToast('Error al actualizar', 'error');
        }
    } catch (err) {
        showToast('Error de conexión', 'error');
    }
};

/**
 * Create a new device
 */
async function createDevice() {
    const nameInput = document.getElementById('name');
    const vehicleInput = document.getElementById('vehicle');
    const name = nameInput.value.trim();
    const vehicle_id = vehicleInput.value.trim() || null;

    if (!name) {
        showToast('El nombre es obligatorio', 'error');
        return;
    }

    try {
        const res = await fetch('/api/devices', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, vehicle_id })
        });

        if (res.ok) {
            showToast('Dispositivo creado correctamente');
            nameInput.value = '';
            vehicleInput.value = '';
            listDevices();
        } else {
            showToast('Error al crear el dispositivo', 'error');
        }
    } catch (err) {
        showToast('Error de red', 'error');
    }
}

/**
 * Send command to device
 */
async function sendCommand(device_id, action) {
    try {
        const res = await fetch('/api/command', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'x-api-key': 'MACMECMIC' // En producción esto debería manejarse con sesión
            },
            body: JSON.stringify({ device_id, action, relay: 0 })
        });

        const data = await res.json();
        if (res.ok) {
            showToast(`Comando '${action.toUpperCase()}' ${data.result === 'sent' ? 'enviado' : 'encolado'}`);
        } else {
            showToast(`Error: ${data.detail || 'Fallo al enviar'}`, 'error');
        }
    } catch (err) {
        showToast('Error al conectar con la API de comandos', 'error');
    }
}

/**
 * Delete device
 */
async function deleteDevice(device_id) {
    if (!confirm('¿Estás seguro de eliminar este dispositivo? Se borrarán todos sus datos.')) return;

    try {
        const res = await fetch(`/api/devices/${device_id}`, { method: 'DELETE' });
        if (res.ok) {
            showToast('Dispositivo eliminado');
            listDevices();
        } else {
            showToast('No se pudo eliminar el dispositivo', 'error');
        }
    } catch (err) {
        showToast('Error de red al eliminar', 'error');
    }
}

/**
 * Setup Auto-Refresh
 */
function setupAutoRefresh() {
    if (autoRefreshToggle.checked) {
        if (!autoRefreshInterval) {
            autoRefreshInterval = setInterval(listDevices, 5000); // Cada 5 segundos
        }
    } else {
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
            autoRefreshInterval = null;
        }
    }
}

// Event Listeners
document.getElementById('create').addEventListener('click', createDevice);
document.getElementById('refresh').addEventListener('click', listDevices);
autoRefreshToggle.addEventListener('change', setupAutoRefresh);

// Init
window.addEventListener('load', () => {
    listDevices();
    setupAutoRefresh();
});

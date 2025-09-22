document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = 'http://127.0.0.1:8000/api';
    const buildingsContainer = document.getElementById('deviceList');
    const loader = document.getElementById('loader');
    const notification = document.getElementById('notification');

    const BUILD_PAGE_SIZE = 100;

    function showNotification(text, isError = false, timeout = 3000) {
        notification.textContent = text;
        notification.style.backgroundColor = isError ? '#ef4444' : '#333';
        notification.classList.add('show');
        setTimeout(() => notification.classList.remove('show'), timeout);
    }

    async function apiRequest(endpoint, options = {}) {
        const url = `${API_BASE_URL}/${endpoint}`;
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error occurred' }));
                throw new Error(errorData.detail || `Request failed with status ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API request to ${endpoint} failed:`, error);
            showNotification(error.message, true);
            throw error;
        }
    }

    function createBuildingCard(building) { // Expects {id, name}
        const card = document.createElement('div');
        card.className = 'building-card';
        card.dataset.buildingId = building.id; // Store building ID
        card.innerHTML = `
            <div class="building-header">
                <button class="toggle-btn">+</button>
                <h2 class="building-title">${escapeHtml(building.name)}</h2>
                <div class="building-status"></div>
            </div>
            <div class="building-body" style="display:none;">
                <div class="building-controls">
                    <input type="text" class="building-search" placeholder="Search devices..."/>
                </div>
                <ul class="devices-list"></ul>
                <div class="building-loader" style="display:none;">Loading...</div>
            </div>
        `;
        
        const header = card.querySelector('.building-header');
        const body = card.querySelector('.building-body');
        const devicesList = card.querySelector('.devices-list');

        const toggleVisibility = async () => {
            const isHidden = body.style.display === 'none';
            body.style.display = isHidden ? 'block' : 'none';
            header.querySelector('.toggle-btn').textContent = isHidden ? '-' : '+';
            if (isHidden && devicesList.children.length === 0) {
                await loadDevicesForBuilding(card);
            }
        };

        header.addEventListener('click', toggleVisibility);

        devicesList.addEventListener('click', (e) => {
            const deviceItem = e.target.closest('.device-item');
            if (deviceItem) handleDeviceClick(deviceItem);
        });

        const searchInput = card.querySelector('.building-search');
        let searchDebounceTimer;
        searchInput.addEventListener('input', () => {
            clearTimeout(searchDebounceTimer);
            searchDebounceTimer = setTimeout(() => {
                loadDevicesForBuilding(card, true, searchInput.value.trim());
            }, 400);
        });

        return card;
    }

    async function loadDevicesForBuilding(card, reset = false, search = '') {
        const buildingId = card.dataset.buildingId; // Use building ID
        const devicesList = card.querySelector('.devices-list');
        const loader = card.querySelector('.building-loader');
        
        if (reset) devicesList.innerHTML = '';
        loader.style.display = 'block';

        try {
            const devices = await apiRequest(`devices?building=${buildingId}&limit=${BUILD_PAGE_SIZE}&search=${encodeURIComponent(search)}`);
            if (devices.length === 0 && reset) {
                devicesList.innerHTML = '<li class="muted">No devices found.</li>';
            } else {
                devices.forEach(device => devicesList.appendChild(createDeviceItem(device)));
            }
        } finally {
            loader.style.display = 'none';
            updateBuildingStatus(card);
        }
    }

    function createDeviceItem(device) {
        const li = document.createElement('li');
        const state = (device.state || 'unknown').toLowerCase();
        li.className = 'device-item';
        li.dataset.deviceId = device.id;
        li.dataset.state = state;

        const stateClass = state === 'armed' ? 'state-armed' : (state === 'disarmed' ? 'state-disarmed' : 'state-unknown');

        li.innerHTML = `
            <span class="device-state-indicator ${stateClass}"></span>
            <div class="device-name">${escapeHtml(device.name)} (ID: ${device.id})</div>
            <div class="device-state-text">${escapeHtml(device.state)}</div>
        `;
        return li;
    }

    async function handleDeviceClick(deviceItem) {
        const deviceId = parseInt(deviceItem.dataset.deviceId, 10);
        const currentState = deviceItem.dataset.state;
        
        if (currentState !== 'armed' && currentState !== 'disarmed') {
            showNotification('Device is in an unmodifiable state.', true);
            return;
        }

        const action = currentState === 'armed' ? 'disarm' : 'arm';
        deviceItem.style.opacity = '0.5';

        try {
            const result = await apiRequest('devices/action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_ids: [deviceId], action: action })
            });

            if (result.success_count > 0) {
                updateDeviceUI(deviceItem, action === 'arm' ? 'armed' : 'disarmed');
                showNotification(`Device ${action}ed successfully.`);
            } else {
                const detail = result.details.find(d => d.device_id === deviceId);
                throw new Error(detail ? detail.message : 'Action failed on the server.');
            }
        } catch (error) {
            showNotification(error.message, true);
        } finally {
            deviceItem.style.opacity = '1';
            updateBuildingStatus(deviceItem.closest('.building-card'));
        }
    }

    function updateDeviceUI(deviceItem, newState) {
        const stateIndicator = deviceItem.querySelector('.device-state-indicator');
        const stateText = deviceItem.querySelector('.device-state-text');
        
        deviceItem.dataset.state = newState;
        stateText.textContent = newState.charAt(0).toUpperCase() + newState.slice(1);

        stateIndicator.className = 'device-state-indicator';
        stateIndicator.classList.add(newState === 'armed' ? 'state-armed' : 'state-disarmed');
    }

    function updateBuildingStatus(card) {
        const devices = card.querySelectorAll('.device-item');
        const statusEl = card.querySelector('.building-status');
        if (devices.length === 0) {
            statusEl.textContent = 'No Devices';
            statusEl.className = 'building-status status-none-armed';
            return;
        }

        const armedCount = Array.from(devices).filter(d => d.dataset.state === 'armed').length;

        if (armedCount === devices.length) {
            statusEl.textContent = 'All Armed';
            statusEl.className = 'building-status status-all-armed';
        } else if (armedCount > 0) {
            statusEl.textContent = 'Partially Armed';
            statusEl.className = 'building-status status-partial-armed';
        } else {
            statusEl.textContent = 'All Disarmed';
            statusEl.className = 'building-status status-none-armed';
        }
    }

    function escapeHtml(str) {
        return String(str || '').replace(/[&<>"']/g, s => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;',
            '"': '&quot;', "'": '&#39;'
        }[s]));
    }

    async function initialize() {
        try {
            loader.style.display = 'block';
            const buildings = await apiRequest('buildings');
            buildingsContainer.innerHTML = '';
            buildings.forEach(building => {
                buildingsContainer.appendChild(createBuildingCard(building));
            });
        } finally {
            loader.style.display = 'none';
        }
    }

    initialize();
});
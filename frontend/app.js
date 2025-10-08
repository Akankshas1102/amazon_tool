document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = 'http://127.0.0.1:8000/api';
    const buildingsContainer = document.getElementById('deviceList');
    const loader = document.getElementById('loader');
    const notification = document.getElementById('notification');
    const buildingSearch = document.querySelector('.building-search');
    const buildingDropdown = document.querySelector('.building-dropdown');
    const clearFilter = document.querySelector('.clear-filter');

    let allBuildings = [];
    let selectedBuildingId = null;
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

    function setupBuildingSelector() {
        buildingSearch.addEventListener('input', () => {
            const query = buildingSearch.value.toLowerCase();
            buildingDropdown.innerHTML = '';
            
            if (query.length === 0) {
                buildingDropdown.style.display = 'none';
                clearFilter.style.display = 'none';
                return;
            }

            const filtered = allBuildings.filter(b => 
                b.name.toLowerCase().includes(query)
            );

            if (filtered.length > 0) {
                filtered.forEach(building => {
                    const option = document.createElement('div');
                    option.className = 'building-option';
                    option.textContent = building.name;
                    option.addEventListener('click', () => selectBuilding(building));
                    buildingDropdown.appendChild(option);
                });
                buildingDropdown.style.display = 'block';
                clearFilter.style.display = 'block';
            } else {
                buildingDropdown.style.display = 'none';
            }
        });

        clearFilter.addEventListener('click', () => {
            buildingSearch.value = '';
            buildingDropdown.style.display = 'none';
            clearFilter.style.display = 'none';
            selectedBuildingId = null;
            loadAllBuildings();
        });

        document.addEventListener('click', (e) => {
            if (!buildingSearch.contains(e.target) && !buildingDropdown.contains(e.target)) {
                buildingDropdown.style.display = 'none';
            }
        });
    }

    function selectBuilding(building) {
        buildingSearch.value = building.name;
        buildingDropdown.style.display = 'none';
        selectedBuildingId = building.id;
        clearFilter.style.display = 'block';
        loadFilteredBuilding(building);
    }

    async function loadFilteredBuilding(building) {
        buildingsContainer.innerHTML = '';
        const card = createBuildingCard(building);
        buildingsContainer.appendChild(card);
        await loadDevicesForBuilding(card);
        const body = card.querySelector('.building-body');
        const toggleBtn = card.querySelector('.toggle-btn');
        body.style.display = 'block';
        toggleBtn.textContent = '-';
    }

    function createBuildingCard(building) {
        const card = document.createElement('div');
        card.className = 'building-card';
        card.dataset.buildingId = building.id;
        
        const scheduledTime = building.scheduled_time || '09:00';
        
        card.innerHTML = `
            <div class="building-header">
                <button class="toggle-btn">+</button>
                <h2 class="building-title">${escapeHtml(building.name)}</h2>
                <div class="building-time-control">
                    <label style="font-size:12px; color:#64748b;">Schedule:</label>
                    <input type="time" class="time-input" value="${scheduledTime}" />
                    <button class="time-save-btn">Save</button>
                </div>
                <div class="building-status"></div>
            </div>
            <div class="building-body" style="display:none;">
                <div class="building-controls">
                    <input type="text" class="device-search" placeholder="Search devices..."/>
                    <div class="bulk-actions">
                        <button class="bulk-btn bulk-arm" disabled>Arm Selected</button>
                        <button class="bulk-btn bulk-disarm" disabled>Disarm Selected</button>
                    </div>
                </div>
                <ul class="devices-list"></ul>
                <div class="building-loader" style="display:none;">Loading...</div>
            </div>
        `;
        
        setupBuildingCardEvents(card);
        return card;
    }

    function setupBuildingCardEvents(card) {
        const header = card.querySelector('.building-header');
        const body = card.querySelector('.building-body');
        const devicesList = card.querySelector('.devices-list');
        const toggleBtn = card.querySelector('.toggle-btn');
        const timeInput = card.querySelector('.time-input');
        const timeSaveBtn = card.querySelector('.time-save-btn');
        const armBtn = card.querySelector('.bulk-arm');
        const disarmBtn = card.querySelector('.bulk-disarm');
        const deviceSearch = card.querySelector('.device-search');

        const toggleVisibility = async () => {
            const isHidden = body.style.display === 'none';
            body.style.display = isHidden ? 'block' : 'none';
            toggleBtn.textContent = isHidden ? '-' : '+';
            if (isHidden && devicesList.children.length === 0) {
                await loadDevicesForBuilding(card);
            }
        };

        header.addEventListener('click', (e) => {
            if (!e.target.closest('.building-time-control')) {
                toggleVisibility();
            }
        });

        timeSaveBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const buildingId = parseInt(card.dataset.buildingId);
            const time = timeInput.value;
            
            if (!time) {
                showNotification('Please select a valid time', true);
                return;
            }

            try {
                await apiRequest(`buildings/${buildingId}/time`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        building_id: buildingId,
                        scheduled_time: time
                    })
                });
                showNotification('Building schedule updated successfully');
            } catch (error) {
                showNotification('Failed to update building schedule', true);
            }
        });

        let searchDebounceTimer;
        deviceSearch.addEventListener('input', () => {
            clearTimeout(searchDebounceTimer);
            searchDebounceTimer = setTimeout(() => {
                loadDevicesForBuilding(card, true, deviceSearch.value.trim());
            }, 400);
        });

        armBtn.addEventListener('click', () => performBulkAction(card, 'arm'));
        disarmBtn.addEventListener('click', () => performBulkAction(card, 'disarm'));

        devicesList.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox') {
                updateBulkActionButtons(card);
            }
            if (e.target.classList.contains('device-state-select')) {
                handleDeviceStateChange(e.target);
            }
            if (e.target.classList.contains('ignore-alarm-checkbox')) {
                handleIgnoreAlarmChange(e.target);
            }
        });
    }

    async function loadDevicesForBuilding(card, reset = false, search = '') {
        const buildingId = card.dataset.buildingId;
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
            updateBulkActionButtons(card);
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
            <input type="checkbox" class="device-checkbox" />
            <span class="device-state-indicator ${stateClass}"></span>
            <div class="device-name">${escapeHtml(device.name)} (ID: ${device.id})</div>
            <select class="device-state-select">
                <option value="armed" ${state === 'armed' ? 'selected' : ''}>Armed</option>
                <option value="disarmed" ${state === 'disarmed' ? 'selected' : ''}>Disarmed</option>
            </select>
            <label class="ignore-alarm-label">
                <input type="checkbox" class="ignore-alarm-checkbox" ${device.is_ignored ? 'checked' : ''} />
                Ignore Alarm
            </label>
        `;
        return li;
    }

    async function handleDeviceStateChange(selectElement) {
        const deviceItem = selectElement.closest('.device-item');
        const deviceId = parseInt(deviceItem.dataset.deviceId, 10);
        const newState = selectElement.value;
        const currentState = deviceItem.dataset.state;
        
        if (newState === currentState) return;

        const action = newState === 'armed' ? 'arm' : 'disarm';
        deviceItem.style.opacity = '0.5';

        try {
            const result = await apiRequest('devices/action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_ids: [deviceId], action: action })
            });

            if (result.success_count > 0) {
                updateDeviceUI(deviceItem, newState);
                showNotification(`Device ${action}ed successfully.`);
            } else {
                const detail = result.details.find(d => d.device_id === deviceId);
                throw new Error(detail ? detail.message : 'Action failed on the server.');
            }
        } catch (error) {
            selectElement.value = currentState;
            showNotification(error.message, true);
        } finally {
            deviceItem.style.opacity = '1';
            updateBuildingStatus(deviceItem.closest('.building-card'));
        }
    }

    async function handleIgnoreAlarmChange(checkbox) {
        const deviceItem = checkbox.closest('.device-item');
        const deviceId = parseInt(deviceItem.dataset.deviceId, 10);
        const action = checkbox.checked ? 'ignore' : 'unignore';

        try {
            await apiRequest('devices/ignored-alarms', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_id: deviceId, action: action })
            });
            showNotification(`Device alarm ${action}d successfully.`);
        } catch (error) {
            checkbox.checked = !checkbox.checked; // Revert checkbox state
            showNotification(`Failed to ${action} device alarm.`, true);
        }
    }

    async function performBulkAction(card, action) {
        const selectedDevices = Array.from(card.querySelectorAll('.device-checkbox:checked'))
            .map(cb => parseInt(cb.closest('.device-item').dataset.deviceId, 10));

        if (selectedDevices.length === 0) {
            showNotification('Please select devices first', true);
            return;
        }

        const armBtn = card.querySelector('.bulk-arm');
        const disarmBtn = card.querySelector('.bulk-disarm');
        
        armBtn.disabled = true;
        disarmBtn.disabled = true;

        try {
            const result = await apiRequest('devices/action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_ids: selectedDevices, action: action })
            });

            result.details.forEach(detail => {
                if (detail.status === 'Success') {
                    const deviceItem = card.querySelector(`[data-device-id="${detail.device_id}"]`);
                    if (deviceItem) {
                        const newState = action === 'arm' ? 'armed' : 'disarmed';
                        updateDeviceUI(deviceItem, newState);
                        const select = deviceItem.querySelector('.device-state-select');
                        select.value = newState;
                    }
                }
            });

            if (result.success_count > 0) {
                showNotification(`${result.success_count} device(s) ${action}ed successfully.`);
            }
            
            if (result.failure_count > 0) {
                showNotification(`${result.failure_count} device(s) failed to ${action}.`, true);
            }

            card.querySelectorAll('.device-checkbox:checked').forEach(cb => cb.checked = false);
            
        } finally {
            updateBulkActionButtons(card);
            updateBuildingStatus(card);
        }
    }

    function updateBulkActionButtons(card) {
        const selectedCount = card.querySelectorAll('.device-checkbox:checked').length;
        const armBtn = card.querySelector('.bulk-arm');
        const disarmBtn = card.querySelector('.bulk-disarm');
        
        armBtn.disabled = selectedCount === 0;
        disarmBtn.disabled = selectedCount === 0;
    }

    function updateDeviceUI(deviceItem, newState) {
        const stateIndicator = deviceItem.querySelector('.device-state-indicator');
        
        deviceItem.dataset.state = newState;

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

    async function loadAllBuildings() {
        try {
            loader.style.display = 'block';
            allBuildings = await apiRequest('buildings');
            buildingsContainer.innerHTML = '';
            
            allBuildings.forEach(building => {
                buildingsContainer.appendChild(createBuildingCard(building));
            });
        } finally {
            loader.style.display = 'none';
        }
    }

    async function initialize() {
        setupBuildingSelector();
        await loadAllBuildings();
    }

    initialize();
});
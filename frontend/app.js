// frontend/app.js

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
        await loadItemsForBuilding(card);
        const body = card.querySelector('.building-body');
        const toggleBtn = card.querySelector('.toggle-btn');
        body.style.display = 'block';
        toggleBtn.textContent = '-';
    }

    function createBuildingCard(building) {
        const card = document.createElement('div');
        card.className = 'building-card';
        card.dataset.buildingId = building.id;
        const startTime = building.start_time || '09:00';
        const endTime = building.end_time || '17:00';

        card.innerHTML = `
            <div class="building-header">
                <button class="toggle-btn">+</button>
                <h2 class="building-title">${escapeHtml(building.name)}</h2>
                <div class="building-actions">
                    <button class="bulk-btn bulk-arm">Arm Building</button>
                    <button class="bulk-btn bulk-disarm">Disarm Building</button>
                </div>
                <div class="building-time-control">
                    <label>Start:</label>
                    <input type="time" class="time-input start-time-input" value="${startTime}" required />
                    <label>End:</label>
                    <input type="time" class="time-input end-time-input" value="${endTime}" required />
                    <button class="time-save-btn">Save</button>
                </div>
                <div class="building-status"></div>
            </div>
            <div class="building-body" style="display:none;">
                <div class="building-controls">
                    <input type="text" class="item-search" placeholder="Search proevents..."/>
                </div>
                <ul class="items-list"></ul>
                <div class="building-loader" style="display:none;">Loading...</div>
            </div>
        `;
        setupBuildingCardEvents(card);
        return card;
    }

    function setupBuildingCardEvents(card) {
        const itemsList = card.querySelector('.items-list');
        itemsList.addEventListener('change', (e) => {
            if (e.target.classList.contains('ignore-item-checkbox')) {
                handleIgnoreChange(e.target);
            }
        });

        const header = card.querySelector('.building-header');
        const body = card.querySelector('.building-body');
        const toggleBtn = card.querySelector('.toggle-btn');
        const startTimeInput = card.querySelector('.start-time-input');
        const endTimeInput = card.querySelector('.end-time-input');
        const timeSaveBtn = card.querySelector('.time-save-btn');
        const armBtn = card.querySelector('.bulk-arm');
        const disarmBtn = card.querySelector('.bulk-disarm');
        const itemSearch = card.querySelector('.item-search');

        const toggleVisibility = async () => {
            const isHidden = body.style.display === 'none';
            body.style.display = isHidden ? 'block' : 'none';
            toggleBtn.textContent = isHidden ? '-' : '+';
            if (isHidden && itemsList.children.length === 0) {
                await loadItemsForBuilding(card);
            }
        };

        header.addEventListener('click', (e) => {
            if (!e.target.closest('.building-time-control') && !e.target.closest('.building-actions')) {
                toggleVisibility();
            }
        });

        timeSaveBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const buildingId = parseInt(card.dataset.buildingId);
            const startTime = startTimeInput.value;
            const endTime = endTimeInput.value;
            
            if (!startTime || !endTime) {
                showNotification('Both start and end times are required.', true);
                return;
            }

            try {
                await apiRequest(`buildings/${buildingId}/time`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        building_id: buildingId,
                        start_time: startTime,
                        end_time: endTime
                    })
                });
                showNotification('Building schedule updated successfully');
            } catch (error) {
                showNotification('Failed to update building schedule', true);
            }
        });

        let searchDebounceTimer;
        itemSearch.addEventListener('input', () => {
            clearTimeout(searchDebounceTimer);
            searchDebounceTimer = setTimeout(() => {
                loadItemsForBuilding(card, true, itemSearch.value.trim());
            }, 400);
        });

        armBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            performBuildingAction(card, 'arm');
        });

        disarmBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            performBuildingAction(card, 'disarm');
        });
    }

    async function loadItemsForBuilding(card, reset = false, search = '') {
        const buildingId = card.dataset.buildingId;
        const itemsList = card.querySelector('.items-list');
        const loader = card.querySelector('.building-loader');
        
        if (reset) itemsList.innerHTML = '';
        loader.style.display = 'block';

        try {
            const items = await apiRequest(`devices?building=${buildingId}&limit=${BUILD_PAGE_SIZE}&search=${encodeURIComponent(search)}`);
            if (items.length === 0 && reset) {
                itemsList.innerHTML = '<li class="muted">No proevents found.</li>';
            } else {
                items.forEach(item => itemsList.appendChild(createItem(item)));
            }
        } finally {
            loader.style.display = 'none';
            updateBuildingStatus(card);
        }
    }

    function createItem(item) {
        const li = document.createElement('li');
        const state = (item.state || 'unknown').toLowerCase();
        li.className = 'device-item';
        li.dataset.itemId = item.id;
        li.dataset.state = state;

        const stateClass = state === 'armed' ? 'state-armed' : (state === 'disarmed' ? 'state-disarmed' : 'state-unknown');

        li.innerHTML = `
            <span class="device-state-indicator ${stateClass}"></span>
            <div class="device-name">${escapeHtml(item.name)} (ID: ${item.id})</div>
            <label class="ignore-alarm-label">
                <input type="checkbox" class="ignore-item-checkbox ignore-on-arm" ${item.is_ignored_on_arm ? 'checked' : ''} />
                Ignore when Armed
            </label>
            <label class="ignore-alarm-label">
                <input type="checkbox" class="ignore-item-checkbox ignore-on-disarm" ${item.is_ignored_on_disarm ? 'checked' : ''} />
                Ignore when Disarmed
            </label>
        `;
        return li;
    }
    
    async function handleIgnoreChange(checkbox) {
        const itemLi = checkbox.closest('.device-item');
        const itemId = parseInt(itemLi.dataset.itemId, 10);
        const ignoreOnArm = itemLi.querySelector('.ignore-on-arm').checked;
        const ignoreOnDisarm = itemLi.querySelector('.ignore-on-disarm').checked;

        try {
            await apiRequest('proevents/ignore', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    item_id: itemId,
                    ignore_on_arm: ignoreOnArm,
                    ignore_on_disarm: ignoreOnDisarm
                })
            });
            showNotification(`ProEvent ignore settings updated.`);
        } catch (error) {
            checkbox.checked = !checkbox.checked; // Revert the clicked checkbox on failure
            showNotification(`Failed to update ignore settings.`, true);
        }
    }

    async function performBuildingAction(card, action) {
        const buildingId = parseInt(card.dataset.buildingId, 10);
        const armBtn = card.querySelector('.bulk-arm');
        const disarmBtn = card.querySelector('.bulk-disarm');
        
        armBtn.disabled = true;
        disarmBtn.disabled = true;

        try {
            await apiRequest('devices/action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ building_id: buildingId, action: action })
            });
            showNotification(`Building ${action}ed successfully. Refreshing...`);
            setTimeout(() => {
                loadItemsForBuilding(card, true, card.querySelector('.item-search').value.trim());
            }, 1500);
        } catch(error) {
            showNotification(`Failed to ${action} building.`, true)
        } finally {
            armBtn.disabled = false;
            disarmBtn.disabled = false;
        }
    }

    function updateBuildingStatus(card) {
        const items = card.querySelectorAll('.device-item');
        const statusEl = card.querySelector('.building-status');
        
        if (items.length === 0) {
            statusEl.textContent = 'No ProEvents';
            statusEl.className = 'building-status status-none-armed';
            return;
        }

        const armedCount = Array.from(items).filter(d => d.dataset.state === 'armed').length;

        if (armedCount === items.length) {
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
// frontend/app.js

document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = 'http://127.0.0.1:8000/api';
    const buildingsContainer = document.getElementById('deviceList');
    const loader = document.getElementById('loader');
    const notification = document.getElementById('notification');
    const buildingSearch = document.querySelector('.building-search');
    const buildingDropdown = document.querySelector('.building-dropdown');
    const clearFilter = document.querySelector('.clear-filter');
    const ignoreModal = document.getElementById('ignoreModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalItemList = document.getElementById('modalItemList');
    const modalConfirmBtn = document.getElementById('modalConfirmBtn');
    const modalCancelBtn = document.getElementById('modalCancelBtn');
    const closeButton = document.querySelector('.close-button');
    const modalSearch = document.getElementById('modalSearch');
    const modalSelectAllBtn = document.getElementById('modalSelectAllBtn');

    // --- New Panel Status Elements ---
    const panelStatusToggle = document.getElementById('panel-status-toggle');
    const panelStatusText = document.getElementById('panel-status-text');


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
            // Handle JSON responses or no-content responses
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.indexOf("application/json") !== -1) {
                return await response.json();
            }
            return {}; // Return empty object for non-json responses
        } catch (error) {
            console.error(`API request to ${endpoint} failed:`, error);
            showNotification(error.message, true);
            throw error;
        }
    }

    // --- Panel Status Logic ---

    async function loadPanelStatus() {
        try {
            const data = await apiRequest('panel_status');
            panelStatusToggle.checked = data.armed;
            updatePanelStatusText(data.armed);
        } catch (error) {
            console.error('Failed to load panel status:', error);
            panelStatusText.textContent = 'Error';
        }
    }

    function updatePanelStatusText(isArmed) {
        if (isArmed) {
            panelStatusText.textContent = 'Panel Armed';
            panelStatusText.style.color = '#22c55e';
        } else {
            panelStatusText.textContent = 'Panel Disarmed';
            panelStatusText.style.color = '#ef4444';
        }
    }

    async function togglePanelStatus() {
        const isArmed = panelStatusToggle.checked;
        try {
            await apiRequest('panel_status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ armed: isArmed })
            });
            updatePanelStatusText(isArmed);
            showNotification(`Panel ${isArmed ? 'Armed' : 'Disarmed'}`);
        } catch (error) {
            console.error('Failed to update panel status:', error);
            // Revert on failure
            panelStatusToggle.checked = !isArmed;
            updatePanelStatusText(!isArmed);
        }
    }

    // --- Building Selector Logic ---

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
                    <button class="bulk-btn bulk-disarm">Set Ignore Flags</button>
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
        const header = card.querySelector('.building-header');
        const body = card.querySelector('.building-body');
        const toggleBtn = card.querySelector('.toggle-btn');
        const startTimeInput = card.querySelector('.start-time-input');
        const endTimeInput = card.querySelector('.end-time-input');
        const timeSaveBtn = card.querySelector('.time-save-btn');
        // "armBtn" removed
        const disarmBtn = card.querySelector('.bulk-disarm'); // This is now "Set Ignore Flags"
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

        // "armBtn" listener removed

        // This listener for "Set Ignore Flags" (formerly "Disarm Building")
        // now correctly shows the modal for setting ignore flags for the "disarm" state.
        disarmBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            // We pass 'disarm' to correctly set the 'is_ignored_on_disarm' flag
            showIgnoreSelectionModal(card.dataset.buildingId, 'disarm');
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

        // Use 'state-unknown' for both 'unknown' and 'disarmed' for indicator
        const stateClass = state === 'armed' ? 'status-all-armed' : 'state-unknown';

        li.innerHTML = `
            <span class="device-state-indicator ${stateClass}" style="background-color: ${state === 'armed' ? '#22c55e' : '#f59e0b'};"></span>
            <div class="device-name">${escapeHtml(item.name)} (ID: ${item.id})</div>
        `;
        return li;
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

    async function showIgnoreSelectionModal(buildingId, action) {
        // Updated title to be more generic, as this modal is now only for setting ignore flags.
        modalTitle.textContent = `Select proevents to ignore`;
        modalItemList.innerHTML = '<div class="loader">Loading...</div>';
        ignoreModal.style.display = 'block';
        
        // Reset modal controls
        modalSearch.value = '';
        modalSelectAllBtn.textContent = 'Select All';

        const items = await apiRequest(`devices?building=${buildingId}&limit=1000`);
        modalItemList.innerHTML = '';
        items.forEach(item => {
            const div = document.createElement('div');
            div.className = 'device-item';
            div.dataset.itemId = item.id;
            
            // The modal will now show *both* ignore flags, but only the 'disarm' one is
            // relevant to the button click. The user can manage both here.
            div.innerHTML = `
                <div class="device-name">${escapeHtml(item.name)}</div>
                <label class="ignore-alarm-label">
                    <input type="checkbox" class="ignore-item-checkbox-arm" ${item.is_ignored_on_arm ? 'checked' : ''} />
                    Ignore on Arm
                </label>
                <label class="ignore-alarm-label">
                    <input type="checkbox" class="ignore-item-checkbox-disarm" ${item.is_ignored_on_disarm ? 'checked' : ''} />
                    Ignore on Disarm
                </label>
            `;
            modalItemList.appendChild(div);
        });
        
        // --- Event Handlers for modal features ---
        
        modalSearch.oninput = () => {
            const query = modalSearch.value.toLowerCase();
            const modalItems = modalItemList.querySelectorAll('.device-item');
            modalItems.forEach(item => {
                const name = item.querySelector('.device-name').textContent.toLowerCase();
                item.style.display = name.includes(query) ? 'flex' : 'none';
            });
            modalSelectAllBtn.textContent = 'Select All'; // Reset button on search
        };
        
        modalSelectAllBtn.onclick = () => {
            const isSelectAll = modalSelectAllBtn.textContent === 'Select All';
            const modalItems = modalItemList.querySelectorAll('.device-item');
            modalItems.forEach(item => {
                // Only toggle checkboxes for visible items
                if (item.style.display !== 'none') {
                    const checkboxArm = item.querySelector('.ignore-item-checkbox-arm');
                    const checkboxDisarm = item.querySelector('.ignore-item-checkbox-disarm');
                    // This button now controls *both* checkboxes for simplicity
                    if (checkboxArm) checkboxArm.checked = isSelectAll;
                    if (checkboxDisarm) checkboxDisarm.checked = isSelectAll;
                }
            });
            modalSelectAllBtn.textContent = isSelectAll ? 'Deselect All' : 'Select All';
        };

        modalConfirmBtn.onclick = async () => {
            const selectedItems = [];
            const itemElements = modalItemList.querySelectorAll('.device-item');
            
            itemElements.forEach(itemEl => {
                const checkboxArm = itemEl.querySelector('.ignore-item-checkbox-arm');
                const checkboxDisarm = itemEl.querySelector('.ignore-item-checkbox-disarm');
                const itemId = parseInt(itemEl.dataset.itemId, 10);
                
                selectedItems.push({
                    item_id: itemId,
                    building_frk: parseInt(buildingId),
                    device_prk: itemId, // Using item_id as a placeholder for device_prk
                    ignore_on_arm: checkboxArm.checked,
                    ignore_on_disarm: checkboxDisarm.checked
                });
            });

            try {
                await apiRequest('proevents/ignore/bulk', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ items: selectedItems })
                });
                showNotification('Ignore settings updated successfully.');
                // Refresh the building view
                const card = document.querySelector(`.building-card[data-building-id='${buildingId}']`);
                if (card) {
                    const itemSearch = card.querySelector('.item-search');
                    loadItemsForBuilding(card, true, itemSearch.value.trim());
                }
            } catch (error) {
                showNotification('Failed to update ignore settings.', true);
            } finally {
                closeModal();
            }
        };
        
        const closeModal = () => {
            ignoreModal.style.display = 'none';
            // Clear event handlers to prevent memory leaks
            modalSearch.oninput = null;
            modalSelectAllBtn.onclick = null;
            modalConfirmBtn.onclick = null;
        };

        modalCancelBtn.onclick = closeModal;
        closeButton.onclick = closeModal;
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
        // --- Load panel status on init ---
        await loadPanelStatus();
        // --- Add listener for toggle ---
        panelStatusToggle.addEventListener('change', togglePanelStatus);
    }

    initialize();
});
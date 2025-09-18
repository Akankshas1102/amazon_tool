document.addEventListener('DOMContentLoaded', () => {
  const API_BASE_URL = 'http://127.0.0.1:8000/api';
  const buildingsContainer = document.getElementById('deviceList'); // reuse existing container
  const loader = document.getElementById('loader');
  const notification = document.getElementById('notification');

  const BUILD_PAGE_SIZE = 100; // devices per page when loading a building

  function showNotification(text, timeout = 3000) {
    notification.textContent = text;
    notification.classList.add('show');
    setTimeout(() => notification.classList.remove('show'), timeout);
  }

  async function fetchBuildings() {
    const res = await fetch(`${API_BASE_URL}/buildings`);
    if (!res.ok) throw new Error('Failed to fetch buildings');
    return await res.json();
  }

  async function fetchDevicesForBuilding(building, limit = BUILD_PAGE_SIZE, offset = 0, search = '') {
    const params = new URLSearchParams();
    if (building) params.append('building', building);
    if (search) params.append('search', search);
    params.append('limit', String(limit));
    params.append('offset', String(offset));
    const url = `${API_BASE_URL}/devices?` + params.toString();
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch devices for ' + building);
    return await res.json();
  }

  function createBuildingCard(building) {
    const card = document.createElement('div');
    card.className = 'building-card';
    card.dataset.building = building;
    card.innerHTML = `
      <div class="building-header">
        <button class="toggle-btn">+</button>
        <h2 class="building-title">Building: ${building}</h2>
      </div>
      <div class="building-body" style="display:none;">
        <div class="building-controls">
          <input type="text" class="building-search" placeholder="Search devices (name or state)"/>
          <button class="load-more" style="display:none;">Load more</button>
        </div>
        <ul class="devices-list"></ul>
        <div class="building-loader" style="display:none;">Loading...</div>
      </div>
    `;
    // state
    card._offset = 0;
    card._ended = false;
    card._lastSearch = '';

    // attach handlers
    const toggleBtn = card.querySelector('.toggle-btn');
    const body = card.querySelector('.building-body');
    const searchInput = card.querySelector('.building-search');
    const devicesList = card.querySelector('.devices-list');
    const loadMoreBtn = card.querySelector('.load-more');
    const buildingLoader = card.querySelector('.building-loader');

    toggleBtn.addEventListener('click', async () => {
      if (body.style.display === 'none') {
        body.style.display = 'block';
        toggleBtn.textContent = '-';
        // if devices not yet loaded, load first page
        if (devicesList.children.length === 0) {
          await loadDevices(true);
        }
      } else {
        body.style.display = 'none';
        toggleBtn.textContent = '+';
      }
    });

    let searchDebounceTimer = null;
    searchInput.addEventListener('input', () => {
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(async () => {
        card._offset = 0;
        card._ended = false;
        card._lastSearch = searchInput.value.trim();
        devicesList.innerHTML = '';
        await loadDevices(true);
      }, 400);
    });

    loadMoreBtn.addEventListener('click', async () => {
      await loadDevices(false);
    });

    async function loadDevices(reset = false) {
      try {
        buildingLoader.style.display = 'block';
        const search = card._lastSearch || '';
        const data = await fetchDevicesForBuilding(building, BUILD_PAGE_SIZE, card._offset, search);
        if (!Array.isArray(data) || data.length === 0) {
          // no results
          if (reset) {
            devicesList.innerHTML = '<li class="muted">No devices found.</li>';
          }
          card._ended = true;
          loadMoreBtn.style.display = 'none';
          return;
        }
        // append devices
        data.forEach(d => {
          const li = document.createElement('li');
          li.className = 'device-item';
          li.innerHTML = `<div class="device-name">${escapeHtml(d.name)}</div><div class="device-state">${escapeHtml(d.state || '')}</div>`;
          devicesList.appendChild(li);
        });
        // advance offset
        card._offset += data.length;
        // show load more if we got a full page
        if (data.length >= BUILD_PAGE_SIZE) {
          loadMoreBtn.style.display = 'inline-block';
        } else {
          loadMoreBtn.style.display = 'none';
          card._ended = true;
        }
      } catch (err) {
        console.error(err);
        showNotification('Error loading devices: ' + err.message);
      } finally {
        buildingLoader.style.display = 'none';
      }
    }

    return card;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"'`=\/]/g, function (s) {
      return ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
        '/': '&#x2F;',
        '`': '&#x60;',
        '=': '&#x3D;'
      })[s];
    });
  }

  async function initialize() {
    try {
      loader.style.display = 'block';
      const buildings = await fetchBuildings();
      buildingsContainer.innerHTML = '';
      if (!buildings || buildings.length === 0) {
        buildingsContainer.innerHTML = '<p>No buildings found.</p>';
        return;
      }
      // create card for each building
      buildings.forEach(b => {
        const card = createBuildingCard(b);
        buildingsContainer.appendChild(card);
      });
    } catch (err) {
      console.error(err);
      showNotification('Failed to load buildings: ' + err.message);
    } finally {
      loader.style.display = 'none';
    }
  }

  initialize();
});

/* ─── GuardX Core App Module ─── */
/* Navigation, API polling, state management */

const API_BASE = '';  // Same origin
let currentPage = 'dashboard';
let pollingInterval = null;
const POLL_RATE = 2000; // 2 seconds

// ─── Navigation ─────────────────────────────────────────────────

function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const page = item.dataset.page;
            navigateTo(page);
        });
    });

    // Menu toggle for mobile
    const toggle = document.getElementById('menu-toggle');
    if (toggle) {
        toggle.addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('open');
        });
    }
}

function navigateTo(page) {
    // Update nav
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`[data-page="${page}"]`)?.classList.add('active');

    // Update pages
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${page}`)?.classList.add('active');

    // Update title
    const titles = {
        dashboard: 'Dashboard',
        anomaly: 'Anomaly Monitor',
        analytics: 'Sensor Analytics',
        ml: 'ML Intelligence',
        labeling: 'Fault Labeling',
        alerts: 'Alerts History',
    };
    document.getElementById('page-title').textContent = titles[page] || page;
    currentPage = page;

    // Load page-specific data
    loadPageData(page);
}

function loadPageData(page) {
    switch (page) {
        case 'dashboard': refreshDashboard(); break;
        case 'anomaly': refreshAnomaly(); break;
        case 'analytics': refreshAnalytics(); break;
        case 'ml': refreshML(); break;
        case 'labeling': refreshLabeling(); break;
        case 'alerts': refreshAlerts(); break;
    }
}

// ─── API Helper ─────────────────────────────────────────────────

async function apiFetch(endpoint) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error(`API error: ${endpoint}`, err);
        return null;
    }
}

async function apiPost(endpoint, data) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return await res.json();
    } catch (err) {
        console.error(`API POST error: ${endpoint}`, err);
        return null;
    }
}

async function apiPut(endpoint) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, { method: 'PUT' });
        return await res.json();
    } catch (err) {
        console.error(`API PUT error: ${endpoint}`, err);
        return null;
    }
}

// ─── Clock ──────────────────────────────────────────────────────

function updateClock() {
    const el = document.getElementById('current-time');
    if (el) {
        el.textContent = new Date().toLocaleString();
    }
}

// ─── Toast Notifications ────────────────────────────────────────

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// ─── Polling ────────────────────────────────────────────────────

function startPolling() {
    pollingInterval = setInterval(() => {
        loadPageData(currentPage);
        updateClock();
        updateAlertBadge();
    }, POLL_RATE);
}

async function updateAlertBadge() {
    const data = await apiFetch('/api/v1/alerts/active');
    const badge = document.getElementById('alert-count');
    if (data && data.length > 0) {
        badge.textContent = data.length;
        badge.style.display = 'inline-block';
    } else {
        badge.style.display = 'none';
    }
}

// ─── Plotly Theme ───────────────────────────────────────────────

const PLOTLY_LAYOUT = {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { family: 'Inter', color: '#9CA3AF', size: 11 },
    margin: { t: 10, r: 10, b: 30, l: 45 },
    xaxis: {
        gridcolor: 'rgba(255,255,255,0.04)',
        zerolinecolor: 'rgba(255,255,255,0.06)',
    },
    yaxis: {
        gridcolor: 'rgba(255,255,255,0.04)',
        zerolinecolor: 'rgba(255,255,255,0.06)',
    },
};

const PLOTLY_CONFIG = {
    responsive: true,
    displayModeBar: false,
};

// ─── Init ───────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    updateClock();
    refreshDashboard();
    startPolling();
});

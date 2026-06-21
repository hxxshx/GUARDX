/* ─── Dashboard Page Module ─── */
/* Health gauge, live sensor charts, status grid, recent alerts */

async function refreshDashboard() {
    const [summary, rawData, healthHistory, anomalyHistory, cncDiag] = await Promise.all([
        apiFetch('/api/v1/dashboard/summary'),
        apiFetch('/api/v1/ingest/latest?n=60'),
        apiFetch('/api/v1/health/history?limit=60'),
        apiFetch('/api/v1/anomaly/history?limit=20'),
        apiFetch('/api/v1/health/diagnostics'),
    ]);

    if (summary) updateStatusGrid(summary);
    if (rawData && rawData.length > 0) updateSensorCharts(rawData);
    if (healthHistory && healthHistory.length > 0) {
        updateHealthGauge(healthHistory);
        // Update RUL Countdown from latest health reading
        const latest = healthHistory[healthHistory.length - 1];
        if (latest) {
            const rulEl = document.getElementById('rul-countdown');
            const degEl = document.getElementById('degradation-rate');
            if (rulEl) {
                if (latest.rul_minutes != null && latest.rul_minutes > 0) {
                    const hrs = Math.floor(latest.rul_minutes / 60);
                    const mins = Math.round(latest.rul_minutes % 60);
                    rulEl.textContent = hrs > 0 ? `${hrs}h ${mins}m` : `${mins} min`;
                    rulEl.style.color = latest.rul_minutes < 30 ? 'var(--high-risk)' : 'var(--warning)';
                } else if (latest.rul_minutes === 0) {
                    rulEl.textContent = 'CRITICAL';
                    rulEl.style.color = 'var(--high-risk)';
                } else {
                    rulEl.textContent = 'Stable ∞';
                    rulEl.style.color = 'var(--healthy)';
                }
            }
            if (degEl) {
                const rate = latest.degradation_rate || 0;
                degEl.textContent = rate > 0 ? `-${rate}%/cycle` : '0%/cycle';
            }
        }
    }
    if (summary) updateMLPhaseBadge(summary.ml_phase);

    // Recent alerts
    const alerts = await apiFetch('/api/v1/alerts?limit=5');
    if (alerts) updateRecentAlerts(alerts);

    // CNC Domain Diagnostics
    if (cncDiag && cncDiag.primary_diagnosis) renderCNCDiagnostics(cncDiag);
}

const FAULT_LABELS = {
    normal: '✅ Normal Operation',
    bearing_wear: '🔴 Bearing Wear',
    imbalance: '⚠️ Imbalance',
    overheating: '🌡️ Overheating',
    overload: '💪 Overload',
    coolant_failure: '❄️ Coolant Failure',
};

function renderCNCDiagnostics(d) {
    const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
    const diagEl = document.getElementById('cnc-diagnosis');
    if (diagEl) {
        diagEl.textContent = FAULT_LABELS[d.primary_diagnosis] || d.primary_diagnosis;
        diagEl.style.color = d.primary_diagnosis === 'normal' ? 'var(--healthy)' : 'var(--warning)';
    }
    el('cnc-confidence', d.confidence + '%');
    el('cnc-evidence-text', d.evidence?.slice(0, 2).join(' | ') || 'No issues detected');
}

function updateStatusGrid(summary) {
    document.getElementById('stat-readings').textContent =
        summary.total_readings?.toLocaleString() || '0';
    document.getElementById('stat-alerts').textContent =
        summary.active_alerts_count || '0';
    document.getElementById('stat-phase').textContent =
        summary.ml_phase || 'A';

    if (summary.latest_anomaly) {
        document.getElementById('stat-anomaly').textContent =
            (summary.latest_anomaly.anomaly_score || 0).toFixed(3);
    }
}

function updateHealthGauge(healthHistory) {
    const latest = healthHistory[healthHistory.length - 1];
    if (!latest) return;

    const score = latest.health_score || 100;
    const risk = latest.risk_level || 'healthy';

    // Update risk badge
    const badge = document.getElementById('risk-badge');
    badge.textContent = risk.replace('_', ' ').toUpperCase();
    badge.className = 'risk-badge ' + risk;

    // Color based on risk
    const colors = {
        healthy: '#00E676',
        warning: '#FFB300',
        critical: '#FF6D00',
        high_risk: '#FF1744',
    };
    const barColor = colors[risk] || '#00E676';

    const gaugeData = [{
        type: 'indicator',
        mode: 'gauge+number',
        value: score,
        number: { suffix: '%', font: { size: 36, color: '#F3F4F6', family: 'Inter' } },
        gauge: {
            axis: { range: [0, 100], tickcolor: '#6B7280' },
            bar: { color: barColor, thickness: 0.7 },
            bgcolor: 'rgba(255,255,255,0.03)',
            borderwidth: 0,
            steps: [
                { range: [0, 40], color: 'rgba(255, 23, 68, 0.08)' },
                { range: [40, 60], color: 'rgba(255, 109, 0, 0.08)' },
                { range: [60, 80], color: 'rgba(255, 179, 0, 0.08)' },
                { range: [80, 100], color: 'rgba(0, 230, 118, 0.08)' },
            ],
            threshold: {
                line: { color: '#F3F4F6', width: 2 },
                thickness: 0.8,
                value: score,
            },
        },
    }];

    const layout = {
        ...PLOTLY_LAYOUT,
        margin: { t: 25, r: 25, b: 10, l: 25 },
        height: 200,
    };

    Plotly.react('health-gauge', gaugeData, layout, PLOTLY_CONFIG);
}

function updateSensorCharts(rawData) {
    const timestamps = rawData.map(r => r.timestamp);
    const sensors = {
        vibration_rms: { id: 'chart-vibration', color: '#00D4FF', data: rawData.map(r => r.vibration_rms) },
        temperature: { id: 'chart-temperature', color: '#FF6D00', data: rawData.map(r => r.temperature) },
        cutting_force: { id: 'chart-current', color: '#7B61FF', data: rawData.map(r => r.cutting_force) },
    };

    for (const [name, sensor] of Object.entries(sensors)) {
        const trace = {
            x: timestamps,
            y: sensor.data,
            type: 'scatter',
            mode: 'lines',
            line: { color: sensor.color, width: 2, shape: 'spline' },
            fill: 'tozeroy',
            fillcolor: sensor.color.replace(')', ', 0.05)').replace('rgb', 'rgba'),
            name: name,
        };

        const layout = {
            ...PLOTLY_LAYOUT,
            height: 180,
            xaxis: { ...PLOTLY_LAYOUT.xaxis, showticklabels: false },
        };

        Plotly.react(sensor.id, [trace], layout, PLOTLY_CONFIG);
    }
}

function updateMLPhaseBadge(phase) {
    const badge = document.getElementById('ml-phase-badge');
    const text = badge.querySelector('.phase-text');
    if (text) text.textContent = `Phase ${phase || 'A'}`;
}

function updateRecentAlerts(alerts) {
    const tbody = document.getElementById('recent-alerts-body');
    if (!alerts || alerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="no-data">No alerts yet</td></tr>';
        return;
    }

    tbody.innerHTML = alerts.map(a => `
        <tr>
            <td>${formatTime(a.timestamp)}</td>
            <td>${a.alert_type}</td>
            <td><span class="severity-${a.severity}">${a.severity}</span></td>
            <td>${a.message}</td>
            <td>
                ${a.acknowledged
            ? '<span class="severity-low">ACK</span>'
            : `<button class="btn btn-sm btn-outline" onclick="ackAlert(${a.id})">Acknowledge</button>`
        }
            </td>
        </tr>
    `).join('');
}

async function ackAlert(id) {
    await apiPut(`/api/v1/alerts/${id}/acknowledge`);
    showToast('Alert acknowledged');
    refreshDashboard();
}

function formatTime(ts) {
    if (!ts) return '--';
    try {
        return new Date(ts).toLocaleTimeString();
    } catch { return ts; }
}

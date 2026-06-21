/* ─── Alerts History Page ─── */

async function refreshAlerts() {
    const alerts = await apiFetch('/api/v1/alerts?limit=100');
    if (alerts) renderAlertsHistory(alerts);
}

function renderAlertsHistory(alerts) {
    const tbody = document.getElementById('alerts-history-body');
    if (!alerts || alerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="no-data">No alerts recorded</td></tr>';
        return;
    }

    tbody.innerHTML = alerts.map(a => `
        <tr>
            <td>${formatTime(a.timestamp)}</td>
            <td>${a.alert_type}</td>
            <td><span class="severity-${a.severity}">${a.severity}</span></td>
            <td>${a.message}</td>
            <td>${a.health_score ? a.health_score.toFixed(1) + '%' : '--'}</td>
            <td>${a.acknowledged ? '<span class="severity-low">Acknowledged</span>' : '<span class="severity-warning">Pending</span>'}</td>
            <td>
                ${a.acknowledged
            ? '--'
            : `<button class="btn btn-sm btn-outline" onclick="ackAlertHistory(${a.id})">ACK</button>`
        }
            </td>
        </tr>
    `).join('');
}

async function ackAlertHistory(id) {
    await apiPut(`/api/v1/alerts/${id}/acknowledge`);
    showToast('Alert acknowledged');
    refreshAlerts();
}

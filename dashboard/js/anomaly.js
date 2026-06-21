/* ─── Anomaly Monitor Page ─── */

async function refreshAnomaly() {
    const [history, flagged] = await Promise.all([
        apiFetch('/api/v1/anomaly/history?limit=200'),
        apiFetch('/api/v1/anomaly/history?limit=50'),
    ]);

    if (history && history.length > 0) renderAnomalyTimeline(history);
    if (flagged) renderFlaggedEvents(flagged.filter(e => e.is_anomaly));
}

function renderAnomalyTimeline(data) {
    const timestamps = data.map(d => d.timestamp);
    const scores = data.map(d => d.anomaly_score);
    const colors = data.map(d => d.is_anomaly ? '#FF1744' : '#00D4FF');

    const trace = {
        x: timestamps,
        y: scores,
        type: 'scatter',
        mode: 'lines+markers',
        line: { color: '#00D4FF', width: 2 },
        marker: { color: colors, size: 4 },
        name: 'Anomaly Score',
    };

    // Threshold line
    const threshold = {
        x: [timestamps[0], timestamps[timestamps.length - 1]],
        y: [0.5, 0.5],
        type: 'scatter',
        mode: 'lines',
        line: { color: '#FF1744', width: 1, dash: 'dash' },
        name: 'Threshold',
    };

    const layout = {
        ...PLOTLY_LAYOUT,
        height: 340,
        yaxis: { ...PLOTLY_LAYOUT.yaxis, title: 'Anomaly Score', range: [0, 1] },
        showlegend: true,
        legend: { x: 0, y: 1.1, orientation: 'h', font: { size: 10 } },
    };

    Plotly.react('chart-anomaly-timeline', [trace, threshold], layout, PLOTLY_CONFIG);
}

function renderFlaggedEvents(events) {
    const tbody = document.getElementById('anomaly-events-body');
    if (!events || events.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="no-data">No anomalies detected yet</td></tr>';
        return;
    }

    tbody.innerHTML = events.slice(0, 20).map(e => `
        <tr>
            <td>${formatTime(e.timestamp)}</td>
            <td><span class="severity-critical">${(e.anomaly_score || 0).toFixed(4)}</span></td>
            <td>${e.model_type || 'isolation_forest'}</td>
            <td>${e.fault_prediction || '--'}</td>
        </tr>
    `).join('');
}

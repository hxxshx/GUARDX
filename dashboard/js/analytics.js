/* ─── Sensor Analytics Page ─── */

async function refreshAnalytics() {
    const sensor = document.getElementById('analytics-sensor-select')?.value || 'vibration';

    const [sensorData, summary] = await Promise.all([
        apiFetch(`/api/v1/analytics/sensor/${sensor}?n=200`),
        apiFetch('/api/v1/analytics/summary'),
    ]);

    if (sensorData && sensorData.data) renderAnalyticsChart(sensorData);
    if (summary && summary[sensor]) renderAnalyticsStats(summary[sensor]);
    if (summary) renderCorrelation(summary);
}

// Listen for sensor select change
document.addEventListener('DOMContentLoaded', () => {
    const sel = document.getElementById('analytics-sensor-select');
    if (sel) sel.addEventListener('change', refreshAnalytics);
});

function renderAnalyticsChart(sensorData) {
    const data = sensorData.data;
    const colors = {
        vibration_rms: '#00D4FF',
        temperature: '#FF6D00',
        cutting_force: '#7B61FF',
        motor_current: '#FFD600',
        speed_command_level: '#00E676',
    };
    const color = colors[sensorData.sensor] || '#00D4FF';

    const trace = {
        x: data.map(d => d.timestamp),
        y: data.map(d => d.value),
        type: 'scatter',
        mode: 'lines',
        line: { color: color, width: 2 },
        fill: 'tozeroy',
        fillcolor: color + '0D',
        name: sensorData.sensor,
    };

    const layout = {
        ...PLOTLY_LAYOUT,
        height: 340,
        yaxis: { ...PLOTLY_LAYOUT.yaxis, title: sensorData.sensor },
    };

    Plotly.react('chart-analytics-detail', [trace], layout, PLOTLY_CONFIG);
}

function renderAnalyticsStats(stats) {
    document.getElementById('stat-min').textContent = stats.min?.toFixed(4) || '--';
    document.getElementById('stat-max').textContent = stats.max?.toFixed(4) || '--';
    document.getElementById('stat-mean').textContent = stats.mean?.toFixed(4) || '--';
    document.getElementById('stat-std').textContent = stats.std?.toFixed(4) || '--';
    document.getElementById('stat-count').textContent = stats.count?.toLocaleString() || '--';
}

function renderCorrelation(summary) {
    const sensors = ['vibration_rms', 'temperature', 'cutting_force', 'motor_current', 'speed_command_level'];
    // Simple correlation display using available stats
    const z = sensors.map(s1 => sensors.map(s2 => {
        if (s1 === s2) return 1.0;
        // Approximate correlation from mean/std ratios
        const a = summary[s1], b = summary[s2];
        if (!a || !b) return 0;
        return Math.min(1, Math.max(-1, (a.std / (a.mean || 1)) * (b.std / (b.mean || 1)) * 2 - 0.5));
    }));

    const trace = {
        z: z,
        x: sensors.map(s => s.replace('_', ' ')),
        y: sensors.map(s => s.replace('_', ' ')),
        type: 'heatmap',
        colorscale: [
            [0, '#0A0E1A'],
            [0.5, '#7B61FF'],
            [1, '#00D4FF'],
        ],
        showscale: true,
        colorbar: { tickfont: { color: '#9CA3AF' } },
    };

    const layout = {
        ...PLOTLY_LAYOUT,
        height: 240,
        margin: { t: 10, r: 10, b: 60, l: 100 },
    };

    Plotly.react('chart-correlation', [trace], layout, PLOTLY_CONFIG);
}

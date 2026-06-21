/* ─── ML Intelligence Page ─── */

async function refreshML() {
    const [status, predictions, metrics, impact] = await Promise.all([
        apiFetch('/api/v1/ml/status'),
        apiFetch('/api/v1/ml/predictions?n=50'),
        apiFetch('/api/v1/ml/metrics'),
        apiFetch('/api/v1/ml/business-impact'),
    ]);

    if (status) renderMLStatus(status);
    if (predictions && predictions.length > 0) renderPredictionChart(predictions);
    if (metrics) renderMLMetrics(metrics);
    if (impact) renderBusinessImpact(impact);
}

function renderMLStatus(status) {
    // Phase cards
    const phases = ['a', 'b', 'c'];
    phases.forEach(p => {
        const card = document.getElementById(`phase-${p}-card`);
        if (card) {
            card.classList.toggle('active', status.current_phase.toLowerCase() === p);
        }
    });

    // Metrics
    document.getElementById('ml-current-phase').textContent =
        `Phase ${status.current_phase} - ${status.phase_description?.split(' - ')[0] || ''}`;
    document.getElementById('ml-label-count').textContent = status.labeled_count || 0;
    document.getElementById('ml-phase-b-thresh').textContent = status.phase_b_threshold || '--';
    document.getElementById('ml-phase-c-thresh').textContent = status.phase_c_threshold || '--';
    document.getElementById('ml-if-loaded').textContent =
        status.unsupervised_model_loaded ? 'Yes' : 'No';
    document.getElementById('ml-clf-loaded').textContent =
        status.supervised_model_loaded ? 'Yes' : 'No';
}

function renderPredictionChart(predictions) {
    // Count anomaly vs normal
    const anomalies = predictions.filter(p => p.is_anomaly).length;
    const normal = predictions.length - anomalies;

    const trace = {
        values: [normal, anomalies],
        labels: ['Normal', 'Anomaly'],
        type: 'pie',
        hole: 0.6,
        marker: {
            colors: ['#00E676', '#FF1744'],
        },
        textinfo: 'label+percent',
        textfont: { color: '#F3F4F6', size: 12 },
    };

    const layout = {
        ...PLOTLY_LAYOUT,
        height: 200,
        showlegend: false,
        margin: { t: 10, r: 10, b: 10, l: 10 },
    };

    Plotly.react('chart-predictions', [trace], layout, PLOTLY_CONFIG);
}

async function triggerRetrain() {
    const btn = document.getElementById('btn-retrain');
    btn.textContent = 'Training...';
    btn.disabled = true;

    const result = await apiPost('/api/v1/ml/retrain', {});

    if (result && result.status === 'ok') {
        showToast('Models retrained successfully!', 'success');
    } else {
        showToast('Retraining failed', 'error');
    }

    btn.textContent = 'Retrain Models';
    btn.disabled = false;
    refreshML();
}

function renderMLMetrics(m) {
    const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
    el('ml-anomaly-rate', m.anomaly_rate != null ? m.anomaly_rate + '%' : '--');
    el('ml-total-preds', m.total_predictions || 0);
    el('ml-clf-status', m.classifier_trained ? '✅ Yes' : '❌ No');
    el('ml-if-status', m.unsupervised_trained ? '✅ Yes' : '❌ No');
}

function renderBusinessImpact(b) {
    const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
    el('biz-incidents', b.critical_incidents_caught || 0);
    el('biz-velocity', b.velocity_warnings || 0);
    el('biz-potential-loss', '$' + (b.potential_loss_without_guardx || 0).toLocaleString());
    el('biz-savings', '$' + (b.estimated_savings_usd || 0).toLocaleString());
}

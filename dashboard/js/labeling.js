/* ─── Fault Labeling Page ─── */

async function refreshLabeling() {
    const [labels, count] = await Promise.all([
        apiFetch('/api/v1/labels?limit=50'),
        apiFetch('/api/v1/labels/count'),
    ]);

    if (labels) renderLabelsTable(labels);
    if (count) {
        const badge = document.getElementById('label-count-badge');
        if (badge) badge.textContent = `${count.count} labels`;
    }
}

async function submitLabel(event) {
    event.preventDefault();
    const statusEl = document.getElementById('label-status');

    const data = {
        start_timestamp: document.getElementById('label-start').value,
        end_timestamp: document.getElementById('label-end').value,
        fault_type: document.getElementById('label-type').value,
        severity: document.getElementById('label-severity').value,
        notes: document.getElementById('label-notes').value,
        labeled_by: 'operator',
    };

    statusEl.textContent = 'Submitting...';
    statusEl.style.color = '#9CA3AF';

    const result = await apiPost('/api/v1/labels', data);

    if (result && result.status === 'ok') {
        statusEl.textContent = 'Label saved!';
        statusEl.style.color = '#00E676';
        showToast('Fault label submitted', 'success');
        document.getElementById('label-form').reset();
        refreshLabeling();
    } else {
        statusEl.textContent = 'Error saving label';
        statusEl.style.color = '#FF1744';
        showToast('Failed to save label', 'error');
    }

    setTimeout(() => { statusEl.textContent = ''; }, 3000);
}

function renderLabelsTable(labels) {
    const tbody = document.getElementById('labels-body');
    if (!labels || labels.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="no-data">No labels yet. Label anomaly events to improve ML predictions.</td></tr>';
        return;
    }

    tbody.innerHTML = labels.map(l => `
        <tr>
            <td>${formatTime(l.start_timestamp)}</td>
            <td>${formatTime(l.end_timestamp)}</td>
            <td><span class="severity-${l.severity}">${l.fault_type.replace('_', ' ')}</span></td>
            <td>${l.severity}</td>
            <td>${l.notes || '--'}</td>
        </tr>
    `).join('');
}

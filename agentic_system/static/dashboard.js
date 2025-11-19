// Dashboard API Configuration
const API_BASE_URL = 'http://localhost:8001';

// Load dashboard data
async function loadDashboard() {
    try {
        // Load guardrail metrics
        const guardrailResponse = await fetch(`${API_BASE_URL}/guardrails/metrics`);
        const guardrailData = await guardrailResponse.json();
        
        if (guardrailData.success) {
            updateGuardrailMetrics(guardrailData.metrics);
            updateViolationsByType(guardrailData.metrics.violations_by_type || {});
            updateViolationsBySeverity(guardrailData.metrics.violations_by_severity || {});
            updateRecentViolations(guardrailData.recent_violations || []);
        }
        
        // Load security metrics
        const securityResponse = await fetch(`${API_BASE_URL}/security/metrics`);
        const securityData = await securityResponse.json();
        
        if (securityData.success) {
            updateSecurityAlerts(securityData.security_alerts || []);
        }
        
        // Update last update time
        document.getElementById('last-update').textContent = 
            `Last update: ${new Date().toLocaleTimeString()}`;
            
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showError('Failed to load dashboard data. Make sure the dashboard server is running on port 8001.');
    }
}

// Update guardrail metrics
function updateGuardrailMetrics(metrics) {
    document.getElementById('total-violations').textContent = metrics.total_violations || 0;
    document.getElementById('critical-violations').textContent = metrics.critical_violations || 0;
    document.getElementById('high-violations').textContent = metrics.high_violations || 0;
    
    // Update status indicators
    document.getElementById('pii-status').className = 
        `status-dot ${metrics.pii_detection_enabled ? 'active' : 'inactive'}`;
    document.getElementById('content-status').className = 
        `status-dot ${metrics.content_moderation_enabled ? 'active' : 'inactive'}`;
    document.getElementById('rate-status').className = 
        `status-dot ${metrics.rate_limiting_enabled ? 'active' : 'inactive'}`;
}

// Update violations by type chart
function updateViolationsByType(violationsByType) {
    const container = document.getElementById('violations-by-type');
    
    if (Object.keys(violationsByType).length === 0) {
        container.innerHTML = '<div class="empty-state">No violations yet</div>';
        return;
    }
    
    const maxValue = Math.max(...Object.values(violationsByType));
    
    let html = '<div class="bar-chart">';
    for (const [type, count] of Object.entries(violationsByType)) {
        const percentage = maxValue > 0 ? (count / maxValue) * 100 : 0;
        html += `
            <div class="bar-item">
                <div class="bar-label">${formatViolationType(type)}</div>
                <div class="bar-wrapper">
                    <div class="bar-fill" style="width: ${percentage}%">${count}</div>
                </div>
            </div>
        `;
    }
    html += '</div>';
    container.innerHTML = html;
}

// Update violations by severity chart
function updateViolationsBySeverity(violationsBySeverity) {
    const container = document.getElementById('violations-by-severity');
    
    if (Object.keys(violationsBySeverity).length === 0) {
        container.innerHTML = '<div class="empty-state">No violations yet</div>';
        return;
    }
    
    const maxValue = Math.max(...Object.values(violationsBySeverity));
    
    let html = '<div class="bar-chart">';
    for (const [severity, count] of Object.entries(violationsBySeverity)) {
        const percentage = maxValue > 0 ? (count / maxValue) * 100 : 0;
        html += `
            <div class="bar-item">
                <div class="bar-label">${severity}</div>
                <div class="bar-wrapper">
                    <div class="bar-fill" style="width: ${percentage}%">${count}</div>
                </div>
            </div>
        `;
    }
    html += '</div>';
    container.innerHTML = html;
}

// Update recent violations list
function updateRecentViolations(violations) {
    const container = document.getElementById('recent-violations');
    
    if (violations.length === 0) {
        container.innerHTML = '<div class="empty-state">No violations yet</div>';
        return;
    }
    
    let html = '<table class="violations-table"><thead><tr>' +
        '<th>Type</th><th>Severity</th><th>User</th><th>Session ID</th><th>Query</th><th>Description</th><th>Timestamp</th>' +
        '</tr></thead><tbody>';
    
    violations.reverse().forEach(violation => {
        const severity = violation.severity || 'LOW';
        const severityClass = severity.toLowerCase();
        const username = violation.username || violation.user || 'Unknown';
        const sessionId = violation.session_id || 'N/A';
        const query = violation.query || violation.user_message || 'N/A';
        const description = violation.description || 'No description';
        
        html += `
            <tr class="violation-row ${severityClass}">
                <td><span class="violation-type">${formatViolationType(violation.violation_type)}</span></td>
                <td><span class="violation-severity severity-${severityClass}">${severity}</span></td>
                <td>${escapeHtml(username)}</td>
                <td><code class="session-id">${escapeHtml(sessionId)}</code></td>
                <td><div class="query-text" data-full-query="${escapeHtml(query)}" title="${escapeHtml(query)}">${escapeHtml(truncateText(query, 50))}</div></td>
                <td>${escapeHtml(description)}</td>
                <td>${formatTimestamp(violation.timestamp || violation.recorded_at)}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Truncate text with ellipsis
function truncateText(text, maxLength) {
    if (!text || text.length <= maxLength) return text || '';
    return text.substring(0, maxLength) + '...';
}

// Update security alerts list
function updateSecurityAlerts(alerts) {
    const container = document.getElementById('security-alerts');
    
    if (alerts.length === 0) {
        container.innerHTML = '<div class="empty-state">No security alerts</div>';
        return;
    }
    
    let html = '';
    alerts.forEach(alert => {
        html += `
            <div class="alert-item">
                <div class="alert-header">
                    <span class="alert-type">${alert.type || 'Security Alert'}</span>
                    <span class="violation-severity severity-${(alert.severity || 'low').toLowerCase()}">${alert.severity || 'LOW'}</span>
                </div>
                <div class="violation-description">${alert.message || alert.description || 'No description'}</div>
                <div class="violation-timestamp">${formatTimestamp(alert.timestamp)}</div>
            </div>
        `;
    });
    container.innerHTML = html;
}

// Format violation type for display
function formatViolationType(type) {
    if (!type) return 'Unknown';
    return type
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');
}

// Format timestamp for display
function formatTimestamp(timestamp) {
    if (!timestamp) return 'Unknown time';
    try {
        const date = new Date(timestamp);
        return date.toLocaleString();
    } catch (e) {
        return timestamp;
    }
}

// Show error message
function showError(message) {
    const container = document.querySelector('.container');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.style.cssText = `
        background: #f44336;
        color: white;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        text-align: center;
    `;
    errorDiv.textContent = message;
    container.insertBefore(errorDiv, container.firstChild);
    
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

// Auto-refresh every 5 seconds
setInterval(loadDashboard, 5000);

// Load dashboard on page load
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
});


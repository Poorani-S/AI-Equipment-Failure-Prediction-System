// Admin Panel JavaScript - User management and system administration

let userEditModal;
let emailReportModal;
let AdminToast;   // Lazy-initialized after DOM ready so window.Toast is available
let AdminLoading;
let AdminAPI;

const setupAdminAutoRefresh = window.setupAutoRefresh || function(callback, interval) {
    callback();
    return setInterval(callback, interval);
};

document.addEventListener('DOMContentLoaded', function() {
    // Initialize after base.js has run — window.Toast is now guaranteed
    AdminToast = window.Toast || {
        success(msg) { console.log('[Toast]', msg); },
        error(msg)   { console.error('[Toast]', msg); },
        warning(msg) { console.warn('[Toast]', msg); },
    };
    AdminLoading = window.Loading || { show(el) { if(el) el.innerHTML = '<div class="spinner"></div>'; } };
    AdminAPI = window.API || {
        async get(url)       { return (await fetch(url)).json(); },
        async post(url, data){ return (await fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data) })).json(); },
    };

    console.log('DEBUG: Admin initializing modals...');
    try {
        userEditModal   = new Modal(document.getElementById('userEditModal'));
        emailReportModal = new Modal(document.getElementById('emailReportModal'));
        console.log('DEBUG: Modals initialized');
    } catch (e) {
        console.error('ERROR: Failed to initialize modals:', e);
    }

    // Load admin CSS
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = '/static/css/admin.css';
    document.head.appendChild(link);

    // Setup tab switching
    setupTabSwitching();

    // Auto-refresh data
    setupAdminAutoRefresh(refreshAdminData, 60000);

    // Load initial data
    loadUsers();
    loadAdminIntelligence();
});

// ── Admin visual feedback helper (non-destructive) ────────────
async function withAdminBtnFeedback(btn, loadingText, action, successMsg) {
    if (!btn) { try { await action(); } catch(e) {} return; }
    const orig = btn.innerHTML;
    btn.innerHTML = `⏳ ${loadingText}`;
    btn.disabled = true;
    btn.style.opacity = '0.75';
    try {
        await action();
        if (successMsg) AdminToast.success(successMsg);
    } catch (e) {
        AdminToast.error('Action failed: ' + (e.message || 'unknown error'));
        console.error(e);
    } finally {
        btn.innerHTML = orig;
        btn.disabled = false;
        btn.style.opacity = '';
    }
}

// Setup tab switching
function setupTabSwitching() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');

            // Remove active class from all
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Add active class
            this.classList.add('active');
            document.getElementById(`tab-${tabName}`).classList.add('active');
        });
    });
}

// Load all admin data
async function refreshAdminData() {
    loadUsers();
    loadAdminIntelligence();
}

// Load users
async function loadUsers() {
    try {
        const tbody = document.querySelector('#usersTable tbody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #00d4ff;">⏳ Loading...</td></tr>';
        }

        const response = await AdminAPI.get('/admin/api/users');
        if (response.success) {
            displayUsers(response.data);
        } else {
            AdminToast.error('Failed to load users');
        }
    } catch (error) {
        console.error('Error loading users:', error);
        AdminToast.error('Error loading users');
    }
}

// Display users in table
function displayUsers(users) {
    const tbody = document.querySelector('#usersTable tbody');
    if (!tbody) return;

    tbody.innerHTML = users.map(user => `
        <tr>
            <td>${user.username}</td>
            <td>${user.email}</td>
            <td><span class="role-badge role-${user.role.toLowerCase()}">${user.role}</span></td>
            <td>${new Date(user.created_at).toLocaleDateString()}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="editUser('${user.id}')">Edit</button>
                <button class="btn btn-sm btn-danger" onclick="deleteUser('${user.id}', '${user.username}')">Delete</button>
            </td>
        </tr>
    `).join('');
}

// Edit user
async function editUser(userId) {
    try {
        const response = await AdminAPI.get(`/admin/api/user/${userId}`);
        if (response.success) {
            const user = response.data;
            document.getElementById('editUserId').value = user.id;
            document.getElementById('editUsername').value = user.username;
            document.getElementById('editEmail').value = user.email;
            document.getElementById('editRole').value = user.role;

            userEditModal.open();
        }
    } catch (error) {
        console.error('Error loading user:', error);
        AdminToast.error('Error loading user details');
    }
}

// Save user changes
async function saveUserChanges() {
    try {
        const userId = document.getElementById('editUserId').value;
        const role = document.getElementById('editRole').value;

        const response = await AdminAPI.post(`/admin/api/user/${userId}`, {
            role: role
        });

        if (response.success) {
            AdminToast.success('User updated successfully');
            userEditModal.close();
            loadUsers();
        } else {
            AdminToast.error('Failed to update user');
        }
    } catch (error) {
        console.error('Error saving user:', error);
        AdminToast.error('Error saving changes');
    }
}

// Delete user
async function deleteUser(userId, username) {
    if (!confirm(`Are you sure you want to delete user "${username}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await AdminAPI.post(`/admin/api/user/${userId}/delete`, {});
        if (response.success) {
            AdminToast.success('User deleted successfully');
            loadUsers();
        } else {
            AdminToast.error('Failed to delete user');
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        AdminToast.error('Error deleting user');
    }
}

// Load analytics
function openEmailReportForm() {
    emailReportModal.open();
}

async function createUser() {
    try {
        const payload = {
            username: document.getElementById('newUserUsername').value.trim(),
            email: document.getElementById('newUserEmail').value.trim(),
            password: document.getElementById('newUserPassword').value,
            role: document.getElementById('newUserRole').value,
        };

        if (!payload.username) {
            AdminToast.error('Username is required');
            return;
        }

        if (!payload.email) {
            AdminToast.error('Email is required');
            return;
        }

        if (!payload.password) {
            AdminToast.error('Password is required');
            return;
        }

        const response = await AdminAPI.post('/admin/api/users', payload);
        if (response.success) {
            AdminToast.success('User created successfully');
            document.getElementById('newUserUsername').value = '';
            document.getElementById('newUserEmail').value = '';
            document.getElementById('newUserPassword').value = '';
            loadUsers();
        } else {
            AdminToast.error(response.error || 'Failed to create user');
        }
    } catch (error) {
        console.error('Error creating user:', error);
        AdminToast.error('Error creating user');
    }
}

function downloadPdfReport() {
    const btn = document.querySelector('[onclick="downloadPdfReport()"]');
    if (btn) { btn.innerHTML = '⏳ Generating PDF...'; btn.disabled = true; }
    window.location.href = '/admin/api/export/pdf';
    setTimeout(() => { if (btn) { btn.innerHTML = '📄 Export PDF'; btn.disabled = false; } }, 4000);
}

async function sendReportEmail() {
    const btn = document.getElementById('sendReportBtn');
    await withAdminBtnFeedback(btn, 'Sending...', async () => {
        const recipient = (document.getElementById('reportRecipient').value || '').trim();
        if (!recipient) {
            throw new Error('Recipient email is required');
        }
        const response = await AdminAPI.post('/admin/api/reports/email', { recipient });
        if (!response.success) {
            throw new Error(response.error || 'Failed to send report');
        }
    }, '✅ Report sent successfully');
    
    if (emailReportModal) emailReportModal.close();
}

async function loadAdminIntelligence() {
    try {
        const response = await AdminAPI.get('/admin/api/intelligence');
        if (!response.success) {
            throw new Error(response.error || 'Failed to load intelligence');
        }
        renderAdminIntelligence(response.data || {});
    } catch (error) {
        console.error('Error loading admin intelligence:', error);
        AdminToast.error('Error loading intelligence');
    }
}

function renderAdminIntelligence(data) {
    const monitoring = data.model_monitoring || {};
    const fleet = (data.platform && data.platform.fleet) || {};
    const auditLog = data.audit_log || [];

    const avgConfidence = document.getElementById('intelAvgConfidence');
    const predictionVolume = document.getElementById('intelPredictionVolume');
    const alertVolume = document.getElementById('intelAlertVolume');
    const fleetStability = document.getElementById('intelFleetStability');
    const adminFleetSummary = document.getElementById('adminFleetSummary');
    const adminAuditLog = document.getElementById('adminAuditLog');

    if (avgConfidence) avgConfidence.textContent = `${monitoring.average_prediction_confidence ?? '--'}%`;
    if (predictionVolume) predictionVolume.textContent = monitoring.prediction_volume_24h ?? '--';
    if (alertVolume) alertVolume.textContent = monitoring.alert_volume ?? '--';
    if (fleetStability) fleetStability.textContent = `${fleet.fleet_stability_score ?? '--'}%`;

    if (adminFleetSummary) {
        const topMachines = (fleet.top_risky_machines || []).slice(0, 5);
        adminFleetSummary.innerHTML = topMachines.length
            ? topMachines.map(item => `
                <div class="admin-audit-item severity-${(item.risk_level || 'low').toLowerCase()}">
                    <span class="admin-audit-category">${item.risk_level || 'Low'}</span>
                    <strong>${item.name || item.equipment_id}</strong>
                    <p>Health score: ${item.health_score ?? '--'}%</p>
                </div>
            `).join('')
            : '<div class="admin-empty-state">No fleet data available.</div>';
    }

    if (adminAuditLog) {
        adminAuditLog.innerHTML = auditLog.length
            ? auditLog.map(item => `
                <div class="admin-audit-item severity-${(item.severity || 'info').toLowerCase()}">
                    <span class="admin-audit-category">${item.category || 'event'}</span>
                    <strong>${item.message}</strong>
                    <p>${formatAdminTime(item.timestamp)}</p>
                </div>
            `).join('')
            : '<div class="admin-empty-state">No audit entries yet.</div>';
    }
}

function formatAdminTime(timestamp) {
    try {
        return new Date(timestamp).toLocaleString();
    } catch (error) {
        return timestamp || '';
    }
}

function downloadIntelligenceJson() {
    window.location.href = '/admin/api/export/intelligence';
}

function downloadIntelligencePdf() {
    window.location.href = '/admin/api/export/intelligence/pdf';
}

// Export data
async function exportData() {
    const btn = document.querySelector('[onclick="exportData()"]');
    await withAdminBtnFeedback(btn, 'Exporting...', async () => {
        const response = await fetch('/admin/api/export', { method: 'GET' });
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `admin-export-${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            throw new Error('Export request failed');
        }
    }, 'Data exported successfully');
}

console.log('✅ Admin JavaScript loaded');

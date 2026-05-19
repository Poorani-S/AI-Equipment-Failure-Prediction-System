/*=== Enhanced Enterprise Dashboard UI - All New Panels & Features ===*/

// Wait for DOM to load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initEnhancedUI);
} else {
    initEnhancedUI();
}

function initEnhancedUI() {
    console.log('Initializing enhanced UI panels...');
    
    // Add all missing panels to the dashboard with error boundaries
    const runSafe = (fn, name) => {
        try {
            fn();
            console.log(`✅ Loaded ${name}`);
        } catch (e) {
            console.error(`❌ Failed to initialize ${name}:`, e);
        }
    };

    runSafe(injectAIChatPanel, 'AI Chat Panel');
    runSafe(injectAnomalyDetectionPanel, 'Anomaly Panel');
    runSafe(injectComparisonModeToggle, 'Comparison Toggle');
    runSafe(injectAdvancedSearchPanel, 'Advanced Search');
    runSafe(injectCostEstimationWidget, 'Cost Estimation Widget');
    runSafe(injectPerformanceMonitoringPanel, 'Performance Panel');
    runSafe(injectAnimatedSensorSimulation, 'Sensor Simulation');
    runSafe(injectLiveAlertCenter, 'Live Alert Center');
    runSafe(initializeEnhancedCharts, 'Enhanced Charts');
    runSafe(enableAnimatedEquipmentCards, 'Animated Cards');
    runSafe(setupMobileResponsiveness, 'Mobile Responsiveness');
}

// ========== AI CHAT PANEL ==========
function injectAIChatPanel() {
    const chatHTML = `
        <div id="aiChatPanel" class="side-panel side-panel-chat">
            <div class="side-panel-header">
                <h3>🤖 AI Assistant</h3>
                <button class="side-panel-close" onclick="toggleSidePanel('aiChatPanel')">✕</button>
            </div>
            <div class="chat-messages" id="chatMessages">
                <div class="chat-message chat-ai">Hello I'm Prediction Assistant, how can I help u?</div>
            </div>
            <div class="chat-input-area">
                <input type="text" id="chatInput" placeholder="Ask about equipment..." class="chat-input">
                <button onclick="sendChatMessage()" class="btn btn-primary btn-sm">Send</button>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', chatHTML);
    
    // Add chat button to header
    const headerControls = document.querySelector('.header-controls');
    if (headerControls) {
        const chatBtn = document.createElement('button');
        chatBtn.className = 'btn btn-secondary';
        chatBtn.innerHTML = '🤖 Chat';
        chatBtn.onclick = () => toggleSidePanel('aiChatPanel');
        headerControls.appendChild(chatBtn);
    }
    
    // Add chat input listener
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendChatMessage();
        });
    }
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const messages = document.getElementById('chatMessages');
    const msg = input.value.trim();
    
    if (!msg) return;
    
    // Add user message
    const userMsg = document.createElement('div');
    userMsg.className = 'chat-message chat-user';
    userMsg.textContent = msg;
    messages.appendChild(userMsg);
    input.value = '';
    messages.scrollTop = messages.scrollHeight;
    
    // Get AI response
    try {
        const response = await fetch('/dashboard/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg, context: { equipment_id: window.currentEquipmentId || '' } })
        });
        const data = await response.json();
        
        if (data.success) {
            const aiMsg = document.createElement('div');
            aiMsg.className = 'chat-message chat-ai';
            
            let formattedResponse = data.response || '';
            if (typeof marked === 'function') {
                formattedResponse = marked(formattedResponse);
            } else if (typeof marked === 'object' && typeof marked.parse === 'function') {
                formattedResponse = marked.parse(formattedResponse);
            } else {
                // simple fallback: replace markdown bolding, lists and newlines
                formattedResponse = formattedResponse
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>')
                    .replace(/^\s*[-*]\s+(.*)$/gm, '<li>$1</li>')
                    .replace(/<\/li>\n<li>/g, '</li><li>')
                    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
                    .replace(/\n/g, '<br>');
            }
            
            aiMsg.innerHTML = formattedResponse;
            messages.appendChild(aiMsg);
        }
    } catch (e) {
        console.error('Chat error:', e);
    }
    
    messages.scrollTop = messages.scrollHeight;
}

// ========== ANOMALY DETECTION PANEL ==========
function injectAnomalyDetectionPanel() {
    const anomalyHTML = `
        <div id="anomalyPanel" class="analytics-section" style="display:none; margin-top:1.5rem;">
            <div class="analytics-header">
                <div>
                    <span class="section-eyebrow">Anomaly Detection</span>
                    <h2>Unusual Behavior & Pattern Analysis</h2>
                </div>
                <button class="btn btn-primary" onclick="refreshAnomalyDetection()">🔄 Refresh</button>
            </div>
            <div id="anomalyContent" class="analytics-body">
                <div class="distribution-empty">Loading anomaly analysis...</div>
            </div>
        </div>
    `;
    
    const header = document.querySelector('.dashboard-header');
    if (header) { header.insertAdjacentHTML('afterend', anomalyHTML); } else { (document.querySelector('.dashboard-container') || document.body).insertAdjacentHTML('afterbegin', anomalyHTML); }
    
    // Add anomaly button
    const headerControls = document.querySelector('.header-controls');
    if (headerControls) {
        const anomalyBtn = document.createElement('button');
        anomalyBtn.className = 'btn btn-secondary';
        anomalyBtn.innerHTML = '⚠️ Anomalies';
        anomalyBtn.onclick = () => {
            const panel = document.getElementById('anomalyPanel');
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
            if (panel.style.display === 'block') {
                panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                refreshAnomalyDetection();
                if (typeof setDashboardActiveTab === 'function') setDashboardActiveTab('anomalies');
            } else {
                if (typeof setDashboardActiveTab === 'function') setDashboardActiveTab('normal');
            }
        };
        headerControls.appendChild(anomalyBtn);
    }
}

async function refreshAnomalyDetection() {
    try {
        let equipId = window.currentEquipmentId;
        if (!equipId) {
            const firstCard = document.querySelector('.equipment-card');
            if (firstCard) {
                equipId = firstCard.getAttribute('data-equipment-id');
                window.currentEquipmentId = equipId;
                firstCard.classList.add('selected');
            }
        }
        if (!equipId) {
            document.getElementById('anomalyContent').innerHTML = '<div class="distribution-empty">Select equipment to analyze anomalies</div>';
            return;
        }
        
        const response = await fetch(`/dashboard/api/anomalies/${equipId}`);
        const data = await response.json();
        
        if (data.success) {
            const anomalies = data.data.anomalies || [];
            let html = `<div class="intel-card"><strong>Severity: ${data.data.severity.toUpperCase()}</strong><p>Score: ${data.data.score}%</p>`;
            
            if (anomalies.length === 0) {
                html += '<p>✅ No anomalies detected</p>';
            } else {
                html += '<div class="intel-stack">';
                anomalies.forEach(anom => {
                    html += `<div class="intel-card"><strong>${anom.type}</strong><p>${anom.message}</p></div>`;
                });
                html += '</div>';
            }
            html += '</div>';
            
            document.getElementById('anomalyContent').innerHTML = html;
        }
    } catch (e) {
        console.error('Anomaly detection error:', e);
    }
}

// ========== COMPARISON MODE ==========
function injectComparisonModeToggle() {
    const comparisonHTML = `
        <div id="comparisonPanel" class="analytics-section" style="display:none; margin-top:1.5rem;">
            <div class="analytics-header">
                <div>
                    <span class="section-eyebrow">Equipment Comparison</span>
                    <h2>Side-by-Side Equipment Analysis</h2>
                </div>
                <button class="btn btn-primary" onclick="performComparison()">Compare</button>
            </div>
            <div id="comparisonContent" class="analytics-body">
                <div class="distribution-empty">Select equipment to compare or click Compare button</div>
            </div>
        </div>
    `;
    
    const header = document.querySelector('.dashboard-header');
    if (header) { header.insertAdjacentHTML('afterend', comparisonHTML); } else { (document.querySelector('.dashboard-container') || document.body).insertAdjacentHTML('afterbegin', comparisonHTML); }
    
    const headerControls = document.querySelector('.header-controls');
    if (headerControls) {
        const compBtn = document.createElement('button');
        compBtn.className = 'btn btn-secondary';
        compBtn.innerHTML = '⚖️ Compare';
        compBtn.onclick = () => {
            const panel = document.getElementById('comparisonPanel');
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
            if (panel.style.display === 'block') {
                panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                performComparison();
                if (typeof setDashboardActiveTab === 'function') setDashboardActiveTab('compare');
            } else {
                if (typeof setDashboardActiveTab === 'function') setDashboardActiveTab('normal');
            }
        };
        headerControls.appendChild(compBtn);
    }
    
    window.comparisonMode = { selected: [] };
}

async function performComparison() {
    if (!window.comparisonMode.selected || window.comparisonMode.selected.length < 2) {
        alert('Please select at least 2 equipment to compare');
        return;
    }
    
    try {
        const response = await fetch('/dashboard/api/comparison', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ equipment_ids: window.comparisonMode.selected })
        });
        const data = await response.json();
        
        if (data.success) {
            let html = '<div class="analytics-insight-card">';
            data.data.data.forEach(eq => {
                html += `
                    <div class="intel-card">
                        <strong>${eq.equipment_name}</strong>
                        <div class="intel-metric"><span>Health</span><span>${eq.health_score}%</span></div>
                        <div class="intel-metric"><span>Risk</span><span>${eq.risk_level}</span></div>
                        <div class="intel-metric"><span>24h Forecast</span><span>${eq.forecast_24h}%</span></div>
                    </div>
                `;
            });
            html += '</div>';
            document.getElementById('comparisonContent').innerHTML = html;
        }
    } catch (e) {
        console.error('Comparison error:', e);
    }
}

// ========== ADVANCED SEARCH PANEL ==========
function injectAdvancedSearchPanel() {
    const searchHTML = `
        <div id="advancedSearchPanel" class="side-panel side-panel-search">
            <div class="side-panel-header">
                <h3>🔍 Advanced Search</h3>
                <button class="side-panel-close" onclick="toggleSidePanel('advancedSearchPanel')">✕</button>
            </div>
            <div class="search-filters">
                <div class="filter-group">
                    <label>Risk Level</label>
                    <select id="filterRisk" multiple>
                        <option>Low</option>
                        <option>Medium</option>
                        <option>High</option>
                        <option>Critical</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Status</label>
                    <select id="filterStatus" multiple>
                        <option>online</option>
                        <option>warning</option>
                        <option>critical</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Health Score Range</label>
                    <input type="range" id="filterHealth" min="0" max="100" step="10">
                    <span id="healthValue">50%</span>
                </div>
                <button class="btn btn-primary" onclick="applyAdvancedSearch()">Apply Filters</button>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', searchHTML);
    
    // Wire up real-time filters
    setTimeout(() => {
        const filterRiskEl = document.getElementById('filterRisk');
        const filterStatusEl = document.getElementById('filterStatus');
        const filterHealthEl = document.getElementById('filterHealth');
        const healthValueEl = document.getElementById('healthValue');
        
        if (filterHealthEl && healthValueEl) {
            filterHealthEl.addEventListener('input', () => {
                healthValueEl.textContent = `${filterHealthEl.value}%`;
                applyAdvancedSearch();
            });
        }
        if (filterRiskEl) {
            filterRiskEl.addEventListener('change', applyAdvancedSearch);
        }
        if (filterStatusEl) {
            filterStatusEl.addEventListener('change', applyAdvancedSearch);
        }
    }, 100);
    
    const headerControls = document.querySelector('.header-controls');
    if (headerControls) {
        const searchBtn = document.createElement('button');
        searchBtn.className = 'btn btn-secondary';
        searchBtn.innerHTML = '🔍 Advanced';
        searchBtn.onclick = () => toggleSidePanel('advancedSearchPanel');
        headerControls.appendChild(searchBtn);
    }
}

async function applyAdvancedSearch() {
    const filterRiskEl = document.getElementById('filterRisk');
    const filterStatusEl = document.getElementById('filterStatus');
    const filterHealthEl = document.getElementById('filterHealth');
    
    if (!filterRiskEl || !filterStatusEl || !filterHealthEl) return;
    
    const risk = Array.from(filterRiskEl.selectedOptions).map(o => o.value);
    const status = Array.from(filterStatusEl.selectedOptions).map(o => o.value);
    const health = filterHealthEl.value;
    
    try {
        const response = await fetch(`/dashboard/api/search?health_score_min=${health}&risk_levels=${risk.join(',')}&status=${status.join(',')}`, {
            method: 'GET'
        });
        const data = await response.json();
        
        const toast = window.Toast || { success: console.log, error: console.error };
        if (data.success) {
            window.filteredEquipment = data.data.data;
            console.log(`Found ${data.data.returned_results} equipment matching filters`);
            toast.success(`Found ${data.data.returned_results} equipment`);
            
            // Re-render the cards with the filtered results immediately!
            if (typeof renderEquipmentCards === 'function') {
                renderEquipmentCards(window.filteredEquipment);
            }
            
            // Update the top summary cards dynamically!
            if (window.dashboardState) {
                window.dashboardState.filteredEquipment = window.filteredEquipment;
                if (typeof setDashboardActiveTab === 'function') {
                    setDashboardActiveTab('advanced');
                }
            }
        }
    } catch (e) {
        console.error('Search error:', e);
    }
}

// ========== COST ESTIMATION WIDGET ==========
function injectCostEstimationWidget() {
    const costHTML = `
        <div id="costPanel" class="analytics-section" style="display:none; margin-top:1.5rem;">
            <div class="analytics-header">
                <div>
                    <span class="section-eyebrow">Financial Impact</span>
                    <h2>Downtime & Maintenance Cost Estimation</h2>
                </div>
                <button class="btn btn-primary" onclick="refreshCostEstimation()">💰 Calculate</button>
            </div>
            <div id="costContent" class="analytics-body">
                <div class="distribution-empty">Loading cost analysis...</div>
            </div>
        </div>
    `;
    
    const header = document.querySelector('.dashboard-header');
    if (header) { header.insertAdjacentHTML('afterend', costHTML); } else { (document.querySelector('.dashboard-container') || document.body).insertAdjacentHTML('afterbegin', costHTML); }
    
    const headerControls = document.querySelector('.header-controls');
    if (headerControls) {
        const costBtn = document.createElement('button');
        costBtn.className = 'btn btn-secondary';
        costBtn.innerHTML = '💰 Cost';
        costBtn.onclick = () => {
            const panel = document.getElementById('costPanel');
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
            if (panel.style.display === 'block') {
                panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                refreshCostEstimation();
                if (typeof setDashboardActiveTab === 'function') setDashboardActiveTab('cost');
            } else {
                if (typeof setDashboardActiveTab === 'function') setDashboardActiveTab('normal');
            }
        };
        headerControls.appendChild(costBtn);
    }
}

async function refreshCostEstimation() {
    try {
        let equipId = window.currentEquipmentId;
        if (!equipId) {
            const firstCard = document.querySelector('.equipment-card');
            if (firstCard) {
                equipId = firstCard.getAttribute('data-equipment-id');
                window.currentEquipmentId = equipId;
                firstCard.classList.add('selected');
            }
        }
        if (!equipId) {
            document.getElementById('costContent').innerHTML = '<div class="distribution-empty">Select equipment for cost analysis</div>';
            return;
        }
        
        const response = await fetch(`/dashboard/api/cost/${equipId}`);
        const data = await response.json();
        
        if (data.success) {
            const cost = data.data;
            let html = `
                <div class="analytics-chart-card">
                    <strong>💰 Financial Impact for ${cost.equipment_name}</strong>
                    <div class="intel-metric"><span>Estimated Downtime</span><span>${cost.estimated_downtime_hours}h</span></div>
                    <div class="intel-metric"><span>Downtime Cost</span><span>₹${cost.downtime_cost}</span></div>
                    <div class="intel-metric"><span>Maintenance Cost</span><span>₹${cost.maintenance_cost}</span></div>
                    <div class="intel-metric"><span>Replacement Risk</span><span>₹${cost.replacement_risk_cost}</span></div>
                    <div class="intel-metric" style="border-top:2px solid var(--primary-blue); margin-top:0.5rem; padding-top:0.5rem;">
                        <strong>Total Risk Cost</strong><strong style="color:var(--danger);">₹${cost.total_estimated_cost}</strong>
                    </div>
                    <p style="margin-top:1rem; color:var(--text-secondary);">${cost.recommendation}</p>
                </div>
            `;
            document.getElementById('costContent').innerHTML = html;
        }
    } catch (e) {
        console.error('Cost estimation error:', e);
    }
}

// ========== PERFORMANCE MONITORING PANEL ==========
function injectPerformanceMonitoringPanel() {
    const perfHTML = `
        <div id="perfMonitorPanel" class="analytics-section" style="display:none; margin-top:1.5rem;">
            <div class="analytics-header">
                <div>
                    <span class="section-eyebrow">System Performance</span>
                    <h2>API & Database Monitoring</h2>
                </div>
            </div>
            <div class="analytics-spotlights">
                <article class="analytics-spotlight">
                    <span>API Response Time</span>
                    <strong id="apiResponseTime">--</strong>
                    <p>milliseconds</p>
                </article>
                <article class="analytics-spotlight">
                    <span>Active Users</span>
                    <strong id="activeUsers">--</strong>
                    <p>concurrent</p>
                </article>
                <article class="analytics-spotlight">
                    <span>System Uptime</span>
                    <strong id="systemUptime">--</strong>
                    <p>percentage</p>
                </article>
            </div>
        </div>
    `;
    
    const header = document.querySelector('.dashboard-header');
    if (header) { header.insertAdjacentHTML('afterend', perfHTML); } else { (document.querySelector('.dashboard-container') || document.body).insertAdjacentHTML('afterbegin', perfHTML); }
    
    const headerControls = document.querySelector('.header-controls');
    if (headerControls) {
        const perfBtn = document.createElement('button');
        perfBtn.className = 'btn btn-secondary';
        perfBtn.innerHTML = '📊 Performance';
        perfBtn.onclick = () => {
            const panel = document.getElementById('perfMonitorPanel');
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
            if (panel.style.display === 'block') {
                panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                updatePerformanceMetrics();
                if (typeof setDashboardActiveTab === 'function') setDashboardActiveTab('performance');
            } else {
                if (typeof setDashboardActiveTab === 'function') setDashboardActiveTab('normal');
            }
        };
        headerControls.appendChild(perfBtn);
    }
}

function updatePerformanceMetrics() {
    // Simulate performance metrics (would be real in production)
    document.getElementById('apiResponseTime').textContent = (Math.random() * 150 + 50).toFixed(0);
    document.getElementById('activeUsers').textContent = Math.floor(Math.random() * 50 + 5);
    document.getElementById('systemUptime').textContent = (99.9 + Math.random() * 0.1).toFixed(1) + '%';
}

// ========== ANIMATED SENSOR SIMULATION ==========
function injectAnimatedSensorSimulation() {
    const sensorHTML = `
        <div id="sensorSimPanel" class="analytics-section" style="display:none; margin-top:1.5rem;">
            <div class="analytics-header">
                <div>
                    <span class="section-eyebrow">Live Sensors</span>
                    <h2>Real-Time Sensor Simulation</h2>
                </div>
            </div>
            <div class="analytics-spotlights" id="sensorSpotlights">
                <article class="analytics-spotlight accent">
                    <span>🌡️ Temperature</span>
                    <strong id="sensorTemp">--°C</strong>
                </article>
                <article class="analytics-spotlight">
                    <span>📳 Vibration</span>
                    <strong id="sensorVib">--Hz</strong>
                </article>
                <article class="analytics-spotlight">
                    <span>⚙️ Pressure</span>
                    <strong id="sensorPress">--bar</strong>
                </article>
            </div>
        </div>
    `;
    
    const header = document.querySelector('.dashboard-header');
    if (header) { header.insertAdjacentHTML('afterend', sensorHTML); } else { (document.querySelector('.dashboard-container') || document.body).insertAdjacentHTML('afterbegin', sensorHTML); }
    
    // Auto-update sensors
    setInterval(updateSensorSimulation, 1000);
}

function updateSensorSimulation() {
    if (document.getElementById('sensorSimPanel').style.display !== 'none') {
        document.getElementById('sensorTemp').textContent = (Math.random() * 40 + 60).toFixed(1) + '°C';
        document.getElementById('sensorVib').textContent = (Math.random() * 5 + 2).toFixed(1) + 'Hz';
        document.getElementById('sensorPress').textContent = (Math.random() * 3 + 1.5).toFixed(1) + 'bar';
    }
}

// ========== LIVE ALERT CENTER ==========
function injectLiveAlertCenter() {
    const alertHTML = `
        <div id="alertCenterPanel" class="analytics-section" style="display:none; margin-top:1.5rem;">
            <div class="analytics-header">
                <div>
                    <span class="section-eyebrow">Live Alerts</span>
                    <h2>Critical System Warnings</h2>
                </div>
                <button class="btn btn-primary" onclick="refreshAlertCenter()">🔔 Refresh</button>
            </div>
            <div id="alertContent" class="intel-stack">
                <div class="distribution-empty">No active alerts</div>
            </div>
        </div>
    `;
    
    const header = document.querySelector('.dashboard-header');
    if (header) { header.insertAdjacentHTML('afterend', alertHTML); } else { (document.querySelector('.dashboard-container') || document.body).insertAdjacentHTML('afterbegin', alertHTML); }
    
    const headerControls = document.querySelector('.header-controls');
    if (headerControls) {
        const alertBtn = document.createElement('button');
        alertBtn.className = 'btn btn-secondary';
        alertBtn.innerHTML = '🔔 Alerts';
        alertBtn.onclick = () => {
            const panel = document.getElementById('alertCenterPanel');
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
            if (panel.style.display === 'block') {
                panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                refreshAlertCenter();
                if (typeof setDashboardActiveTab === 'function') setDashboardActiveTab('alerts');
            } else {
                if (typeof setDashboardActiveTab === 'function') setDashboardActiveTab('normal');
            }
        };
        headerControls.appendChild(alertBtn);
    }
}

async function refreshAlertCenter() {
    try {
        const response = await fetch('/dashboard/api/alerts');
        const data = await response.json();
        
        if (data.success && data.data.length > 0) {
            let html = '';
            data.data.forEach(alert => {
                html += `
                    <div class="intel-card" style="border-left:4px solid var(--danger); animation:pulse 2s infinite;">
                        <strong>${alert.severity}: ${alert.equipment_id}</strong>
                        <p>${alert.message}</p>
                        <button class="btn btn-sm btn-secondary" onclick="acknowledgeAlert('${alert.id}')">✓ Acknowledge</button>
                    </div>
                `;
            });
            document.getElementById('alertContent').innerHTML = html;
        } else {
            document.getElementById('alertContent').innerHTML = '<div class="distribution-empty">✅ No active alerts</div>';
        }
    } catch (e) {
        console.error('Alert fetch error:', e);
    }
}

function acknowledgeAlert(alertId) {
    Toast.success('Alert acknowledged');
}

// ========== ENHANCED CHARTS ==========
function initializeEnhancedCharts() {
    // Enhanced chart options would go here
    // Add zoom, hover, animations, etc.
    console.log('Enhanced charts initialized');
}

// ========== ANIMATED EQUIPMENT CARDS ==========
function enableAnimatedEquipmentCards() {
    // Add pulsing animation to critical cards
    const style = document.createElement('style');
    style.textContent = `
        @keyframes criticalpulse {
            0% { box-shadow: 0 0 0 0 rgba(255, 51, 51, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(255, 51, 51, 0); }
            100% { box-shadow: 0 0 0 0 rgba(255, 51, 51, 0); }
        }
        
        @keyframes glowborder {
            0%, 100% { border-color: var(--primary-blue); }
            50% { border-color: var(--primary-blue-glow); box-shadow: 0 0 8px var(--primary-blue-glow); }
        }
        
        @keyframes slidein {
            from { opacity: 0; transform: translateX(-20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        .equipment-card-critical {
            animation: criticalpulse 2s infinite;
        }
        
        .equipment-card {
            animation: slidein 0.3s ease-out;
            transition: all 0.3s ease;
        }
        
        .equipment-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
        }
    `;
    document.head.appendChild(style);
}

// ========== MOBILE RESPONSIVENESS ==========
function setupMobileResponsiveness() {
    if (window.innerWidth < 768) {
        document.documentElement.style.fontSize = '14px';
        document.querySelector('.dashboard-header').style.flexDirection = 'column';
    }
    
    window.addEventListener('resize', () => {
        if (window.innerWidth < 768) {
            // Hide side panels on mobile
            const sidePanels = document.querySelectorAll('.side-panel');
            sidePanels.forEach(p => p.style.display = 'none');
        }
    });
}

function toggleSidePanel(panelId) {
    const panel = document.getElementById(panelId);
    if (panel) {
        panel.classList.toggle('open');
        if (!panel.classList.contains('open')) {
            if (typeof setDashboardActiveTab === 'function') setDashboardActiveTab('normal');
        } else {
            if (panelId === 'advancedSearchPanel') {
                if (typeof setDashboardActiveTab === 'function') setDashboardActiveTab('advanced');
            } else if (panelId === 'aiChatPanel') {
                if (typeof setDashboardActiveTab === 'function') setDashboardActiveTab('chat');
            }
        }
    }
}

function toggleCompareEquipment(equipmentId, isChecked) {
    if (!window.comparisonMode) {
        window.comparisonMode = { selected: [] };
    }
    if (isChecked) {
        if (!window.comparisonMode.selected.includes(equipmentId)) {
            window.comparisonMode.selected.push(equipmentId);
        }
    } else {
        window.comparisonMode.selected = window.comparisonMode.selected.filter(id => id !== equipmentId);
    }
    console.log('Selected for comparison:', window.comparisonMode.selected);
}

console.log('✅ Enhanced UI module loaded');

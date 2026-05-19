// Base JavaScript functionality for the application

// Toast/Notification system
class Toast {
    static show(message, type = 'success', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#00ff88' : '#ff3333'};
            color: #0a0e27;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            z-index: 10000;
            animation: slideInRight 0.3s ease;
        `;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    static success(message) {
        this.show(message, 'success');
    }

    static error(message) {
        this.show(message, 'error', 4000);
    }

    static warning(message) {
        this.show(message, 'warning', 3500);
    }
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.body.setAttribute('data-theme', theme);
    
    const sunIconPath = `<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />`;
    const moonIconPath = `<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>`;
    
    document.querySelectorAll('[data-theme-toggle]').forEach((toggle) => {
        const thumbIcon = toggle.querySelector('.thumb-icon');
        if (thumbIcon) {
            thumbIcon.innerHTML = theme === 'light' ? sunIconPath : moonIconPath;
        }
        toggle.setAttribute('aria-pressed', theme === 'light' ? 'true' : 'false');
    });

    // Update Chart.js defaults if library is loaded
    if (window.Chart) {
        const isLight = theme === 'light';
        Chart.defaults.color = isLight ? '#4b5563' : '#9ca3af';
        Chart.defaults.scale.grid.color = isLight ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)';
        Chart.defaults.plugins.tooltip.backgroundColor = isLight ? 'rgba(255,255,255,0.95)' : 'rgba(17,24,39,0.95)';
        Chart.defaults.plugins.tooltip.titleColor = isLight ? '#111827' : '#f9fafb';
        Chart.defaults.plugins.tooltip.bodyColor = isLight ? '#374151' : '#d1d5db';
        Chart.defaults.plugins.tooltip.borderColor = isLight ? '#e5e7eb' : '#374151';
        Chart.defaults.plugins.tooltip.borderWidth = 1;
    }
    
    // Dispatch event for local page charts to re-render
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme } }));
}

function toggleTheme() {
    const currentTheme = document.body.getAttribute('data-theme') || 'dark';
    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
    applyTheme(nextTheme);
    window.localStorage.setItem('ai-equipment-theme', nextTheme);
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    .spinner {
        display: none;
    }
`;
document.head.appendChild(style);

// API utilities
class API {
    static async fetch(url, method = 'GET', data = null, silent = false) {
        const options = {
            method,
            headers: { 'Content-Type': 'application/json' },
        };
        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                let errorMsg = `API Error: ${response.status}`;
                try {
                    const errorData = await response.json();
                    if (errorData && errorData.error) errorMsg = errorData.error;
                } catch (e) {}
                throw new Error(errorMsg);
            }
            return await response.json();
        } catch (error) {
            console.warn('API Error:', url, error.message);
            if (!silent) Toast.error(`Action failed: ${error.message}`);
            throw error;
        }
    }

    static get(url) { return this.fetch(url, 'GET', null, false); }
    static getSilent(url) { return this.fetch(url, 'GET', null, true); }
    static post(url, data) { return this.fetch(url, 'POST', data, false); }
    static postSilent(url, data) { return this.fetch(url, 'POST', data, true); }
    static put(url, data) { return this.fetch(url, 'PUT', data, false); }
    static delete(url) { return this.fetch(url, 'DELETE', null, false); }
}

// Modal utilities
class Modal {
    constructor(element) {
        this.element = element;
        this.closeBtn = element ? element.querySelector('.modal-close') || element.querySelector('.close') : null;
        if (this.closeBtn) {
            this.closeBtn.onclick = () => this.close();
        }
        window.onclick = (event) => {
            if (this.element && event.target === this.element) {
                this.close();
            }
        };
    }

    open() {
        if (this.element) this.element.style.display = 'block';
    }

    close() {
        if (this.element) this.element.style.display = 'none';
    }
}

// Loading utilities
class Loading {
    static show(button) {
        if (!button) return;
        button.disabled = true;
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = '<span class="spinner"></span> ⏳ Sending...';
    }

    static hide(button) {
        if (!button) return;
        button.disabled = false;
        button.innerHTML = button.dataset.originalText || 'Submit';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme
    const savedTheme = window.localStorage.getItem('ai-equipment-theme') || 'dark';
    applyTheme(savedTheme);

    if (window.ThemeEffects && !window.themeEffects && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        window.themeEffects = new ThemeEffects();
    }

    // Theme toggle listeners
    document.querySelectorAll('[data-theme-toggle]').forEach(btn => {
        btn.addEventListener('click', toggleTheme);
    });

    // Mobile menu toggle
    const burger = document.getElementById('globalBurger');
    const menu = document.getElementById('navbarMenu');
    if (burger && menu) {
        burger.addEventListener('click', () => {
            burger.classList.toggle('active');
            menu.classList.toggle('active');
            document.body.classList.toggle('menu-open');
        });

        // Close menu when clicking links
        menu.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                burger.classList.remove('active');
                menu.classList.remove('active');
                document.body.classList.remove('menu-open');
            });
        });
    }

    // Modal global closing
    window.addEventListener('click', (event) => {
        if (event.target.classList.contains('modal')) {
            event.target.style.display = 'none';
        }
    });
});

window.API = API;
window.Modal = Modal;
window.Toast = Toast;
window.Loading = Loading;
console.log('✅ Base utilities initialized');

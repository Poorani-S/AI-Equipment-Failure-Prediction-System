/**
 * AI Equipment Failure Prediction - Theme Effects
 * Handles background animations (bubbles/snow) and theme-reactive canvas effects.
 */

class ThemeEffects {
    constructor() {
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.animationId = null;
        this.theme = document.body.getAttribute('data-theme') || 'dark';
        this.reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        this.init();
    }

    init() {
        if (this.reducedMotion) {
            return;
        }

        if (document.getElementById('theme-background-canvas')) {
            return;
        }

        this.canvas.id = 'theme-background-canvas';
        this.canvas.style.position = 'fixed';
        this.canvas.style.top = '0';
        this.canvas.style.left = '0';
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        this.canvas.style.zIndex = '0';
        this.canvas.style.pointerEvents = 'none';
        document.body.appendChild(this.canvas);

        window.addEventListener('resize', () => this.resize());
        window.addEventListener('themeChanged', (e) => {
            this.theme = e.detail.theme;
            this.createParticles();
        });

        this.resize();
        this.createParticles();
        this.animate();
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
        this.createParticles();
    }

    createParticles() {
        this.particles = [];
        const count = Math.min(220, Math.max(80, Math.floor((window.innerWidth * window.innerHeight) / 5200)));
        
        for (let i = 0; i < count; i++) {
            this.particles.push(this.resetParticle({}));
        }
    }

    resetParticle(p) {
        p.x = Math.random() * this.canvas.width;
        p.y = Math.random() * this.canvas.height;
        p.size = Math.random() * 2.8 + 0.9;
        p.speedX = (Math.random() - 0.5) * (this.theme === 'light' ? 0.18 : 0.28);
        p.speedY = Math.random() * (this.theme === 'light' ? 0.52 : 0.34) + 0.1;
        p.opacity = Math.random() * 0.28 + 0.1;
        p.drift = Math.random() * Math.PI * 2;
        
        if (this.theme === 'light') {
            p.color = `rgba(37, 99, 235, ${p.opacity})`;
        } else {
            p.color = `rgba(34, 211, 238, ${p.opacity})`;
        }
        
        return p;
    }

    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        for (let i = 0; i < this.particles.length; i++) {
            const p = this.particles[i];
            
            p.drift += 0.01;
            p.x += p.speedX + Math.sin(p.drift) * 0.15;
            p.y += p.speedY;
            
            if (p.y > this.canvas.height) {
                p.y = -10;
                p.x = Math.random() * this.canvas.width;
            }
            if (p.x > this.canvas.width || p.x < 0) {
                p.speedX *= -1;
            }
            
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            this.ctx.fillStyle = p.color;
            this.ctx.shadowColor = p.color;
            this.ctx.shadowBlur = this.theme === 'light' ? 6 : 12;
            this.ctx.fill();
        }
        
        this.animationId = requestAnimationFrame(() => this.animate());
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (!window.themeEffects && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        window.themeEffects = new ThemeEffects();
    }
});

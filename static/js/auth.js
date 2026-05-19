document.addEventListener("DOMContentLoaded", () => {
    const bubblesContainer = document.querySelector(".auth-bubbles");
    if (bubblesContainer) {
        const bubbleCount = window.innerWidth < 700 ? 10 : 18;
        for (let index = 0; index < bubbleCount; index += 1) {
            const bubble = document.createElement("span");
            bubble.className = "auth-bubble";
            const size = 12 + Math.random() * 46;
            const left = Math.random() * 100;
            const delay = Math.random() * 10;
            const duration = 10 + Math.random() * 14;
            bubble.style.width = `${size}px`;
            bubble.style.height = `${size}px`;
            bubble.style.left = `${left}%`;
            bubble.style.animationDelay = `${delay}s`;
            bubble.style.animationDuration = `${duration}s`;
            bubblesContainer.appendChild(bubble);
        }
    }

    // Auto-hide flash alerts after a few seconds to keep the form in focus.
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach((alert) => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.3s ease";
            alert.style.opacity = "0";
            setTimeout(() => alert.remove(), 300);
        }, 4000);
    });

    const form = document.querySelector(".auth-form");
    if (!form) {
        return;
    }

    const passwordInput = document.getElementById("password");
    const confirmInput = document.getElementById("confirm_password");

    if (confirmInput && passwordInput) {
        form.addEventListener("submit", (event) => {
            if (passwordInput.value !== confirmInput.value) {
                event.preventDefault();
                alert("Passwords do not match.");
                confirmInput.focus();
            }
        });
    }
});

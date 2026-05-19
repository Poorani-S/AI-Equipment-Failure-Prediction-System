const form = document.getElementById("prediction-form");
const resultCard = document.getElementById("result-card");
const resultLabel = document.getElementById("result-label");
const resultValue = document.getElementById("result-value");
const confidenceValue = document.getElementById("confidence-value");
const storageValue = document.getElementById("storage-value");
const toast = document.getElementById("toast");

function showToast(message, kind = "success") {
    if (kind === "error" || kind === "danger") Toast.error(message);
    else Toast.success(message);
}

function setResultState(type, title, confidence, stored, extra) {
    // Standardize types to match CSS classes
    const cssType = (type === "alert" || type === "danger") ? "danger" : (type === "safe" || type === "success") ? "success" : "idle";
    
    resultCard.classList.remove("idle", "success", "danger");
    resultCard.classList.add(cssType);
    
    resultLabel.textContent = cssType === "danger" ? "Failure risk detected" : cssType === "success" ? "System status stable" : "Awaiting sensor input";
    resultValue.textContent = title;
    
    if (confidenceValue) confidenceValue.textContent = confidence;
    if (storageValue) {
        storageValue.textContent = stored ? "Stored ✓" : "Offline";
        storageValue.style.color = stored ? "var(--success)" : "var(--danger)";
    }
    
    const extraEl = document.getElementById("result-extra");
    if (extraEl) extraEl.textContent = extra || "";
}

// ── Equipment Name Dropdown Management ──────────────────────────
const STORAGE_KEY = "ai-equipment-names";
const equipSelect = document.getElementById("equipment_name");
const addBtn = document.getElementById("addEquipBtn");
const delBtn = document.getElementById("delEquipBtn");

function saveEquipmentList() {
    const opts = Array.from(equipSelect.options).map(o => o.value);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(opts));
}

function loadEquipmentList() {
    try {
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
        if (saved && saved.length > 0) {
            // Clear defaults and restore saved list
            while (equipSelect.options.length > 0) equipSelect.remove(0);
            saved.forEach(name => {
                const opt = new Option(name, name);
                equipSelect.appendChild(opt);
            });
        }
    } catch (e) { /* ignore */ }
}

loadEquipmentList();

if (addBtn) {
    addBtn.addEventListener("click", () => {
        const name = prompt("Enter new equipment name:");
        if (!name || !name.trim()) return;
        const trimmed = name.trim();
        // Check for duplicate
        const existing = Array.from(equipSelect.options).find(o => o.value.toLowerCase() === trimmed.toLowerCase());
        if (existing) { showToast("Equipment already in list", "error"); return; }
        const opt = new Option(trimmed, trimmed);
        equipSelect.appendChild(opt);
        equipSelect.value = trimmed;
        saveEquipmentList();
        showToast(`Added: ${trimmed}`, "success");
    });
}

if (delBtn) {
    delBtn.addEventListener("click", () => {
        if (equipSelect.options.length <= 1) {
            showToast("Cannot delete the last equipment", "error");
            return;
        }
        const selected = equipSelect.value;
        const idx = equipSelect.selectedIndex;
        equipSelect.remove(idx);
        saveEquipmentList();
        showToast(`Deleted: ${selected}`, "success");
    });
}

// ── Prediction Form Submit ───────────────────────────────────────
form.addEventListener("submit", async (event) => {
    event.preventDefault();

    // Check if user is logged in
    const isLoggedIn = document.querySelector('.logout-btn') !== null;
    if (!isLoggedIn) {
        setResultState("idle", "Authentication Required", "--", false, "Please login to run AI predictions.");
        Toast.error("Authentication required. Redirecting to login page...");
        setTimeout(() => {
            window.location.href = "/auth/login";
        }, 1800);
        return;
    }

    const payload = {
        "equipment_type": document.getElementById("equipment_type") ? document.getElementById("equipment_type").value : "Turbine",
        "equipment_name": document.getElementById("equipment_name").value,
        "Temperature": Number(document.getElementById("temperature").value),
        "Vibration":   Number(document.getElementById("vibration").value),
        "Pressure":    Number(document.getElementById("pressure").value),
        "Humidity":    Number(document.getElementById("humidity").value),
        "Runtime Hours": Number(document.getElementById("runtime_hours").value),
    };

    try {
        const response = await fetch("/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || "Prediction request failed.");
        }

        const isFailure = data.prediction_value === 1;
        const extra = `Equipment: ${data.equipment_name || payload.equipment_name}  |  Risk: ${data.risk_level || "—"}`;
        setResultState(
            isFailure ? "alert" : "safe",
            data.prediction,
            `${data.failure_probability}%`,
            data.stored,
            extra
        );

        if (isFailure) {
            Toast.error(data.prediction);
        } else {
            Toast.success(data.prediction);
        }
    } catch (error) {
        setResultState("idle", "Prediction unavailable", "--", false);
        Toast.error(error.message);
    }
});
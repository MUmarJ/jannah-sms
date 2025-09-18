/**
 * Main JavaScript for Jannah SMS Admin
 * Elderly-friendly interface with simple interactions
 */

// Simple utility functions for elderly-friendly interface
const App = {
  // Initialize the application
  init() {
    console.log("🚀 Jannah SMS Admin initialized");
    this.setupEventListeners();
    this.setupFormValidation();
    this.setupAlerts();
    this.setupTooltips();
  },

  // Setup event listeners
  setupEventListeners() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach((alert) => {
      if (!alert.dataset.persist) {
        setTimeout(() => {
          this.dismissAlert(alert);
        }, 5000);
      }
    });

    // Handle form submissions with loading states
    const forms = document.querySelectorAll("form");
    forms.forEach((form) => {
      form.addEventListener("submit", (e) => {
        // Only set loading state if form validation passes
        if (form.hasAttribute("data-validate")) {
          if (!this.validateForm(form)) {
            return; // Don't set loading state if validation fails
          }
        }
        this.setLoadingState(form, true);

        // Auto-clear loading state after 10 seconds as failsafe
        setTimeout(() => {
          this.setLoadingState(form, false);
        }, 10000);
      });
    });

    // Auto-resize textareas
    const textareas = document.querySelectorAll(".form-textarea");
    textareas.forEach((textarea) => {
      this.autoResize(textarea);
      textarea.addEventListener("input", () => {
        this.autoResize(textarea);
      });
    });

    // Phone number formatting
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    phoneInputs.forEach((input) => {
      input.addEventListener("input", (e) => {
        this.formatPhoneNumber(e.target);
      });
    });
  },

  // Simple form validation
  setupFormValidation() {
    const forms = document.querySelectorAll("form[data-validate]");
    forms.forEach((form) => {
      form.addEventListener("submit", (e) => {
        if (!this.validateForm(form)) {
          e.preventDefault();
        }
      });

      // Real-time validation
      const inputs = form.querySelectorAll("input, textarea, select");
      inputs.forEach((input) => {
        input.addEventListener("blur", () => {
          this.validateField(input);
        });
      });
    });
  },

  // Validate individual field
  validateField(field) {
    const errorElement = field.parentElement.querySelector(".form-error");
    let isValid = true;
    let errorMessage = "";

    // Required validation
    if (field.hasAttribute("required") && !field.value.trim()) {
      isValid = false;
      errorMessage = "This field is required";
    }

    // Email validation
    if (field.type === "email" && field.value) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(field.value)) {
        isValid = false;
        errorMessage = "Please enter a valid email address";
      }
    }

    // Phone validation
    if (field.type === "tel" && field.value) {
      const phoneRegex = /^\(\d{3}\) \d{3}-\d{4}$/;
      if (!phoneRegex.test(field.value)) {
        isValid = false;
        errorMessage = "Please enter a valid phone number";
      }
    }

    // Update UI
    if (isValid) {
      field.classList.remove("error");
      if (errorElement) {
        errorElement.textContent = "";
      }
    } else {
      field.classList.add("error");
      if (errorElement) {
        errorElement.textContent = errorMessage;
      }
    }

    return isValid;
  },

  // Validate entire form
  validateForm(form) {
    const fields = form.querySelectorAll("input, textarea, select");
    let isValid = true;

    fields.forEach((field) => {
      if (!this.validateField(field)) {
        isValid = false;
      }
    });

    return isValid;
  },

  // Format phone number as user types
  formatPhoneNumber(input) {
    let value = input.value.replace(/\D/g, "");

    if (value.length >= 6) {
      value = `(${value.slice(0, 3)}) ${value.slice(3, 6)}-${value.slice(
        6,
        10
      )}`;
    } else if (value.length >= 3) {
      value = `(${value.slice(0, 3)}) ${value.slice(3)}`;
    }

    input.value = value;
  },

  // Auto-resize textarea based on content
  autoResize(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = textarea.scrollHeight + "px";
  },

  // Set loading state for forms and buttons
  setLoadingState(element, loading) {
    const buttons = element.querySelectorAll(
      'button[type="submit"], input[type="submit"]'
    );

    if (loading) {
      element.classList.add("loading");
      buttons.forEach((btn) => {
        btn.disabled = true;
        const originalText = btn.textContent;
        btn.dataset.originalText = originalText;
        btn.innerHTML = '<span class="spinner"></span> Processing...';
      });
    } else {
      element.classList.remove("loading");
      buttons.forEach((btn) => {
        btn.disabled = false;
        btn.textContent = btn.dataset.originalText || "Submit";
      });
    }
  },

  // Setup auto-dismissing alerts
  setupAlerts() {
    window.showAlert = (message, type = "info", duration = 5000) => {
      const alert = document.createElement("div");
      alert.className = `alert alert-${type}`;
      alert.textContent = message;
      alert.style.position = "fixed";
      alert.style.top = "20px";
      alert.style.right = "20px";
      alert.style.zIndex = "9999";
      alert.style.maxWidth = "400px";

      document.body.appendChild(alert);

      // Auto dismiss
      setTimeout(() => {
        this.dismissAlert(alert);
      }, duration);
    };
  },

  // Dismiss alert with animation
  dismissAlert(alert) {
    alert.style.opacity = "0";
    alert.style.transform = "translateX(100%)";
    setTimeout(() => {
      if (alert.parentElement) {
        alert.parentElement.removeChild(alert);
      }
    }, 300);
  },

  // Simple tooltips for help text
  setupTooltips() {
    const tooltipElements = document.querySelectorAll("[data-tooltip]");
    tooltipElements.forEach((element) => {
      element.addEventListener("mouseenter", (e) => {
        this.showTooltip(e.target);
      });
      element.addEventListener("mouseleave", (e) => {
        this.hideTooltip(e.target);
      });
    });
  },

  // Show tooltip
  showTooltip(element) {
    const tooltip = document.createElement("div");
    tooltip.className = "tooltip";
    tooltip.textContent = element.dataset.tooltip;
    tooltip.style.position = "absolute";
    tooltip.style.backgroundColor = "#1f2937";
    tooltip.style.color = "white";
    tooltip.style.padding = "8px 12px";
    tooltip.style.borderRadius = "6px";
    tooltip.style.fontSize = "14px";
    tooltip.style.zIndex = "10000";
    tooltip.style.maxWidth = "200px";
    tooltip.style.wordWrap = "break-word";

    document.body.appendChild(tooltip);

    const rect = element.getBoundingClientRect();
    tooltip.style.left = rect.left + "px";
    tooltip.style.top = rect.bottom + 8 + "px";

    element._tooltip = tooltip;
  },

  // Hide tooltip
  hideTooltip(element) {
    if (element._tooltip) {
      document.body.removeChild(element._tooltip);
      delete element._tooltip;
    }
  },

  // Utility function to make API calls
  async apiCall(url, options = {}) {
    const defaultOptions = {
      headers: {
        "Content-Type": "application/json",
      },
    };

    const config = { ...defaultOptions, ...options };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("API call failed:", error);
      window.showAlert(`Error: ${error.message}`, "danger");
      throw error;
    }
  },

  // Confirm dialog with better styling
  confirm(message, title = "Confirm Action") {
    return new Promise((resolve) => {
      const modal = document.createElement("div");
      modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
            `;

      const dialog = document.createElement("div");
      dialog.style.cssText = `
                background-color: white;
                padding: 32px;
                border-radius: 12px;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
                max-width: 400px;
                width: 90%;
                text-align: center;
            `;

      dialog.innerHTML = `
                <h3 style="margin: 0 0 16px 0; font-size: 24px; color: #1f2937;">${title}</h3>
                <p style="margin: 0 0 24px 0; font-size: 18px; color: #374151;">${message}</p>
                <div style="display: flex; gap: 12px; justify-content: center;">
                    <button id="cancel" class="btn btn-secondary">Cancel</button>
                    <button id="confirm" class="btn btn-primary">Confirm</button>
                </div>
            `;

      modal.appendChild(dialog);
      document.body.appendChild(modal);

      const handleChoice = (confirmed) => {
        document.body.removeChild(modal);
        resolve(confirmed);
      };

      dialog.querySelector("#confirm").onclick = () => handleChoice(true);
      dialog.querySelector("#cancel").onclick = () => handleChoice(false);
      modal.onclick = (e) => {
        if (e.target === modal) handleChoice(false);
      };
    });
  },
};

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => App.init());
} else {
  App.init();
}

// Export for use in other scripts
window.App = App;

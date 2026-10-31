/**
 * StayZen Global Form Validation and Custom Alerts System
 * 
 * Provides:
 * 1. Live, asynchronous real-time validation of all inputs (Email, Phone, Username, Passwords, Dates, Capacity).
 * 2. Overriding of native browser window.alert() with custom premium alerts.
 * 3. Dynamic error messages below form fields.
 */

(function () {
    // 1. Inject Style sheet for toast notifications, validation modal overlays, and inline error styling
    const injectStyles = () => {
        if (document.getElementById('stayzen-validation-styles')) return;

        const style = document.createElement('style');
        style.id = 'stayzen-validation-styles';
        style.textContent = `
            /* Custom Toast Notifications styling */
            .global-toast-container {
                position: fixed;
                top: 24px;
                right: 24px;
                z-index: 9999999;
                display: flex;
                flex-direction: column;
                gap: 12px;
                max-width: 380px;
                width: calc(100% - 48px);
                pointer-events: none;
            }
            .toast-item {
                background: #ffffff;
                color: #1e293b;
                border-radius: 12px;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
                padding: 16px 20px;
                display: flex;
                align-items: center;
                gap: 12px;
                border-left: 4px solid #3b82f6;
                animation: toastSlideIn 0.35s cubic-bezier(0.16, 1, 0.3, 1);
                position: relative;
                pointer-events: auto;
            }
            [data-theme="dark"] .toast-item {
                background: #1e293b;
                color: #f8fafc;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
            }
            .toast-item.success { border-left-color: #22c55e; }
            .toast-item.error, .toast-item.danger { border-left-color: #ef4444; }
            .toast-item.warning { border-left-color: #f59e0b; }
            
            .toast-icon {
                font-size: 18px;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
                width: 24px;
                height: 24px;
                border-radius: 50%;
            }
            .toast-item.success .toast-icon { color: #22c55e; }
            .toast-item.error .toast-icon, .toast-item.danger .toast-icon { color: #ef4444; }
            .toast-item.warning .toast-icon { color: #f59e0b; }
            
            .toast-content {
                font-family: 'Inter', system-ui, -apple-system, sans-serif;
                font-size: 14px;
                font-weight: 500;
                flex: 1;
                line-height: 1.4;
            }
            .toast-close {
                background: none;
                border: none;
                font-size: 20px;
                color: #94a3b8;
                cursor: pointer;
                padding: 0;
                line-height: 1;
                transition: color 0.2s, transform 0.2s;
                display: flex;
                align-items: center;
                justify-content: center;
                width: 20px;
                height: 20px;
            }
            .toast-close:hover { color: #64748b; transform: scale(1.1); }
            
            @keyframes toastSlideIn {
                from { opacity: 0; transform: translateX(60px); }
                to { opacity: 1; transform: translateX(0); }
            }
            @keyframes toastFadeOut {
                to { opacity: 0; transform: translateY(-20px); }
            }

            /* Custom Overlay Modal alert styling */
            .stayzen-alert-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(9, 10, 15, 0.65);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                z-index: 99999999;
                display: flex;
                align-items: center;
                justify-content: center;
                opacity: 0;
                transition: opacity 0.25s ease;
            }
            .stayzen-alert-overlay.show { opacity: 1; }
            
            .stayzen-alert-card {
                background: #ffffff;
                color: #1e293b;
                width: 90%;
                max-width: 460px;
                border-radius: 20px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
                padding: 30px;
                text-align: center;
                transform: scale(0.9);
                transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                box-sizing: border-box;
            }
            [data-theme="dark"] .stayzen-alert-card {
                background: #10121a;
                color: #f8fafc;
                border-color: rgba(255, 255, 255, 0.08);
            }
            .stayzen-alert-overlay.show .stayzen-alert-card { transform: scale(1); }
            
            .stayzen-alert-icon {
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: rgba(193, 155, 118, 0.15);
                color: #c19b76;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 28px;
                margin: 0 auto 20px;
            }
            [data-theme="dark"] .stayzen-alert-icon {
                background: rgba(193, 155, 118, 0.2);
                color: #d4b896;
            }
            
            .stayzen-alert-title {
                font-family: 'Gilda Display', 'Inter', serif;
                font-size: 20px;
                font-weight: 600;
                margin-bottom: 12px;
                margin-top: 0;
            }
            
            .stayzen-alert-message {
                font-family: 'Inter', sans-serif;
                font-size: 14px;
                line-height: 1.6;
                color: #64748b;
                margin-bottom: 24px;
                white-space: pre-line;
                text-align: left;
                max-height: 250px;
                overflow-y: auto;
                padding-right: 5px;
            }
            [data-theme="dark"] .stayzen-alert-message { color: #94a3b8; }
            
            .stayzen-alert-btn {
                font-family: 'Inter', sans-serif;
                background: #c19b76;
                color: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 12px 32px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.2s, transform 0.1s;
                outline: none;
                box-shadow: 0 4px 14px rgba(193, 155, 118, 0.4);
            }
            .stayzen-alert-btn:hover { background: #a57f5a; }
            .stayzen-alert-btn:active { transform: scale(0.97); }

            /* Inline Validation Error Messages */
            .validation-error-msg {
                color: #ef4444 !important;
                font-size: 11.5px;
                font-weight: 500;
                margin-top: 4px;
                display: block;
                animation: fadeInError 0.2s ease-in-out;
            }
            .form-group.invalid input,
            .form-group.invalid select,
            .form-group.invalid textarea {
                border-color: #ef4444 !important;
                box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.2) !important;
            }
            @keyframes fadeInError {
                from { opacity: 0; transform: translateY(-4px); }
                to { opacity: 1; transform: translateY(0); }
            }

            /* Password Strength Container and Requirement list styling */
            .password-strength-container {
                margin-top: 8px;
                padding: 12px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                text-align: left;
            }
            [data-theme="light"] .password-strength-container {
                background: #f8fafc;
                border-color: #e2e8f0;
            }
            .strength-bar-wrapper {
                height: 6px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 3px;
                margin-bottom: 8px;
                overflow: hidden;
            }
            [data-theme="light"] .strength-bar-wrapper {
                background: #e2e8f0;
            }
            .strength-bar {
                height: 100%;
                width: 0%;
                transition: width 0.3s, background-color 0.3s;
                border-radius: 3px;
            }
            .strength-text {
                font-size: 12px;
                font-weight: 600;
                margin-bottom: 6px;
                color: #f8fafc;
            }
            [data-theme="light"] .strength-text {
                color: #1e293b;
            }
            .password-reqs {
                list-style: none;
                padding: 0;
                margin: 0;
                font-size: 11.5px;
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            .req-item {
                display: flex;
                align-items: center;
                gap: 6px;
                transition: color 0.2s;
            }
            .req-item.met {
                color: #22c55e !important;
            }
            .req-item.unmet {
                color: #ef4444 !important;
            }
        `;
        document.head.appendChild(style);
    };

    // 2. Custom premium Alert Modal builder
    const showCustomModal = (message, callback) => {
        const existing = document.querySelector('.stayzen-alert-overlay');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.className = 'stayzen-alert-overlay';

        let iconHTML = '⚠️';
        let titleHTML = 'Validation Failed';
        const msgLower = message.toLowerCase();

        if (msgLower.includes('pay') || msgLower.includes('confirm') || msgLower.includes('success') || msgLower.includes('amount')) {
            iconHTML = 'ℹ️';
            titleHTML = 'Information';
        }

        overlay.innerHTML = `
            <div class="stayzen-alert-card">
                <div class="stayzen-alert-icon">${iconHTML}</div>
                <h3 class="stayzen-alert-title">${titleHTML}</h3>
                <div class="stayzen-alert-message">${message}</div>
                <button class="stayzen-alert-btn">OK</button>
            </div>
        `;

        document.body.appendChild(overlay);

        setTimeout(() => {
            overlay.classList.add('show');
        }, 10);

        const closeBtn = overlay.querySelector('.stayzen-alert-btn');
        closeBtn.focus();

        closeBtn.addEventListener('click', function () {
            overlay.classList.remove('show');
            setTimeout(() => {
                overlay.remove();
                if (callback) callback();
            }, 250);
        });
    };

    // Helper to get friendly names for inputs
    const getFieldName = (field) => {
        if (field.id) {
            const label = document.querySelector(`label[for="${field.id}"]`);
            if (label) return label.textContent.replace(/[*:]/g, '').trim();
        }
        const parentLabel = field.closest('label');
        if (parentLabel) return parentLabel.textContent.replace(/[*:]/g, '').trim();
        
        // Lookup from label tag that is a sibling or parent sibling
        const group = field.closest('.form-group');
        if (group) {
            const label = group.querySelector('label');
            if (label) return label.textContent.replace(/[*:]/g, '').trim();
        }

        if (field.placeholder) return field.placeholder.trim();
        if (field.name) {
            return field.name
                .replace(/[-_]/g, ' ')
                .replace(/\b\w/g, c => c.toUpperCase());
        }
        return 'Field';
    };

    // Helper to parse date inputs safely
    const parseDateInput = (value) => {
        const parts = value.split('-');
        if (parts.length === 3) {
            const year = parseInt(parts[0], 10);
            const month = parseInt(parts[1], 10) - 1;
            const day = parseInt(parts[2], 10);
            return new Date(year, month, day);
        }
        return new Date(value);
    };

    // Inline Error Display utilities
    const showError = (input, message) => {
        const formGroup = input.closest('.form-group') || input.parentElement;
        formGroup.classList.add('invalid');
        
        let errorMsg = formGroup.querySelector('.validation-error-msg');
        if (!errorMsg) {
            errorMsg = document.createElement('span');
            errorMsg.className = 'validation-error-msg';
            formGroup.appendChild(errorMsg);
        }
        errorMsg.textContent = message;
    };

    const clearError = (input) => {
        const formGroup = input.closest('.form-group') || input.parentElement;
        formGroup.classList.remove('invalid');
        
        const errorMsg = formGroup.querySelector('.validation-error-msg');
        if (errorMsg) {
            errorMsg.remove();
        }
    };

    // Password strength meters UI
    const updatePasswordStrength = (input) => {
        const value = input.value;
        const formGroup = input.closest('.form-group') || input.parentElement;
        
        let container = formGroup.querySelector('.password-strength-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'password-strength-container';
            container.innerHTML = `
                <div class="strength-bar-wrapper">
                    <div class="strength-bar"></div>
                </div>
                <div class="strength-text">Strength: <span class="strength-label">Weak</span></div>
            `;
            formGroup.appendChild(container);
        }

        const bar = container.querySelector('.strength-bar');
        const label = container.querySelector('.strength-label');

        const len = value.length;
        let strength = 'Weak';
        let color = '#ef4444';
        let percent = '25%';
        let isValid = false;

        if (len >= 10) {
            strength = 'Strong';
            color = '#22c55e';
            percent = '100%';
            isValid = true;
        } else if (len >= 6) {
            strength = 'Medium';
            color = '#f59e0b';
            percent = '60%';
            isValid = true;
        }

        bar.style.width = percent;
        bar.style.backgroundColor = color;
        label.textContent = strength;
        label.style.color = color;

        if (!isValid) {
            showError(input, 'Password must be at least 6 characters.');
        } else {
            clearError(input);
        }

        return { isValid };
    };

    const removePasswordRequirements = (input) => {
        const formGroup = input.closest('.form-group') || input.parentElement;
        const container = formGroup.querySelector('.password-strength-container');
        if (container) {
            container.remove();
        }
    };

    // Live Field Validator Engine
    const validateField = async (input) => {
        if (input.type === 'hidden' || input.disabled || input.offsetParent === null) return true;

        const value = input.value.trim();
        const friendlyName = getFieldName(input);
        const nameLower = (input.name || '').toLowerCase();

        // 1. Required field checking
        if (input.hasAttribute('required')) {
            if (input.type === 'checkbox') {
                if (!input.checked) {
                    showError(input, `${friendlyName} is required.`);
                    return false;
                }
            } else if (input.type === 'radio') {
                const name = input.name;
                const form = input.closest('form');
                const checked = form ? form.querySelector(`input[name="${name}"]:checked`) : null;
                if (!checked) {
                    showError(input, `${friendlyName} is required.`);
                    return false;
                }
            } else if (!value) {
                showError(input, `${friendlyName} is required.`);
                return false;
            }
        }

        if (!value) {
            clearError(input);
            if (input.type === 'password') {
                removePasswordRequirements(input);
            }
            return true;
        }

        // 2. Name validation (Prevent special characters & numbers)
        if (nameLower.includes('name') || nameLower === 'sname') {
            const nameRegex = /^[a-zA-Z\s]+$/;
            if (!nameRegex.test(value)) {
                // Instantly remove non-matching chars during input
                const cleanVal = value.replace(/[^a-zA-Z\s]/g, '');
                if (cleanVal !== value) {
                    input.value = cleanVal;
                }
                showError(input, 'Special characters and numbers are not allowed.');
                return false;
            }
        }

        // 3. Email validation (check format always; check DB only on non-login forms)
        if (input.type === 'email' || nameLower.includes('email') || nameLower === 'signemail') {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                showError(input, 'Please enter a valid email address.');
                return false;
            }

            // Skip DB duplicate check on login forms — email must already exist there
            const form = input.closest('form');
            const isLoginForm = form && form.dataset.formType === 'login';

            if (!isLoginForm) {
                try {
                    const response = await fetch(`/accounts/validate/?field=email&value=${encodeURIComponent(value)}`);
                    const data = await response.json();
                    if (data.exists) {
                        showError(input, 'Email already exists.');
                        return false;
                    }
                } catch (err) {
                    console.error('Email check failed:', err);
                }
            }
        }

        // 4. Username database check — skip on login forms
        if (nameLower === 'username') {
            const form = input.closest('form');
            const isLoginForm = form && form.dataset.formType === 'login';
            if (!isLoginForm) {
                try {
                    const response = await fetch(`/accounts/validate/?field=username&value=${encodeURIComponent(value)}`);
                    const data = await response.json();
                    if (data.exists) {
                        showError(input, 'Username already taken.');
                        return false;
                    }
                } catch (err) {
                    console.error('Username check failed:', err);
                }
            }
        }

        // 5. Phone Validation (Allow numbers only, validate length)
        if (input.type === 'tel' || nameLower.includes('phone') || nameLower.includes('contact')) {
            const cleanVal = value.replace(/[^0-9]/g, '');
            if (cleanVal !== value) {
                input.value = cleanVal;
            }
            
            if (cleanVal.length !== 10) {
                showError(input, 'Invalid phone number.');
                return false;
            }
        }

        // 6. Password strength — only on non-login forms (register / change password)
        const isPasswordToCheck = input.type === 'password' &&
                                   nameLower.includes('password') &&
                                   !nameLower.includes('confirm') &&
                                   !nameLower.includes('old') &&
                                   nameLower !== 'cpassword';
        if (isPasswordToCheck) {
            const form = input.closest('form');
            const isLoginForm = form && form.dataset.formType === 'login';
            if (!isLoginForm) {
                const result = updatePasswordStrength(input);
                if (!result.isValid) return false;
            }
        }

        // 7. Confirm Password matching checking
        if (input.type === 'password' && (nameLower.includes('confirm') || nameLower === 'cpassword')) {
            const form = input.closest('form');
            if (form) {
                const mainPass = form.querySelector('input[type="password"]:not([name*="confirm"]):not([name*="old"]):not([name="cpassword"])');
                if (mainPass && mainPass.value !== value) {
                    showError(input, 'Passwords do not match.');
                    return false;
                }
            }
        }

        // 8. Dates validation (No past dates, end date after start date)
        if (input.type === 'date') {
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const inputDate = parseDateInput(value);

            const isBookingDate = nameLower.includes('in') || nameLower.includes('out') || nameLower.includes('start') || nameLower.includes('end') || nameLower.includes('date');
            
            if (isBookingDate && inputDate < today) {
                showError(input, 'Date cannot be in the past.');
                return false;
            }

            const form = input.closest('form');
            if (form) {
                let startField = null;
                let endField = null;

                if (nameLower.includes('out') || nameLower.includes('end') || nameLower.includes('to')) {
                    endField = input;
                    startField = form.querySelector('input[type="date"][name*="in"], input[type="date"][name*="start"], input[type="date"][name*="from"]');
                } else if (nameLower.includes('in') || nameLower.includes('start') || nameLower.includes('from')) {
                    startField = input;
                    endField = form.querySelector('input[type="date"][name*="out"], input[type="date"][name*="end"], input[type="date"][name*="to"]');
                }

                if (startField && endField && startField.value && endField.value) {
                    const startVal = parseDateInput(startField.value);
                    const endVal = parseDateInput(endField.value);
                    if (endVal < startVal) {
                        showError(endField, 'Check-out / end date must be on or after the check-in / start date.');
                        return false;
                    } else {
                        // Clear sequence errors
                        const endErr = endField.closest('.form-group')?.querySelector('.validation-error-msg');
                        if (endErr && endErr.textContent.includes('after')) {
                            clearError(endField);
                        }
                    }
                }
            }
        }

        // 9. Capacity and guest counts validation
        if ((input.type === 'number' || nameLower.includes('count') || nameLower.includes('guests') || nameLower === 'adults' || nameLower === 'children') && input.type !== 'checkbox' && input.type !== 'radio' && !nameLower.includes('discount')) {
            const numValue = parseInt(value, 10);
            if (isNaN(numValue)) {
                showError(input, `${friendlyName} must be a number.`);
                return false;
            }

            // Room Adults / Children bounds check
            if (nameLower === 'adults' || nameLower === 'children') {
                const roomIdEl = document.getElementById('room_id');
                if (roomIdEl) {
                    let maxVal = 999;
                    if (roomIdEl.tagName === 'SELECT') {
                        const selectedOption = roomIdEl.options[roomIdEl.selectedIndex];
                        if (selectedOption) {
                            maxVal = parseInt(selectedOption.getAttribute(nameLower === 'adults' ? 'data-max-adults' : 'data-max-children')) || 999;
                        }
                    } else {
                        maxVal = parseInt(roomIdEl.getAttribute(nameLower === 'adults' ? 'data-max-adults' : 'data-max-children')) || 999;
                    }
                    if (numValue > maxVal) {
                        showError(input, `Exceeds room capacity (Max: ${maxVal} ${nameLower}).`);
                        return false;
                    }
                }
            }

            // Hall Capacity check
            if (nameLower === 'guest_count') {
                const hallIdEl = document.getElementById('hall_id');
                if (hallIdEl) {
                    let maxVal = 999999;
                    if (hallIdEl.tagName === 'SELECT') {
                        const selectedOption = hallIdEl.options[hallIdEl.selectedIndex];
                        if (selectedOption) {
                            maxVal = parseInt(selectedOption.getAttribute('data-capacity')) || 999999;
                        }
                    } else {
                        maxVal = parseInt(hallIdEl.getAttribute('data-capacity')) || 999999;
                    }
                    if (numValue > maxVal) {
                        showError(input, `Exceeds hall capacity (Max: ${maxVal} guests).`);
                        return false;
                    }
                }
            }

            // Table capacity check
            if (nameLower === 'guests') {
                const maxVal = parseInt(input.getAttribute('data-max-capacity')) || 999;
                if (numValue > maxVal) {
                    showError(input, `Exceeds table capacity (Max: ${maxVal} guests).`);
                    return false;
                }
            }
        }

        clearError(input);
        return true;
    };

    // Bind real-time event listeners on typing or updating field values
    const bindRealTimeValidation = (form) => {
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            if (input.__validationBound) return;
            input.__validationBound = true;

            const handler = () => {
                validateField(input);
            };

            input.addEventListener('input', handler);
            input.addEventListener('change', handler);
            input.addEventListener('blur', handler);
        });
    };

    // Submit handler - run all async checks and block submit if validation fails
    let currentSubmitEvent = null;

    const setupEventListeners = () => {
        document.addEventListener('submit', async function (e) {
            const form = e.target;

            if (form.__validated) {
                return;
            }

            e.preventDefault();
            e.stopImmediatePropagation();
            currentSubmitEvent = e;

            const fields = Array.from(form.querySelectorAll('input:not([type="hidden"]), select, textarea'))
                .filter(field => !field.disabled && field.offsetParent !== null);

            let isValid = true;
            for (const field of fields) {
                const isFieldValid = await validateField(field);
                if (!isFieldValid) {
                    isValid = false;
                }
            }

            if (!isValid) {
                currentSubmitEvent = null;
                showCustomModal("Please correct the errors in the form before submitting.");
                return;
            }

            // Submit form
            form.__validated = true;
            form.submit();

            setTimeout(() => {
                currentSubmitEvent = null;
            }, 50);
        }, true);

        // Hijack window.alert to convert localhost native alerts into beautiful modals
        const originalAlert = window.alert;
        window.alert = function (message) {
            if (currentSubmitEvent) {
                currentSubmitEvent.preventDefault();
                const form = currentSubmitEvent.target;

                showCustomModal(message, function () {
                    form.__validated = true;
                    form.submit();
                });
                return;
            }

            showCustomModal(message);
        };
    };

    const init = () => {
        injectStyles();
        setupEventListeners();

        const applyNoValidateAndBind = () => {
            document.querySelectorAll('form').forEach(form => {
                if (!form.hasAttribute('novalidate')) {
                    form.setAttribute('novalidate', 'true');
                }
                bindRealTimeValidation(form);
            });
        };
        
        applyNoValidateAndBind();

        const observer = new MutationObserver(applyNoValidateAndBind);
        observer.observe(document.body, { childList: true, subtree: true });
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
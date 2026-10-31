(function () {
    'use strict';

    const CONFIG = {
        storagePrefix: 'stayzen_form_state_v3:',
        submitPrefix: 'stayzen_form_submit_v3:',
        excludedTypes: ['password', 'file', 'submit', 'button', 'reset', 'image'],
        excludedNames: [
            'csrfmiddlewaretoken',
            'csrf_token',
            '_token',
            'otp',
            'one_time_password',
            'verification_code',
            'security_code',
            'cvv',
            'cvc',
            'card_number',
            'credit_card',
            'debit_card',
            'card_cvc',
            'card_cvv',
            'expiry_date',
            'card_expiry',
            'pin',
            'secret',
            'auth_code',
        ],
        excludedPatterns: [
            /password/i,
            /passwd/i,
            /csrf/i,
            /token/i,
            /otp/i,
            /cvv/i,
            /cvc/i,
            /card.*number/i,
            /credit.*card/i,
            /debit.*card/i,
            /security.*code/i,
            /verification.*code/i,
            /secret/i,
            /pin/i,
        ],
    };

    const initializedForms = new WeakSet();
    const pendingSaveTimers = new WeakMap();
    let pendingSubmission = null;
    const pagePath = window.location.pathname;

    function getNavigationType() {
        try {
            const entries = performance.getEntriesByType('navigation');
            if (entries && entries.length) {
                return entries[0].type;
            }
        } catch (e) {
            // Older browsers may not support the modern API.
        }

        if (performance && performance.navigation) {
            if (performance.navigation.type === 1) {
                return 'reload';
            }
            if (performance.navigation.type === 2) {
                return 'back_forward';
            }
        }

        return 'navigate';
    }

    function isReloadNavigation() {
        return getNavigationType() === 'reload';
    }

    function getFormIndex(form) {
        return Array.prototype.indexOf.call(document.querySelectorAll('form'), form);
    }

    function getFormKey(form) {
        const index = getFormIndex(form);
        const formId = (form.id || '').trim();
        const formAction = (form.getAttribute('action') || '').trim();

        if (formId) {
            return `${CONFIG.storagePrefix}${pagePath}::id::${formId}`;
        }

        if (formAction) {
            return `${CONFIG.storagePrefix}${pagePath}::action::${formAction}`;
        }

        return `${CONFIG.storagePrefix}${pagePath}::form_${index}`;
    }

    function shouldSkipForm(form) {
        return form.getAttribute('data-no-preserve') === 'true';
    }

    function shouldSkipField(field) {
        if (!field || !field.name || field.disabled) {
            return true;
        }

        const tagName = (field.tagName || '').toLowerCase();
        const fieldType = (field.type || '').toLowerCase();
        const fieldName = (field.name || '').toLowerCase();
        const fieldId = (field.id || '').toLowerCase();
        const lookup = `${fieldName} ${fieldId}`;

        if (CONFIG.excludedTypes.includes(fieldType)) {
            return true;
        }

        for (const excluded of CONFIG.excludedNames) {
            if (fieldName === excluded || fieldId === excluded) {
                return true;
            }
        }

        for (const pattern of CONFIG.excludedPatterns) {
            if (pattern.test(lookup)) {
                return true;
            }
        }

        const autocomplete = (field.getAttribute('autocomplete') || '').toLowerCase();
        if ([
            'cc-number',
            'cc-exp',
            'cc-csc',
            'cc-name',
            'cc-type',
            'current-password',
            'new-password',
            'one-time-code',
        ].includes(autocomplete)) {
            return true;
        }

        if (field.hasAttribute('data-no-preserve') || field.hasAttribute('data-sensitive')) {
            return true;
        }

        return tagName === 'button';
    }

    function readFormState(form) {
        const state = {};
        const elements = Array.from(form.elements || []);

        elements.forEach((field) => {
            if (shouldSkipField(field)) {
                return;
            }

            const tagName = (field.tagName || '').toLowerCase();
            const fieldType = (field.type || '').toLowerCase();
            const name = field.name;

            if (fieldType === 'checkbox') {
                if (!Array.isArray(state[name])) {
                    state[name] = [];
                }

                if (field.checked) {
                    state[name].push(field.value);
                }
                return;
            }

            if (fieldType === 'radio') {
                if (field.checked) {
                    state[name] = field.value;
                }
                return;
            }

            if (tagName === 'select' && field.multiple) {
                state[name] = Array.from(field.selectedOptions).map((option) => option.value);
                return;
            }

            state[name] = field.value;
        });

        return state;
    }

    function saveFormState(form) {
        if (!form || shouldSkipForm(form)) {
            return;
        }

        const key = getFormKey(form);
        const state = readFormState(form);

        try {
            if (Object.keys(state).length) {
                sessionStorage.setItem(key, JSON.stringify(state));
            } else {
                sessionStorage.removeItem(key);
            }
        } catch (e) {
            // Ignore storage quota/security failures.
        }
    }

    function restoreFormState(form) {
        if (!form || shouldSkipForm(form)) {
            return;
        }

        const key = getFormKey(form);
        let state = null;

        try {
            const stored = sessionStorage.getItem(key);
            if (!stored) {
                return;
            }
            state = JSON.parse(stored);
        } catch (e) {
            return;
        }

        const elements = Array.from(form.elements || []);
        elements.forEach((field) => {
            if (shouldSkipField(field)) {
                return;
            }

            const tagName = (field.tagName || '').toLowerCase();
            const fieldType = (field.type || '').toLowerCase();
            const name = field.name;

            if (!(name in state)) {
                return;
            }

            const value = state[name];

            if (fieldType === 'checkbox') {
                const values = Array.isArray(value) ? value : [value];
                field.checked = values.map(String).includes(String(field.value));
                return;
            }

            if (fieldType === 'radio') {
                field.checked = String(field.value) === String(value);
                return;
            }

            if (tagName === 'select' && field.multiple && Array.isArray(value)) {
                const selectedValues = value.map(String);
                Array.from(field.options).forEach((option) => {
                    option.selected = selectedValues.includes(String(option.value));
                });
                return;
            }

            field.value = value;
        });
    }

    function clearStoredFormStateForPath(pathname) {
        const prefix = `${CONFIG.storagePrefix}${pathname}::`;
        const submitPrefix = `${CONFIG.submitPrefix}`;
        const keysToRemove = [];

        try {
            for (let i = 0; i < sessionStorage.length; i += 1) {
                const key = sessionStorage.key(i);
                if (!key) {
                    continue;
                }

                if (key.startsWith(prefix)) {
                    keysToRemove.push(key);
                    continue;
                }

                if (key.startsWith(submitPrefix)) {
                    const raw = sessionStorage.getItem(key);
                    if (!raw) {
                        continue;
                    }

                    try {
                        const parsed = JSON.parse(raw);
                        if (parsed && parsed.path === pathname) {
                            keysToRemove.push(key);
                        }
                    } catch (e) {
                        keysToRemove.push(key);
                    }
                }
            }

            keysToRemove.forEach((key) => sessionStorage.removeItem(key));
        } catch (e) {
            // Ignore storage errors.
        }
    }

    function formHasValidationErrors() {
        return Boolean(document.querySelector([
            '.errorlist',
            '.invalid-feedback',
            '.field-error',
            '.is-invalid',
            '[aria-invalid="true"]',
            '.alert-danger',
            '.alert-error',
            '.toast-item.error',
            '.toast-item.danger',
        ].join(',')));
    }

    function clearSubmissionMarkersIfAppropriate() {
        const markers = [];

        try {
            for (let i = 0; i < sessionStorage.length; i += 1) {
                const key = sessionStorage.key(i);
                if (key && key.startsWith(CONFIG.submitPrefix)) {
                    markers.push(key);
                }
            }
        } catch (e) {
            return;
        }

        markers.forEach((markerKey) => {
            let marker = null;
            try {
                marker = JSON.parse(sessionStorage.getItem(markerKey));
            } catch (e) {
                marker = null;
            }

            if (!marker || !marker.path) {
                sessionStorage.removeItem(markerKey);
                return;
            }

            if (marker.path !== pagePath) {
                clearStoredFormStateForPath(marker.path);
                sessionStorage.removeItem(markerKey);
                return;
            }

            if (!formHasValidationErrors()) {
                clearStoredFormStateForPath(marker.path);
                sessionStorage.removeItem(markerKey);
            }
        });
    }

    function registerForm(form) {
        if (!form || initializedForms.has(form) || shouldSkipForm(form)) {
            return;
        }

        initializedForms.add(form);
        restoreFormState(form);
    }

    function registerAllForms() {
        document.querySelectorAll('form').forEach((form) => registerForm(form));
    }

    function queueSave(form) {
        if (!form || shouldSkipForm(form)) {
            return;
        }

        const existingTimer = pendingSaveTimers.get(form);
        if (existingTimer) {
            clearTimeout(existingTimer);
        }

        const timer = window.setTimeout(() => {
            saveFormState(form);
            pendingSaveTimers.delete(form);
        }, 75);

        pendingSaveTimers.set(form, timer);
    }

    function handleFormEvent(event) {
        const target = event.target;
        const form = target && target.closest ? target.closest('form') : null;
        if (!form || shouldSkipForm(form)) {
            return;
        }

        if (event.type === 'input' || event.type === 'change') {
            queueSave(form);
        }

        if (event.type === 'submit') {
            // Keep the latest values before navigation starts.
            saveFormState(form);
            const submissionCandidate = {
                key: getFormKey(form),
                path: pagePath,
                time: Date.now(),
            };

            Promise.resolve().then(() => {
                if (!event.defaultPrevented) {
                    pendingSubmission = submissionCandidate;
                }
            });
        }
    }

    function commitPendingSubmission() {
        if (!pendingSubmission) {
            return;
        }

        try {
            sessionStorage.setItem(
                `${CONFIG.submitPrefix}${pendingSubmission.key}`,
                JSON.stringify({
                    path: pendingSubmission.path,
                    time: pendingSubmission.time,
                })
            );
        } catch (e) {
            // Ignore storage errors.
        } finally {
            pendingSubmission = null;
        }
    }

    function installGlobalListeners() {
        document.addEventListener('input', handleFormEvent, true);
        document.addEventListener('change', handleFormEvent, true);
        document.addEventListener('submit', handleFormEvent, true);

        window.addEventListener('pagehide', (event) => {
            if (!event.persisted) {
                commitPendingSubmission();
            }
        });

        window.addEventListener('beforeunload', () => {
            commitPendingSubmission();
            document.querySelectorAll('form').forEach((form) => {
                if (!shouldSkipForm(form)) {
                    saveFormState(form);
                }
            });
        });

        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (!node || node.nodeType !== 1) {
                        return;
                    }

                    if (node.tagName && node.tagName.toLowerCase() === 'form') {
                        registerForm(node);
                    }

                    if (node.querySelectorAll) {
                        node.querySelectorAll('form').forEach((form) => registerForm(form));
                    }
                });
            });
        });

        observer.observe(document.documentElement, {
            childList: true,
            subtree: true,
        });
    }

    function init() {
        if (isReloadNavigation()) {
            clearStoredFormStateForPath(pagePath);
        }

        clearSubmissionMarkersIfAppropriate();
        registerAllForms();
        installGlobalListeners();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
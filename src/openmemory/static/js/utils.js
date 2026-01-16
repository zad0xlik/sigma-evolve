// UI Utilities and Helper Functions

export const utils = {
    // Format date to locale string
    formatDate(date) {
        return new Date(date).toLocaleString();
    },

    // Format confidence as percentage
    formatConfidence(value) {
        return Math.round(value * 100) + '%';
    },

    // Format time in seconds
    formatTime(seconds) {
        if (seconds < 60) return `${Math.round(seconds)}s`;
        if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
        return `${Math.round(seconds / 3600)}h`;
    },

    // Show toast notification
    showToast(message, type = 'info') {
        // Dispatch custom event that Alpine component will listen to
        window.dispatchEvent(new CustomEvent('show-toast', {
            detail: { message, type }
        }));
    },

    // Show success toast
    success(message) {
        this.showToast(message, 'success');
    },

    // Show error toast
    error(message) {
        this.showToast(message, 'error');
    },

    // Show info toast
    info(message) {
        this.showToast(message, 'info');
    },

    // Validate URL format
    isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    },

    // Validate GitHub URL
    isValidGitHubUrl(string) {
        return this.isValidUrl(string) && string.includes('github.com');
    },

    // Copy text to clipboard
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.success('Copied to clipboard');
        } catch (err) {
            this.error('Failed to copy to clipboard');
        }
    },

    // Debounce function
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Store value in localStorage
    store(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.error('Failed to store value', e);
        }
    },

    // Retrieve value from localStorage
    retrieve(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.error('Failed to retrieve value', e);
            return defaultValue;
        }
    },

    // Remove value from localStorage
    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (e) {
            console.error('Failed to remove value', e);
        }
    }
};

// Make utils available globally for Alpine
window.utils = utils;

/**
 * Shared utilities for the Veckans Recept app
 */

const Utils = {
    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    },

    /**
     * Get CSS class for store styling
     */
    getStoreClass(store) {
        if (store.startsWith('ICA')) return 'ica';
        if (store.includes('Coop')) return 'coop';
        if (store === 'Willys') return 'willys';
        return '';
    },

    /**
     * Get short display name for store
     */
    getShortStoreName(store) {
        if (store === 'ICA Supermarket') return 'ICA';
        if (store === 'ICA Nära') return 'ICA Nära';
        if (store === 'ICA Maxi') return 'ICA Maxi';
        if (store === 'ICA Kvantum') return 'ICA Kvantum';
        if (store === 'Stora Coop') return 'Stora Coop';
        if (store === 'Coop') return 'Coop';
        if (store === 'Willys') return 'Willys';
        return store;
    },
};

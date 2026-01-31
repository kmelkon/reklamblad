/**
 * Deals Page - Browse and select deals for shopping lists
 */

class DealsApp {
    constructor() {
        this.deals = [];
        this.filteredDeals = [];
        this.selectedIds = new Set();
        this.currentStore = 'all';
        this.searchQuery = '';
        this.sortBy = 'name';
        this.sortAsc = true;
        this.initialized = false;

        // Virtual scroll state
        this.ROW_HEIGHT = 64;
        this.CARD_HEIGHT = 180;
        this.BUFFER_SIZE = 15;
        this.visibleStart = 0;
        this.visibleEnd = 0;
        this.isMobile = false;
        this.scrollRAF = null;

        // Bound handlers for cleanup
        this.boundHandlers = {
            resize: null,
            scroll: null,
        };

        // Debounce timer
        this.searchDebounceTimer = null;

        this.elements = {};
    }

    /**
     * Initialize the deals page (lazy - called on first route visit)
     */
    async init() {
        if (this.initialized) {
            this.onEnter();
            return;
        }

        this.cacheElements();
        this.checkMobile();
        await this.loadData();
        this.bindEvents();
        this.setupVirtualScroll();
        this.render();
        this.initialized = true;
    }

    /**
     * Check if we're on mobile
     */
    checkMobile() {
        this.isMobile = window.innerWidth <= 768;
    }

    /**
     * Get item height based on viewport
     */
    getItemHeight() {
        return this.isMobile ? this.CARD_HEIGHT : this.ROW_HEIGHT;
    }

    /**
     * Cache DOM element references
     */
    cacheElements() {
        this.elements = {
            page: document.getElementById('pageDeals'),
            container: document.getElementById('dealsContainer'),
            searchInput: document.getElementById('dealsSearchInput'),
            filterGroup: document.getElementById('dealsFilterGroup'),
            countDisplay: document.getElementById('dealsCount'),
            selectionBar: document.getElementById('selectionBar'),
            selectionCount: document.getElementById('selectionCount'),
        };
    }

    /**
     * Load deals data
     */
    async loadData() {
        try {
            const res = await fetch('deals.json');
            if (!res.ok) throw new Error('Failed to fetch deals');
            this.deals = await res.json();
            this.filteredDeals = [...this.deals];
            this.renderFilterChips();
            this.updateCount();
        } catch (error) {
            console.error('Failed to load deals:', error);
            this.showError();
        }
    }

    /**
     * Render store filter chips
     */
    renderFilterChips() {
        if (!this.elements.filterGroup) return;

        const stores = this.getStores();
        let html = `<button class="filter-chip active" data-store="all">Alla</button>`;

        stores.forEach(store => {
            const storeClass = Utils.getStoreClass(store);
            const shortName = Utils.getShortStoreName(store);
            html += `
                <button class="filter-chip" data-store="${Utils.escapeHtml(store)}">
                    <span class="chip-dot ${storeClass}"></span>
                    ${Utils.escapeHtml(shortName)}
                </button>
            `;
        });

        this.elements.filterGroup.innerHTML = html;
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Search input (debounced)
        if (this.elements.searchInput) {
            this.elements.searchInput.addEventListener('input', (e) => {
                const value = e.target.value.toLowerCase().trim();
                clearTimeout(this.searchDebounceTimer);
                this.searchDebounceTimer = setTimeout(() => {
                    this.searchQuery = value;
                    this.filterDeals();
                }, 150);
            });
        }

        // Filter chips (event delegation)
        if (this.elements.filterGroup) {
            this.elements.filterGroup.addEventListener('click', (e) => {
                const chip = e.target.closest('.filter-chip');
                if (!chip) return;

                this.elements.filterGroup.querySelectorAll('.filter-chip').forEach(c =>
                    c.classList.remove('active')
                );
                chip.classList.add('active');
                this.currentStore = chip.dataset.store;
                this.filterDeals();
            });
        }

        // Clear selection button
        const clearBtn = document.getElementById('clearSelectionBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearSelection());
        }

        // Add to list button
        const addToListBtn = document.getElementById('addToListBtn');
        if (addToListBtn) {
            addToListBtn.addEventListener('click', () => {
                const deals = this.getSelectedDeals();
                if (deals.length > 0) {
                    listsApp.showAddToListSheet(deals);
                }
            });
        }

        // Resize handler (bound for cleanup)
        this.boundHandlers.resize = () => {
            const wasMobile = this.isMobile;
            this.checkMobile();
            if (wasMobile !== this.isMobile) {
                this.render();
            }
        };
        window.addEventListener('resize', this.boundHandlers.resize);

        // Deal selection via event delegation
        if (this.elements.container) {
            // Select-all checkbox (use change event for checkbox)
            this.elements.container.addEventListener('change', (e) => {
                if (e.target.classList.contains('deal-select-all')) {
                    if (e.target.checked) {
                        this.selectAll();
                    } else {
                        this.clearSelection();
                    }
                }
            });

            this.elements.container.addEventListener('click', (e) => {
                const checkbox = e.target.closest('.deal-checkbox');
                if (checkbox) {
                    const idx = parseInt(checkbox.dataset.idx, 10);
                    this.toggleSelection(idx);
                    this.renderVisibleItems();
                    return;
                }

                const addBtn = e.target.closest('.deal-add-btn, .deal-card-cta');
                if (addBtn) {
                    const idx = parseInt(addBtn.dataset.idx, 10);
                    this.toggleSelection(idx);
                    this.renderVisibleItems();
                    return;
                }
            });

            // Sort header clicks (desktop)
            this.elements.container.addEventListener('click', (e) => {
                const header = e.target.closest('.deals-th[data-sort]');
                if (header) {
                    this.handleSort(header);
                }
            });

            // Sort header keyboard support (Enter/Space)
            this.elements.container.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    const header = e.target.closest('.deals-th[data-sort]');
                    if (header) {
                        e.preventDefault();
                        this.handleSort(header);
                    }
                }
            });
        }
    }

    /**
     * Handle sort header activation
     */
    handleSort(header) {
        const sortKey = header.dataset.sort;
        if (this.sortBy === sortKey) {
            this.sortAsc = !this.sortAsc;
        } else {
            this.sortBy = sortKey;
            this.sortAsc = true;
        }
        this.sortDeals();
        this.render();
    }

    /**
     * Setup virtual scroll
     */
    setupVirtualScroll() {
        this.boundHandlers.scroll = () => {
            if (this.scrollRAF) return;
            this.scrollRAF = requestAnimationFrame(() => {
                this.scrollRAF = null;
                if (router.currentRoute === '/deals') {
                    this.updateVisibleRange();
                }
            });
        };
        window.addEventListener('scroll', this.boundHandlers.scroll, { passive: true });
    }

    /**
     * Calculate visible range based on scroll position
     */
    updateVisibleRange() {
        const scrollTop = window.scrollY;
        const viewportHeight = window.innerHeight;
        const itemHeight = this.getItemHeight();
        const headerOffset = this.elements.container?.offsetTop || 0;

        const relativeScroll = Math.max(0, scrollTop - headerOffset);
        const startIdx = Math.floor(relativeScroll / itemHeight);
        const visibleCount = Math.ceil(viewportHeight / itemHeight);

        const newStart = Math.max(0, startIdx - this.BUFFER_SIZE);
        const newEnd = Math.min(this.filteredDeals.length, startIdx + visibleCount + this.BUFFER_SIZE);

        if (newStart !== this.visibleStart || newEnd !== this.visibleEnd) {
            this.visibleStart = newStart;
            this.visibleEnd = newEnd;
            this.renderVisibleItems();
        }
    }

    /**
     * Sort deals array
     */
    sortDeals() {
        this.filteredDeals.sort((a, b) => {
            let valA, valB;

            switch (this.sortBy) {
                case 'price':
                    valA = parseFloat(a.price.replace(':-', '').replace(',', '.')) || 0;
                    valB = parseFloat(b.price.replace(':-', '').replace(',', '.')) || 0;
                    break;
                case 'store':
                    valA = a.store;
                    valB = b.store;
                    break;
                default: // name
                    valA = a.name.toLowerCase();
                    valB = b.name.toLowerCase();
            }

            if (valA < valB) return this.sortAsc ? -1 : 1;
            if (valA > valB) return this.sortAsc ? 1 : -1;
            return 0;
        });
    }

    /**
     * Filter deals based on search and store
     */
    filterDeals() {
        this.filteredDeals = this.deals.filter(deal => {
            const matchesSearch = !this.searchQuery ||
                deal.name.toLowerCase().includes(this.searchQuery) ||
                (deal.description && deal.description.toLowerCase().includes(this.searchQuery));

            const matchesStore = this.currentStore === 'all' ||
                deal.store === this.currentStore;

            return matchesSearch && matchesStore;
        });

        this.updateCount();
        this.render();
    }

    /**
     * Update deals count display
     */
    updateCount() {
        if (this.elements.countDisplay) {
            this.elements.countDisplay.textContent = this.filteredDeals.length;
        }
    }

    /**
     * Generate stable ID for a deal (survives filter/sort)
     */
    getDealId(deal) {
        return `${deal.store}|${deal.name}|${deal.price}`;
    }

    /**
     * Toggle deal selection by index
     */
    toggleSelection(idx) {
        const deal = this.filteredDeals[idx];
        if (!deal) return;

        const id = this.getDealId(deal);
        if (this.selectedIds.has(id)) {
            this.selectedIds.delete(id);
        } else {
            this.selectedIds.add(id);
        }
        this.updateSelectionUI();
    }

    /**
     * Select all visible deals
     */
    selectAll() {
        this.filteredDeals.forEach(deal => this.selectedIds.add(this.getDealId(deal)));
        this.renderVisibleItems();
        this.updateSelectionUI();
    }

    /**
     * Clear all selections
     */
    clearSelection() {
        this.selectedIds.clear();
        this.renderVisibleItems();
        this.updateSelectionUI();
    }

    /**
     * Get array of selected deal objects
     */
    getSelectedDeals() {
        return this.deals.filter(deal => this.selectedIds.has(this.getDealId(deal)));
    }

    /**
     * Update selection bar visibility and count
     */
    updateSelectionUI() {
        if (!this.elements.selectionBar) return;

        const count = this.selectedIds.size;
        const addBtn = /** @type {HTMLButtonElement | null} */ (document.getElementById('addToListBtn'));

        if (count > 0) {
            this.elements.selectionBar.classList.add('visible');
            if (this.elements.selectionCount) {
                this.elements.selectionCount.textContent = String(count);
            }
            if (addBtn) addBtn.disabled = false;
        } else {
            this.elements.selectionBar.classList.remove('visible');
            if (addBtn) addBtn.disabled = true;
        }

        // Sync select-all checkbox state
        const selectAllCheckbox = /** @type {HTMLInputElement | null} */ (document.getElementById('selectAllDeals'));
        if (selectAllCheckbox) {
            const allSelected = this.filteredDeals.length > 0 &&
                this.filteredDeals.every(deal => this.selectedIds.has(this.getDealId(deal)));
            const someSelected = this.selectedIds.size > 0;

            selectAllCheckbox.checked = allSelected;
            selectAllCheckbox.indeterminate = someSelected && !allSelected;
        }
    }

    /**
     * Called when entering the deals page
     */
    onEnter() {
        // Re-render in case data changed
        if (this.initialized) {
            // Re-attach window listeners
            if (this.boundHandlers.resize) {
                window.addEventListener('resize', this.boundHandlers.resize);
            }
            if (this.boundHandlers.scroll) {
                window.addEventListener('scroll', this.boundHandlers.scroll, { passive: true });
            }
            this.render();
        }
    }

    /**
     * Called when leaving the deals page
     */
    onLeave() {
        // Clear selections when navigating away
        this.clearSelection();

        // Cancel pending RAF
        if (this.scrollRAF) {
            cancelAnimationFrame(this.scrollRAF);
            this.scrollRAF = null;
        }

        // Clear debounce timer
        clearTimeout(this.searchDebounceTimer);

        // Remove event listeners
        if (this.boundHandlers.resize) {
            window.removeEventListener('resize', this.boundHandlers.resize);
        }
        if (this.boundHandlers.scroll) {
            window.removeEventListener('scroll', this.boundHandlers.scroll);
        }
    }

    /**
     * Get unique stores from deals
     */
    getStores() {
        const stores = new Map();
        this.deals.forEach(deal => {
            stores.set(deal.store, (stores.get(deal.store) || 0) + 1);
        });
        return Array.from(stores.entries())
            .sort((a, b) => b[1] - a[1])
            .map(([store]) => store);
    }

    /**
     * Render the deals list with virtual scroll
     */
    render() {
        if (!this.elements.container) return;

        if (this.filteredDeals.length === 0) {
            this.elements.container.innerHTML = `
                <div class="empty-state">
                    <h3>Inga erbjudanden hittades</h3>
                    <p>Prova att ändra din sökning eller filter</p>
                </div>
            `;
            return;
        }

        const totalHeight = this.filteredDeals.length * this.getItemHeight();

        if (this.isMobile) {
            this.elements.container.innerHTML = `
                <div class="deals-virtual-scroll" style="height: ${totalHeight}px; position: relative;">
                    <div class="deals-cards" id="dealsItems"></div>
                </div>
            `;
        } else {
            this.elements.container.innerHTML = `
                <div class="deals-table-wrapper">
                    <div class="deals-table">
                        <div class="deals-thead">
                            <div class="deals-tr deals-header-row">
                                <div class="deals-th deals-th-checkbox">
                                    <label class="deal-checkbox-label">
                                        <input type="checkbox" class="deal-select-all" id="selectAllDeals">
                                        <span class="deal-checkbox-custom"></span>
                                    </label>
                                </div>
                                <div class="deals-th deals-th-image"></div>
                                <div class="deals-th deals-th-name" data-sort="name" tabindex="0" role="button" aria-label="Sortera efter produkt">
                                    Produkt ${this.sortBy === 'name' ? (this.sortAsc ? '↑' : '↓') : ''}
                                </div>
                                <div class="deals-th deals-th-price" data-sort="price" tabindex="0" role="button" aria-label="Sortera efter pris">
                                    Pris ${this.sortBy === 'price' ? (this.sortAsc ? '↑' : '↓') : ''}
                                </div>
                                <div class="deals-th deals-th-original">Ord. pris</div>
                                <div class="deals-th deals-th-store" data-sort="store" tabindex="0" role="button" aria-label="Sortera efter butik">
                                    Butik ${this.sortBy === 'store' ? (this.sortAsc ? '↑' : '↓') : ''}
                                </div>
                                <div class="deals-th deals-th-desc">Beskrivning</div>
                            </div>
                        </div>
                        <div class="deals-tbody" style="height: ${totalHeight}px; position: relative;" id="dealsItems">
                        </div>
                    </div>
                </div>
            `;
        }

        // Initial visible range
        this.visibleStart = 0;
        this.visibleEnd = Math.min(this.filteredDeals.length, Math.ceil(window.innerHeight / this.getItemHeight()) + this.BUFFER_SIZE);
        this.renderVisibleItems();
        this.updateSelectionUI();
    }

    /**
     * Render only visible items (virtual scroll)
     */
    renderVisibleItems() {
        const container = document.getElementById('dealsItems');
        if (!container) return;

        const itemHeight = this.getItemHeight();
        const items = this.filteredDeals.slice(this.visibleStart, this.visibleEnd);

        if (this.isMobile) {
            container.innerHTML = items.map((deal, i) => {
                const idx = this.visibleStart + i;
                const top = idx * itemHeight;
                return this.renderCard(deal, idx, top);
            }).join('');
        } else {
            container.innerHTML = items.map((deal, i) => {
                const idx = this.visibleStart + i;
                const top = idx * itemHeight;
                return this.renderRow(deal, idx, top);
            }).join('');
        }
    }

    /**
     * Render a table row (desktop)
     */
    renderRow(deal, idx, top) {
        const storeClass = Utils.getStoreClass(deal.store);
        const isSelected = this.selectedIds.has(this.getDealId(deal));
        const shortDesc = this.truncate(deal.description, 60);

        return `
            <div class="deals-tr ${isSelected ? 'selected' : ''}" style="position: absolute; top: ${top}px; left: 0; right: 0; height: ${this.ROW_HEIGHT}px;">
                <div class="deals-td deals-td-checkbox">
                    <label class="deal-checkbox-label">
                        <input type="checkbox" class="deal-checkbox" data-idx="${idx}" ${isSelected ? 'checked' : ''}>
                        <span class="deal-checkbox-custom"></span>
                    </label>
                </div>
                <div class="deals-td deals-td-image">
                    ${deal.image
                        ? `<img class="deal-thumb-img" src="${Utils.escapeHtml(deal.image)}" alt="" loading="lazy">`
                        : `<div class="deal-thumb ${storeClass}">${this.getStoreIcon(deal.store)}</div>`
                    }
                </div>
                <div class="deals-td deals-td-name">
                    <span class="deal-name">${Utils.escapeHtml(deal.name)}</span>
                    ${deal.unit ? `<span class="deal-unit">${Utils.escapeHtml(deal.unit)}</span>` : ''}
                </div>
                <div class="deals-td deals-td-price">
                    <span class="deal-price">${Utils.escapeHtml(deal.price)}</span>
                </div>
                <div class="deals-td deals-td-original">
                    ${deal.ord_pris ? `<span class="deal-original-price">${Utils.escapeHtml(deal.ord_pris)}</span>` : '—'}
                </div>
                <div class="deals-td deals-td-store">
                    <span class="deal-store-badge ${storeClass}">${Utils.escapeHtml(Utils.getShortStoreName(deal.store))}</span>
                </div>
                <div class="deals-td deals-td-desc">
                    <span class="deal-desc">${Utils.escapeHtml(shortDesc)}</span>
                </div>
            </div>
        `;
    }

    /**
     * Render a card (mobile) - ICA-inspired horizontal layout
     */
    renderCard(deal, idx, top) {
        const storeClass = Utils.getStoreClass(deal.store);
        const isSelected = this.selectedIds.has(this.getDealId(deal));

        // Build description with price comparison info
        const descParts = [];
        if (deal.description) descParts.push(deal.description);
        if (deal.jfr_pris) descParts.push(`Jmfpris ${deal.jfr_pris}`);
        const fullDesc = descParts.join('. ');

        return `
            <article class="deal-card ${storeClass} ${isSelected ? 'selected' : ''}" style="position: absolute; top: ${top}px; left: 0; right: 0; height: ${this.CARD_HEIGHT - 12}px;">
                <div class="deal-card-media">
                    ${deal.image
                        ? `<img class="deal-card-img" src="${Utils.escapeHtml(deal.image)}" alt="${Utils.escapeHtml(deal.name)}" loading="lazy">`
                        : `<div class="deal-card-placeholder ${storeClass}">${this.getStoreIcon(deal.store)}</div>`
                    }
                    <div class="deal-card-price-tag ${storeClass}">
                        <span class="price-value">${Utils.escapeHtml(deal.price)}</span>
                        ${deal.unit && deal.unit !== '/st' ? `<span class="price-unit">${Utils.escapeHtml(deal.unit)}</span>` : ''}
                    </div>
                </div>
                <div class="deal-card-content">
                    <div class="deal-card-info">
                        <h3 class="deal-card-title">${Utils.escapeHtml(deal.name)}</h3>
                        <p class="deal-card-meta">${Utils.escapeHtml(fullDesc)}</p>
                    </div>
                    <button class="deal-card-cta ${isSelected ? 'added' : ''}" data-idx="${idx}" aria-label="${isSelected ? 'Ta bort från lista' : 'Lägg i inköpslista'}">
                        <svg class="cta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            ${isSelected
                                ? `<path d="M20 6L9 17l-5-5"/>`
                                : `<path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>`
                            }
                        </svg>
                        <span class="cta-text">${isSelected ? 'Tillagd' : 'Lägg i inköpslista'}</span>
                    </button>
                </div>
            </article>
        `;
    }

    /**
     * Get store icon SVG
     */
    getStoreIcon(_store) {
        // Simple grocery bag icon as placeholder
        return `
            <svg class="deal-store-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/>
                <path d="M3 6h18"/>
                <path d="M16 10a4 4 0 01-8 0"/>
            </svg>
        `;
    }

    /**
     * Truncate string with ellipsis
     */
    truncate(str, len) {
        if (!str) return '';
        return str.length > len ? str.substring(0, len) + '...' : str;
    }

    /**
     * Show error state
     */
    showError() {
        if (this.elements.container) {
            this.elements.container.innerHTML = `
                <div class="empty-state" role="alert">
                    <h3>Kunde inte ladda erbjudanden</h3>
                    <p>Försök ladda om sidan</p>
                </div>
            `;
        }
    }
}

// Singleton instance
const dealsApp = new DealsApp();

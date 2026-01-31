/**
 * Shopping Lists - Data storage, UI components, and page logic
 */

// ============================================
// LISTS STORAGE - localStorage CRUD
// ============================================

const ListsStorage = {
    STORAGE_KEY: 'shopping-lists',

    /**
     * Generate unique ID
     */
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substring(2, 7);
    },

    /**
     * Get default list name with current date
     */
    getDefaultName() {
        const now = new Date();
        const day = now.getDate();
        const month = now.toLocaleDateString('sv-SE', { month: 'long' });
        return `Att handla ${day} ${month}`;
    },

    /**
     * Get all lists from storage
     */
    getAll() {
        try {
            const data = localStorage.getItem(this.STORAGE_KEY);
            return data ? JSON.parse(data) : [];
        } catch (e) {
            console.error('Failed to read lists:', e);
            return [];
        }
    },

    /**
     * Save all lists to storage
     */
    save(lists) {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(lists));
            return true;
        } catch (e) {
            console.error('Failed to save lists:', e);
            return false;
        }
    },

    /**
     * Get a list by ID
     */
    getById(id) {
        const lists = this.getAll();
        return lists.find(list => list.id === id) || null;
    },

    /**
     * Create a new list
     */
    create(name) {
        const now = Date.now();
        const list = {
            id: this.generateId(),
            name: name || this.getDefaultName(),
            createdAt: now,
            updatedAt: now,
            items: []
        };
        const lists = this.getAll();
        lists.unshift(list); // Add to beginning (most recent first)
        this.save(lists);
        return list;
    },

    /**
     * Update a list
     */
    update(id, updates) {
        const lists = this.getAll();
        const idx = lists.findIndex(list => list.id === id);
        if (idx === -1) return null;

        lists[idx] = {
            ...lists[idx],
            ...updates,
            updatedAt: Date.now()
        };

        // Move to front (most recently updated first)
        const [updated] = lists.splice(idx, 1);
        lists.unshift(updated);

        this.save(lists);
        return updated;
    },

    /**
     * Delete a list
     */
    delete(id) {
        const lists = this.getAll();
        const filtered = lists.filter(list => list.id !== id);
        if (filtered.length !== lists.length) {
            this.save(filtered);
            return true;
        }
        return false;
    },

    /**
     * Add items to a list, returns { added, duplicates }
     */
    addItems(listId, items) {
        const list = this.getById(listId);
        if (!list) return { added: 0, duplicates: 0 };

        const existingIds = new Set(list.items.map(item => item.id));
        let added = 0;
        let duplicates = 0;

        items.forEach(item => {
            if (existingIds.has(item.id)) {
                duplicates++;
            } else {
                list.items.push({
                    ...item,
                    checked: false,
                    addedAt: Date.now()
                });
                added++;
            }
        });

        if (added > 0) {
            this.update(listId, { items: list.items });
        }

        return { added, duplicates };
    },

    /**
     * Toggle item checked state
     */
    toggleItemChecked(listId, itemId) {
        const list = this.getById(listId);
        if (!list) return false;

        const item = list.items.find(i => i.id === itemId);
        if (item) {
            item.checked = !item.checked;
            this.update(listId, { items: list.items });
            return true;
        }
        return false;
    },

    /**
     * Remove checked items from a list
     */
    clearChecked(listId) {
        const list = this.getById(listId);
        if (!list) return 0;

        const beforeCount = list.items.length;
        list.items = list.items.filter(item => !item.checked);
        const removed = beforeCount - list.items.length;

        if (removed > 0) {
            this.update(listId, { items: list.items });
        }
        return removed;
    }
};

// ============================================
// TOAST NOTIFICATIONS
// ============================================

const Toast = {
    container: null,

    /**
     * Initialize toast container
     */
    init() {
        if (this.container) return;
        this.container = document.getElementById('toastContainer');
    },

    /**
     * Show a toast message
     */
    show(message, duration = 3000) {
        this.init();
        if (!this.container) return;

        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        this.container.appendChild(toast);

        // Trigger animation
        requestAnimationFrame(() => {
            toast.classList.add('visible');
        });

        // Auto remove
        setTimeout(() => {
            toast.classList.remove('visible');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
};

// ============================================
// BOTTOM SHEET COMPONENT
// ============================================

class BottomSheet {
    constructor() {
        this.overlay = null;
        this.sheet = null;
        this.isOpenState = false;
        this.boundHandleKeydown = this.handleKeydown.bind(this);
    }

    /**
     * Initialize DOM references
     */
    init() {
        this.overlay = document.getElementById('bottomSheetOverlay');
        this.sheet = document.getElementById('bottomSheetContent');

        if (this.overlay) {
            this.overlay.addEventListener('click', (e) => {
                if (e.target === this.overlay) {
                    this.close();
                }
            });
        }
    }

    /**
     * Open sheet with HTML content
     */
    open(html) {
        if (!this.sheet || !this.overlay) this.init();
        if (!this.sheet || !this.overlay) return;

        this.sheet.innerHTML = html;
        this.overlay.classList.add('visible');
        document.body.classList.add('sheet-open');
        this.isOpenState = true;

        document.addEventListener('keydown', this.boundHandleKeydown);

        // Focus first focusable element
        requestAnimationFrame(() => {
            const focusable = /** @type {HTMLElement | null} */ (this.sheet.querySelector('button, input, [tabindex]:not([tabindex="-1"])'));
            if (focusable) focusable.focus();
        });
    }

    /**
     * Close sheet
     */
    close() {
        if (!this.overlay) return;

        this.overlay.classList.remove('visible');
        document.body.classList.remove('sheet-open');
        this.isOpenState = false;

        document.removeEventListener('keydown', this.boundHandleKeydown);
    }

    /**
     * Handle escape key
     */
    handleKeydown(e) {
        if (e.key === 'Escape' && this.isOpenState) {
            this.close();
        }
    }

    /**
     * Check if sheet is open
     */
    isOpen() {
        return this.isOpenState;
    }
}

// Singleton instance
const bottomSheet = new BottomSheet();

// ============================================
// LISTS APP - Page controller
// ============================================

class ListsApp {
    constructor() {
        this.initialized = false;
        this.currentView = 'list'; // 'list' or 'detail'
        this.currentListId = null;
        this.elements = {};
    }

    /**
     * Initialize the lists page
     */
    init() {
        if (this.initialized) {
            this.onEnter();
            return;
        }

        this.cacheElements();
        bottomSheet.init();
        Toast.init();
        this.bindEvents();
        this.render();
        this.initialized = true;
    }

    /**
     * Cache DOM references
     */
    cacheElements() {
        this.elements = {
            page: document.getElementById('pageLists'),
            container: document.getElementById('listsContainer')
        };
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        if (!this.elements.container) return;

        // Event delegation for list interactions
        this.elements.container.addEventListener('click', (e) => {
            // List card click
            const card = e.target.closest('.list-card');
            if (card && !e.target.closest('.list-menu-btn')) {
                const listId = card.dataset.listId;
                this.showDetailView(listId);
                return;
            }

            // Menu button click
            const menuBtn = e.target.closest('.list-menu-btn');
            if (menuBtn) {
                e.stopPropagation();
                const listId = menuBtn.dataset.listId;
                this.showListMenu(listId, menuBtn);
                return;
            }

            // Back button in detail view
            if (e.target.closest('.list-back-btn')) {
                this.showListView();
                return;
            }

            // Item checkbox
            const checkbox = e.target.closest('.list-item-checkbox');
            if (checkbox) {
                const itemId = checkbox.dataset.itemId;
                this.toggleItemChecked(itemId);
                return;
            }

            // Clear checked button
            if (e.target.closest('.clear-checked-btn')) {
                this.clearCheckedItems();
                return;
            }

            // Create new list button (empty state)
            if (e.target.closest('.create-list-btn')) {
                this.showCreateListForm();
                return;
            }
        });

        // Name editing (blur to save)
        this.elements.container.addEventListener('blur', (e) => {
            if (e.target.classList.contains('list-name-editable')) {
                const newName = e.target.textContent.trim();
                if (newName && this.currentListId) {
                    ListsStorage.update(this.currentListId, { name: newName });
                }
            }
        }, true);

        // Prevent enter key in editable name (save on enter)
        this.elements.container.addEventListener('keydown', (e) => {
            if (e.target.classList.contains('list-name-editable') && e.key === 'Enter') {
                e.preventDefault();
                e.target.blur();
            }
        });
    }

    /**
     * Called when entering the lists page
     */
    onEnter() {
        if (this.currentView === 'detail' && this.currentListId) {
            this.renderDetailView(this.currentListId);
        } else {
            this.render();
        }
    }

    /**
     * Called when leaving the lists page
     */
    onLeave() {
        // Close any open menus
        const menu = document.querySelector('.list-menu-dropdown.visible');
        if (menu) menu.remove();
    }

    /**
     * Show add-to-list bottom sheet
     */
    showAddToListSheet(deals) {
        const lists = ListsStorage.getAll();

        let html = `
            <div class="sheet-header">
                <h2 class="sheet-title">Spara till lista</h2>
                <p class="sheet-subtitle">${deals.length} ${deals.length === 1 ? 'vara' : 'varor'} valda</p>
            </div>
            <div class="sheet-body">
        `;

        if (lists.length > 0) {
            html += `<div class="sheet-lists">`;
            lists.forEach(list => {
                const itemCount = list.items.length;
                const stores = [...new Set(list.items.map(i => i.store))];
                html += `
                    <button class="sheet-list-btn" data-list-id="${Utils.escapeHtml(list.id)}">
                        <div class="sheet-list-info">
                            <span class="sheet-list-name">${Utils.escapeHtml(list.name)}</span>
                            <span class="sheet-list-meta">${itemCount} ${itemCount === 1 ? 'vara' : 'varor'}</span>
                        </div>
                        <div class="sheet-list-stores">
                            ${stores.slice(0, 3).map(store => {
                                const storeClass = Utils.getStoreClass(store);
                                return `<span class="sheet-store-dot ${storeClass}"></span>`;
                            }).join('')}
                        </div>
                    </button>
                `;
            });
            html += `</div>`;
        }

        html += `
                <button class="sheet-create-btn" id="sheetCreateListBtn">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 5v14M5 12h14"/>
                    </svg>
                    <span>Skapa ny lista</span>
                </button>
            </div>
        `;

        bottomSheet.open(html);

        // Bind sheet events
        const sheetContent = document.getElementById('bottomSheetContent');
        if (sheetContent) {
            sheetContent.addEventListener('click', (e) => {
                const target = /** @type {HTMLElement} */ (e.target);
                // Add to existing list
                const listBtn = /** @type {HTMLElement | null} */ (target.closest('.sheet-list-btn'));
                if (listBtn) {
                    const listId = listBtn.dataset.listId;
                    this.addDealsToList(listId, deals);
                    return;
                }

                // Create new list
                if (target.closest('#sheetCreateListBtn')) {
                    this.showCreateListForm(deals);
                    return;
                }
            });
        }
    }

    /**
     * Show create list form in bottom sheet
     */
    showCreateListForm(deals = null) {
        const defaultName = ListsStorage.getDefaultName();

        const html = `
            <div class="sheet-header">
                <h2 class="sheet-title">Skapa ny lista</h2>
            </div>
            <div class="sheet-body">
                <div class="sheet-form">
                    <label class="sheet-label" for="newListName">Namn</label>
                    <input type="text" id="newListName" class="sheet-input" value="${Utils.escapeHtml(defaultName)}" placeholder="Listans namn">
                </div>
                <div class="sheet-actions">
                    <button class="sheet-btn secondary" id="sheetCancelBtn">Avbryt</button>
                    <button class="sheet-btn primary" id="sheetSaveBtn">Skapa</button>
                </div>
            </div>
        `;

        bottomSheet.open(html);

        // Focus and select input
        const input = /** @type {HTMLInputElement | null} */ (document.getElementById('newListName'));
        if (input) {
            input.focus();
            input.select();
        }

        // Bind form events
        const saveBtn = document.getElementById('sheetSaveBtn');
        const cancelBtn = document.getElementById('sheetCancelBtn');

        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                const name = input?.value.trim() || defaultName;
                const list = ListsStorage.create(name);

                if (deals && deals.length > 0) {
                    const items = deals.map(deal => ({
                        id: `${deal.store}|${deal.name}|${deal.price}`,
                        name: deal.name,
                        price: deal.price,
                        store: deal.store,
                        image: deal.image || null
                    }));
                    ListsStorage.addItems(list.id, items);
                    Toast.show(`${deals.length} varor tillagda i "${list.name}"`);
                    dealsApp.clearSelection();
                } else {
                    Toast.show(`Lista "${list.name}" skapad`);
                }

                bottomSheet.close();
                this.render();
            });
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                bottomSheet.close();
            });
        }

        // Enter key to save
        if (input) {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    saveBtn?.click();
                }
            });
        }
    }

    /**
     * Add deals to an existing list
     */
    addDealsToList(listId, deals) {
        const list = ListsStorage.getById(listId);
        if (!list) return;

        const items = deals.map(deal => ({
            id: `${deal.store}|${deal.name}|${deal.price}`,
            name: deal.name,
            price: deal.price,
            store: deal.store,
            image: deal.image || null
        }));

        const result = ListsStorage.addItems(listId, items);

        if (result.duplicates > 0 && result.added === 0) {
            Toast.show(`${result.duplicates} varor redan i listan`);
        } else if (result.duplicates > 0) {
            Toast.show(`${result.added} tillagda, ${result.duplicates} redan i listan`);
        } else {
            Toast.show(`Tillagd i "${list.name}"`);
        }

        bottomSheet.close();
        dealsApp.clearSelection();
        this.render();
    }

    /**
     * Render main list view
     */
    render() {
        if (!this.elements.container) return;

        this.currentView = 'list';
        this.currentListId = null;

        const lists = ListsStorage.getAll();

        if (lists.length === 0) {
            this.elements.container.innerHTML = `
                <div class="lists-empty-state">
                    <div class="empty-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/>
                            <rect x="9" y="2" width="6" height="4" rx="1"/>
                            <path d="M12 11v6M9 14h6"/>
                        </svg>
                    </div>
                    <h3 class="empty-title">Inga inköpslistor</h3>
                    <p class="empty-text">Välj erbjudanden att spara till en lista</p>
                    <button class="create-list-btn">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 5v14M5 12h14"/>
                        </svg>
                        Skapa lista
                    </button>
                </div>
            `;
            return;
        }

        const cardsHtml = lists.map(list => this.renderListCard(list)).join('');

        this.elements.container.innerHTML = `
            <div class="lists-header">
                <h2 class="lists-title">Inköpslistor</h2>
                <span class="lists-count">${lists.length} ${lists.length === 1 ? 'lista' : 'listor'}</span>
            </div>
            <div class="lists-grid">
                ${cardsHtml}
            </div>
        `;
    }

    /**
     * Render a list card
     */
    renderListCard(list) {
        const itemCount = list.items.length;
        const checkedCount = list.items.filter(i => i.checked).length;
        const stores = [...new Set(list.items.map(i => i.store))];
        const timeAgo = this.formatTimeAgo(list.updatedAt);

        return `
            <article class="list-card" data-list-id="${Utils.escapeHtml(list.id)}">
                <div class="list-card-header">
                    <h3 class="list-card-name">${Utils.escapeHtml(list.name)}</h3>
                    <button class="list-menu-btn" data-list-id="${Utils.escapeHtml(list.id)}" aria-label="Meny">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="6" r="1.5"/>
                            <circle cx="12" cy="12" r="1.5"/>
                            <circle cx="12" cy="18" r="1.5"/>
                        </svg>
                    </button>
                </div>
                <div class="list-card-meta">
                    <span class="list-card-count">${itemCount} ${itemCount === 1 ? 'vara' : 'varor'}${checkedCount > 0 ? ` (${checkedCount} klar)` : ''}</span>
                    <span class="list-card-time">${timeAgo}</span>
                </div>
                <div class="list-card-stores">
                    ${stores.slice(0, 4).map(store => {
                        const storeClass = Utils.getStoreClass(store);
                        return `<span class="list-store-badge ${storeClass}">${Utils.escapeHtml(Utils.getShortStoreName(store))}</span>`;
                    }).join('')}
                    ${stores.length > 4 ? `<span class="list-store-badge">+${stores.length - 4}</span>` : ''}
                </div>
            </article>
        `;
    }

    /**
     * Show list detail view
     */
    showDetailView(listId) {
        this.currentView = 'detail';
        this.currentListId = listId;
        this.renderDetailView(listId);
    }

    /**
     * Render detail view for a list
     */
    renderDetailView(listId) {
        const list = ListsStorage.getById(listId);
        if (!list || !this.elements.container) {
            this.render();
            return;
        }

        // Group items by store, unchecked first
        const uncheckedItems = list.items.filter(i => !i.checked);
        const checkedItems = list.items.filter(i => i.checked);

        // Group unchecked by store
        const storeGroups = {};
        uncheckedItems.forEach(item => {
            const store = item.store;
            if (!storeGroups[store]) storeGroups[store] = [];
            storeGroups[store].push(item);
        });

        let itemsHtml = '';

        // Render unchecked items grouped by store
        Object.entries(storeGroups).forEach(([store, items]) => {
            const storeClass = Utils.getStoreClass(store);
            itemsHtml += `
                <div class="list-store-group">
                    <div class="list-store-header ${storeClass}">
                        <span class="store-dot ${storeClass}"></span>
                        <span class="store-name">${Utils.escapeHtml(Utils.getShortStoreName(store))}</span>
                        <span class="store-count">${items.length}</span>
                    </div>
                    <div class="list-items">
                        ${items.map(item => this.renderListItem(item)).join('')}
                    </div>
                </div>
            `;
        });

        // Render checked items section
        if (checkedItems.length > 0) {
            itemsHtml += `
                <div class="list-checked-section">
                    <div class="list-checked-header">
                        <span class="checked-title">Klart</span>
                        <span class="checked-count">${checkedItems.length}</span>
                        <button class="clear-checked-btn">Rensa</button>
                    </div>
                    <div class="list-items checked">
                        ${checkedItems.map(item => this.renderListItem(item)).join('')}
                    </div>
                </div>
            `;
        }

        // Empty state if no items
        if (list.items.length === 0) {
            itemsHtml = `
                <div class="list-empty-state">
                    <p>Listan är tom</p>
                    <a href="#/deals" class="list-add-link">Lägg till erbjudanden</a>
                </div>
            `;
        }

        this.elements.container.innerHTML = `
            <div class="list-detail">
                <div class="list-detail-header">
                    <button class="list-back-btn" aria-label="Tillbaka">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M19 12H5M12 19l-7-7 7-7"/>
                        </svg>
                    </button>
                    <h2 class="list-name-editable" contenteditable="true" spellcheck="false">${Utils.escapeHtml(list.name)}</h2>
                </div>
                <div class="list-detail-content">
                    ${itemsHtml}
                </div>
            </div>
        `;
    }

    /**
     * Render a single list item
     */
    renderListItem(item) {
        const storeClass = Utils.getStoreClass(item.store);

        return `
            <div class="list-item ${item.checked ? 'checked' : ''}" data-item-id="${Utils.escapeHtml(item.id)}">
                <label class="list-item-checkbox" data-item-id="${Utils.escapeHtml(item.id)}">
                    <input type="checkbox" ${item.checked ? 'checked' : ''}>
                    <span class="checkbox-custom"></span>
                </label>
                <div class="list-item-info">
                    <span class="list-item-name">${Utils.escapeHtml(item.name)}</span>
                    <span class="list-item-price ${storeClass}">${Utils.escapeHtml(item.price)}</span>
                </div>
                ${item.image ? `<img class="list-item-image" src="${Utils.escapeHtml(item.image)}" alt="" loading="lazy">` : ''}
            </div>
        `;
    }

    /**
     * Toggle item checked state
     */
    toggleItemChecked(itemId) {
        if (!this.currentListId) return;
        ListsStorage.toggleItemChecked(this.currentListId, itemId);
        this.renderDetailView(this.currentListId);
    }

    /**
     * Clear all checked items
     */
    clearCheckedItems() {
        if (!this.currentListId) return;
        const removed = ListsStorage.clearChecked(this.currentListId);
        if (removed > 0) {
            Toast.show(`${removed} ${removed === 1 ? 'vara' : 'varor'} rensade`);
        }
        this.renderDetailView(this.currentListId);
    }

    /**
     * Show list view (back from detail)
     */
    showListView() {
        this.currentView = 'list';
        this.currentListId = null;
        this.render();
    }

    /**
     * Show list menu dropdown
     */
    showListMenu(listId, button) {
        // Close any existing menu
        const existing = document.querySelector('.list-menu-dropdown');
        if (existing) existing.remove();

        const rect = button.getBoundingClientRect();

        const menu = document.createElement('div');
        menu.className = 'list-menu-dropdown visible';
        menu.innerHTML = `
            <button class="menu-item rename" data-action="rename">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17 3a2.85 2.83 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z"/>
                </svg>
                Byt namn
            </button>
            <button class="menu-item delete" data-action="delete">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                </svg>
                Ta bort
            </button>
        `;
        menu.style.top = `${rect.bottom + 4}px`;
        menu.style.right = `${window.innerWidth - rect.right}px`;

        document.body.appendChild(menu);

        // Menu actions
        menu.addEventListener('click', (e) => {
            const target = /** @type {HTMLElement} */ (e.target);
            const menuItem = /** @type {HTMLElement | null} */ (target.closest('.menu-item'));
            const action = menuItem?.dataset.action;
            if (action === 'rename') {
                this.renameList(listId);
            } else if (action === 'delete') {
                this.deleteList(listId);
            }
            menu.remove();
        });

        // Close on outside click
        const closeMenu = (e) => {
            if (!menu.contains(e.target) && e.target !== button) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        };
        setTimeout(() => document.addEventListener('click', closeMenu), 0);
    }

    /**
     * Rename a list
     */
    renameList(listId) {
        const list = ListsStorage.getById(listId);
        if (!list) return;

        const html = `
            <div class="sheet-header">
                <h2 class="sheet-title">Byt namn</h2>
            </div>
            <div class="sheet-body">
                <div class="sheet-form">
                    <label class="sheet-label" for="renameListInput">Namn</label>
                    <input type="text" id="renameListInput" class="sheet-input" value="${Utils.escapeHtml(list.name)}">
                </div>
                <div class="sheet-actions">
                    <button class="sheet-btn secondary" id="renameCancelBtn">Avbryt</button>
                    <button class="sheet-btn primary" id="renameSaveBtn">Spara</button>
                </div>
            </div>
        `;

        bottomSheet.open(html);

        const input = /** @type {HTMLInputElement | null} */ (document.getElementById('renameListInput'));
        const saveBtn = document.getElementById('renameSaveBtn');
        const cancelBtn = document.getElementById('renameCancelBtn');

        if (input) {
            input.focus();
            input.select();
        }

        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                const newName = input?.value.trim();
                if (newName) {
                    ListsStorage.update(listId, { name: newName });
                    Toast.show('Namn uppdaterat');
                    this.render();
                }
                bottomSheet.close();
            });
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => bottomSheet.close());
        }

        if (input) {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') saveBtn?.click();
            });
        }
    }

    /**
     * Delete a list
     */
    deleteList(listId) {
        const list = ListsStorage.getById(listId);
        if (!list) return;

        const html = `
            <div class="sheet-header">
                <h2 class="sheet-title">Ta bort lista?</h2>
                <p class="sheet-subtitle">"${Utils.escapeHtml(list.name)}" med ${list.items.length} ${list.items.length === 1 ? 'vara' : 'varor'}</p>
            </div>
            <div class="sheet-body">
                <div class="sheet-actions">
                    <button class="sheet-btn secondary" id="deleteCancelBtn">Avbryt</button>
                    <button class="sheet-btn danger" id="deleteConfirmBtn">Ta bort</button>
                </div>
            </div>
        `;

        bottomSheet.open(html);

        const confirmBtn = document.getElementById('deleteConfirmBtn');
        const cancelBtn = document.getElementById('deleteCancelBtn');

        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => {
                ListsStorage.delete(listId);
                Toast.show(`"${list.name}" borttagen`);
                bottomSheet.close();
                this.render();
            });
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => bottomSheet.close());
        }
    }

    /**
     * Format time ago string
     */
    formatTimeAgo(timestamp) {
        const now = Date.now();
        const diff = now - timestamp;

        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return 'Just nu';
        if (minutes < 60) return `${minutes} min sedan`;
        if (hours < 24) return `${hours} tim sedan`;
        if (days === 1) return 'Igår';
        if (days < 7) return `${days} dagar sedan`;

        const date = new Date(timestamp);
        return date.toLocaleDateString('sv-SE', { day: 'numeric', month: 'short' });
    }
}

// Singleton instance
const listsApp = new ListsApp();

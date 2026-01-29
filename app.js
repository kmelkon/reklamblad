/**
 * Veckans Recept - Recipe & Deals App
 */

class RecipeApp {
    constructor() {
        this.recipes = [];
        this.deals = [];
        this.filteredRecipes = [];
        this.currentStore = 'all';
        this.searchQuery = '';
        this.currentSort = 'match';
        this.currentCategory = 'all';
        this.categories = [];

        this.elements = {
            recipeGrid: document.getElementById('recipeGrid'),
            searchInput: document.getElementById('searchInput'),
            filterGroup: document.getElementById('filterGroup'),
            lastUpdated: document.getElementById('lastUpdated'),
            recipeCount: document.getElementById('recipeCount'),
            dealCount: document.getElementById('dealCount'),
            sortSelect: document.getElementById('sortSelect'),
            categoryPills: document.getElementById('categoryPills'),
        };

        this.filtersExpanded = false;

        // Validate required elements
        const required = ['recipeGrid', 'searchInput', 'sortSelect', 'categoryPills', 'filterGroup'];
        for (const id of required) {
            if (!this.elements[id]) {
                console.error(`Missing required element: #${id}`);
                return;
            }
        }

        this.init();
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    async init() {
        await this.loadData();
        this.bindEvents();
        this.render();
    }

    async loadData() {
        try {
            const [matchesRes, dealsRes] = await Promise.all([
                fetch('recipe_matches.json'),
                fetch('deals.json')
            ]);

            if (!matchesRes.ok || !dealsRes.ok) {
                throw new Error('Failed to fetch data');
            }

            const matchesData = await matchesRes.json();
            const dealsData = await dealsRes.json();

            this.recipes = matchesData.recipes || [];
            this.deals = dealsData || [];
            this.lastUpdated = matchesData.last_updated;
            this.filteredRecipes = [...this.recipes];

            // Calculate global average rating for IMDB-style weighted sorting
            const recipesWithRating = this.recipes.filter(r => r.rating && r.reviews);
            if (recipesWithRating.length > 0) {
                const totalRating = recipesWithRating.reduce((sum, r) => sum + r.rating, 0);
                this.globalAvgRating = totalRating / recipesWithRating.length;
            } else {
                this.globalAvgRating = 4.5; // fallback
            }
            this.minReviewsForTrust = 25; // m parameter - tunable

            // Extract unique categories (split comma-separated)
            const categorySet = new Set();
            this.recipes.forEach(r => {
                if (r.category) {
                    r.category.split(',').forEach(c => {
                        const trimmed = c.trim();
                        if (trimmed) categorySet.add(trimmed);
                    });
                }
            });
            this.categories = Array.from(categorySet).sort();
            this.renderCategoryPills();

            // Build store filter buttons
            this.renderStoreFilters();

            this.updateStats();
            this.updateLastUpdated();
        } catch (error) {
            console.error('Failed to load data:', error);
            this.showError();
        }
    }

    bindEvents() {
        // Search
        this.elements.searchInput.addEventListener('input', (e) => {
            this.searchQuery = e.target.value.toLowerCase().trim();
            this.filterRecipes();
        });

        // Sort select
        this.elements.sortSelect.addEventListener('change', (e) => {
            this.currentSort = e.target.value;
            this.filterRecipes();
        });

        // Category pills (event delegation)
        this.elements.categoryPills.addEventListener('click', (e) => {
            const pill = e.target.closest('.category-pill');
            if (!pill) return;
            this.elements.categoryPills.querySelectorAll('.category-pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            this.currentCategory = pill.dataset.category;
            this.filterRecipes();
        });
    }

    renderCategoryPills() {
        const container = this.elements.categoryPills;
        const allPill = `<button class="category-pill active" data-category="all">Alla</button>`;
        const pills = this.categories.map(cat =>
            `<button class="category-pill" data-category="${this.escapeHtml(cat)}">${this.escapeHtml(cat)}</button>`
        ).join('');
        container.innerHTML = allPill + pills;
    }

    renderStoreFilters() {
        // Count deals per store
        const storeCounts = {};
        this.deals.forEach(deal => {
            const store = deal.store;
            storeCounts[store] = (storeCounts[store] || 0) + 1;
        });

        // Sort stores by deal count (descending)
        const sortedStores = Object.entries(storeCounts)
            .sort((a, b) => b[1] - a[1])
            .map(([store]) => store);

        const PRIMARY_COUNT = 3;
        const primaryStores = sortedStores.slice(0, PRIMARY_COUNT);
        const overflowStores = sortedStores.slice(PRIMARY_COUNT);

        const container = this.elements.filterGroup;

        // "Alla butiker" button
        let html = `
            <button class="filter-btn active" data-store="all">
                <span class="filter-icon">◉</span>
                Alla butiker
            </button>
        `;

        // Primary store buttons
        primaryStores.forEach(store => {
            const storeClass = this.getStoreClass(store);
            const shortName = this.getShortStoreName(store);
            html += `
                <button class="filter-btn" data-store="${this.escapeHtml(store)}">
                    <span class="filter-dot ${storeClass}"></span>
                    ${this.escapeHtml(shortName)}
                </button>
            `;
        });

        // Overflow toggle + container
        if (overflowStores.length > 0) {
            html += `
                <button class="filter-toggle" id="filterToggle">
                    <span>Fler</span>
                    <span class="filter-count">${overflowStores.length}</span>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M9 18l6-6-6-6"/>
                    </svg>
                </button>
                <div class="filter-overflow" id="filterOverflow">
            `;

            overflowStores.forEach(store => {
                const storeClass = this.getStoreClass(store);
                const shortName = this.getShortStoreName(store);
                html += `
                    <button class="filter-btn" data-store="${this.escapeHtml(store)}">
                        <span class="filter-dot ${storeClass}"></span>
                        ${this.escapeHtml(shortName)}
                    </button>
                `;
            });

            html += `</div>`;
        }

        container.innerHTML = html;
        this.bindFilterEvents();
    }

    getShortStoreName(store) {
        // Return shorter display names for buttons
        if (store === 'ICA Supermarket') return 'ICA';
        if (store === 'ICA Nära') return 'ICA Nära';
        if (store === 'ICA Maxi') return 'ICA Maxi';
        if (store === 'ICA Kvantum') return 'ICA Kvantum';
        if (store === 'Stora Coop') return 'Stora Coop';
        if (store === 'Coop') return 'Coop';
        if (store === 'Willys') return 'Willys';
        return store;
    }

    bindFilterEvents() {
        // Store filter buttons
        const filterBtns = this.elements.filterGroup.querySelectorAll('.filter-btn');
        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentStore = btn.dataset.store;
                this.filterRecipes();
            });
        });

        // Toggle button for overflow
        const toggleBtn = document.getElementById('filterToggle');
        const overflow = document.getElementById('filterOverflow');
        if (toggleBtn && overflow) {
            toggleBtn.addEventListener('click', () => {
                this.filtersExpanded = !this.filtersExpanded;
                this.elements.filterGroup.classList.toggle('expanded', this.filtersExpanded);
                toggleBtn.classList.toggle('expanded', this.filtersExpanded);
                toggleBtn.querySelector('span:first-child').textContent =
                    this.filtersExpanded ? 'Färre' : 'Fler';
            });
        }
    }

    parseTime(isoTime) {
        if (!isoTime) return Infinity;
        const match = isoTime.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
        if (!match) return Infinity;
        return parseInt(match[1] || 0) * 60 + parseInt(match[2] || 0);
    }

    // IMDB-style weighted rating: WR = (v/(v+m)) * R + (m/(v+m)) * C
    getWeightedRating(recipe) {
        const R = recipe.rating || 0;
        const v = recipe.reviews || 0;
        const m = this.minReviewsForTrust;
        const C = this.globalAvgRating;

        if (!R) return 0;
        return (v / (v + m)) * R + (m / (v + m)) * C;
    }

    sortRecipes() {
        this.filteredRecipes.sort((a, b) => {
            switch (this.currentSort) {
                case 'rating': return this.getWeightedRating(b) - this.getWeightedRating(a);
                case 'time': return this.parseTime(a.time) - this.parseTime(b.time);
                default: return b.match_percentage - a.match_percentage;
            }
        });
    }

    filterRecipes() {
        this.filteredRecipes = this.recipes.filter(recipe => {
            // Search filter (name, category, ingredients)
            const matchesSearch = !this.searchQuery ||
                recipe.name.toLowerCase().includes(this.searchQuery) ||
                (recipe.category && recipe.category.toLowerCase().includes(this.searchQuery)) ||
                recipe.matched_ingredients?.some(ing => ing.ingredient?.toLowerCase().includes(this.searchQuery)) ||
                recipe.unmatched_ingredients?.some(ing => ing.toLowerCase().includes(this.searchQuery));

            // Store filter
            let matchesStore = this.currentStore === 'all';
            if (!matchesStore && recipe.matched_ingredients) {
                matchesStore = recipe.matched_ingredients.some(
                    ing => ing.deal_store === this.currentStore
                );
            }

            // Category filter (handles comma-separated categories)
            const matchesCategory = this.currentCategory === 'all' ||
                (recipe.category && recipe.category.split(',').some(c => c.trim() === this.currentCategory));

            return matchesSearch && matchesStore && matchesCategory;
        });

        this.sortRecipes();
        this.render();
    }

    updateStats() {
        this.elements.recipeCount.textContent = this.recipes.length;
        this.elements.dealCount.textContent = this.deals.length;
    }

    updateLastUpdated() {
        if (this.lastUpdated) {
            const date = new Date(this.lastUpdated);
            const formatted = date.toLocaleDateString('sv-SE', {
                day: 'numeric',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit'
            });
            this.elements.lastUpdated.querySelector('.update-text').textContent =
                `Uppdaterad ${formatted}`;
        }
    }

    formatTime(isoTime) {
        if (!isoTime) return null;
        const match = isoTime.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
        if (!match) return null;
        const hours = parseInt(match[1] || 0);
        const mins = parseInt(match[2] || 0);
        if (hours > 0) return `${hours}h ${mins}m`;
        return `${mins} min`;
    }

    getStoreClass(store) {
        if (store.startsWith('ICA')) return 'ica';
        if (store.includes('Coop')) return 'coop';
        if (store === 'Willys') return 'willys';
        return '';
    }

    getImageUrl(image) {
        if (!image) return null;
        if (typeof image === 'string') return image;
        if (Array.isArray(image) && image.length > 0) return image[0];
        return null;
    }

    renderPriceComparison(ing) {
        if (!ing.deal_price) return '';

        const parts = [];
        const price = this.escapeHtml(ing.deal_price);
        const unit = ing.deal_unit;

        parts.push(`<span class="price-current">${price}</span>`);

        if (unit && (unit === '/kg' || unit === '/st' || unit === '/liter')) {
            parts.push(`<span class="price-unit">${unit}</span>`);
        }

        const multiMatch = unit?.match(/^(\d+)\s+för$/);
        if (multiMatch) {
            const count = parseInt(multiMatch[1]);
            const numPrice = parseFloat(ing.deal_price.replace(':-', '').replace(',', '.'));
            const perItem = (numPrice / count).toFixed(0);
            parts.push(`<span class="price-unit">(${perItem}:-/st)</span>`);
        }

        if (ing.ord_pris) {
            parts.push(`<span class="price-original">${this.escapeHtml(ing.ord_pris)}</span>`);
        }

        return `<span class="tag-price">${parts.join(' ')}</span>`;
    }

    createRecipeCard(recipe) {
        const time = this.formatTime(recipe.time);
        const percentage = recipe.match_percentage || 0;
        const circumference = 2 * Math.PI * 22; // radius 22
        const offset = circumference - (percentage / 100) * circumference;

        const imageUrl = this.getImageUrl(recipe.image);
        const imageHtml = imageUrl
            ? `<img class="card-image" src="${this.escapeHtml(imageUrl)}" alt="${this.escapeHtml(recipe.name)}" loading="lazy">`
            : '';

        const matchedHtml = (recipe.matched_ingredients || []).slice(0, 5).map(ing => {
            const storeClass = this.getStoreClass(ing.deal_store);
            const priceHtml = this.renderPriceComparison(ing);
            return `<span class="ingredient-tag matched ${storeClass}">${this.escapeHtml(ing.ingredient)} ${priceHtml}</span>`;
        }).join('');

        const unmatchedHtml = (recipe.unmatched_ingredients || []).slice(0, 3).map(ing =>
            `<span class="ingredient-tag">${this.escapeHtml(ing)}</span>`
        ).join('');

        const moreCount = (recipe.unmatched_ingredients || []).length - 3;
        const moreHtml = moreCount > 0 ? `<span class="ingredient-tag">+${moreCount}</span>` : '';

        return `
            <article class="recipe-card">
                ${imageHtml}
                <div class="card-header">
                    <span class="card-category">${this.escapeHtml(recipe.category) || 'Recept'}</span>
                    <h2 class="card-title">${this.escapeHtml(recipe.name)}</h2>
                    <div class="card-meta">
                        ${time ? `<span class="meta-item"><span class="meta-icon">⏱</span> ${time}</span>` : ''}
                        ${recipe.servings ? `<span class="meta-item"><span class="meta-icon">👤</span> ${recipe.servings}</span>` : ''}
                    </div>
                </div>

                <div class="match-score">
                    <div class="score-ring">
                        <svg width="56" height="56" viewBox="0 0 56 56">
                            <circle class="score-ring-bg" cx="28" cy="28" r="22"/>
                            <circle class="score-ring-progress" cx="28" cy="28" r="22"
                                    style="stroke-dashoffset: ${offset}"/>
                        </svg>
                        <span class="score-text">${Math.round(percentage)}%</span>
                    </div>
                    <div class="score-details">
                        <div class="score-label">Ingredienser på rea</div>
                        <div class="score-fraction">${recipe.matched_count} av ${recipe.total_ingredients}</div>
                    </div>
                </div>

                <div class="ingredients-section">
                    <div class="ingredients-title">På rea just nu</div>
                    <div class="ingredient-tags">
                        ${matchedHtml || '<span class="ingredient-tag">Inga träffar</span>'}
                    </div>
                    ${unmatchedHtml ? `
                        <div class="ingredients-title" style="margin-top: var(--space-md);">Övriga ingredienser</div>
                        <div class="ingredient-tags">${unmatchedHtml}${moreHtml}</div>
                    ` : ''}
                </div>

                <div class="card-footer">
                    <a href="${this.escapeHtml(recipe.url)}" target="_blank" rel="noopener" class="recipe-link">
                        Se recept
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M5 12h14M12 5l7 7-7 7"/>
                        </svg>
                    </a>
                    ${recipe.rating ? `
                        <div class="rating">
                            <span class="rating-star">★</span>
                            ${recipe.rating}
                            ${recipe.reviews ? `<span>(${recipe.reviews})</span>` : ''}
                        </div>
                    ` : ''}
                </div>
            </article>
        `;
    }

    render() {
        if (this.filteredRecipes.length === 0) {
            this.elements.recipeGrid.innerHTML = `
                <div class="empty-state">
                    <h3>Inga recept hittades</h3>
                    <p>Prova att ändra din sökning eller filter</p>
                </div>
            `;
            return;
        }

        this.elements.recipeGrid.innerHTML = this.filteredRecipes
            .map(recipe => this.createRecipeCard(recipe))
            .join('');

        // Trigger ring animations after render
        requestAnimationFrame(() => {
            document.querySelectorAll('.score-ring-progress').forEach(ring => {
                ring.style.transition = 'stroke-dashoffset 1s cubic-bezier(0.16, 1, 0.3, 1)';
            });
        });
    }

    showError() {
        this.elements.recipeGrid.innerHTML = `
            <div class="empty-state">
                <h3>Kunde inte ladda data</h3>
                <p>Försök ladda om sidan</p>
            </div>
        `;
    }
}

// Theme toggle
function initTheme() {
    const toggle = document.getElementById('themeToggle');
    if (!toggle) return;

    // Check stored preference
    let stored = null;
    try {
        stored = localStorage.getItem('theme');
    } catch (e) {
        // localStorage unavailable (private browsing, etc.)
    }
    if (stored) {
        document.documentElement.setAttribute('data-theme', stored);
    }

    // Update aria-label based on current effective theme
    function updateAriaLabel() {
        const current = document.documentElement.getAttribute('data-theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const isDark = current === 'dark' || (!current && prefersDark);
        toggle.setAttribute('aria-label', isDark ? 'Byt till ljust tema' : 'Byt till mörkt tema');
    }
    updateAriaLabel();

    // Listen for system preference changes
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handleSystemChange = () => {
        let hasExplicit = false;
        try {
            hasExplicit = !!localStorage.getItem('theme');
        } catch (e) {}
        if (!hasExplicit) {
            // No explicit preference, UI follows system automatically via CSS
            updateAriaLabel();
        }
    };
    // Safari <14 fallback
    if (mq.addEventListener) {
        mq.addEventListener('change', handleSystemChange);
    } else {
        mq.addListener(handleSystemChange);
    }

    toggle.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

        let next;
        if (current === 'dark') {
            next = 'light';
        } else if (current === 'light') {
            next = 'dark';
        } else {
            // No explicit setting - flip from system preference
            next = prefersDark ? 'light' : 'dark';
        }

        // Add transition class for smooth theme switch
        document.documentElement.classList.add('theme-transition');
        document.documentElement.setAttribute('data-theme', next);
        try {
            localStorage.setItem('theme', next);
        } catch (e) {
            // localStorage unavailable
        }

        // Update aria-label
        toggle.setAttribute('aria-label', next === 'dark' ? 'Byt till ljust tema' : 'Byt till mörkt tema');

        // Remove transition class after animation completes
        setTimeout(() => {
            document.documentElement.classList.remove('theme-transition');
        }, 400);
    });
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initTheme();

    // Initialize router
    router.init().bindNav();

    // Initialize RecipeApp
    new RecipeApp();
});

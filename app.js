/**
 * Veckans Recept - Recipe & Deals App
 */

class RecipeApp {
    constructor() {
        this.recipes = [];
        this.deals = [];
        this.filteredRecipes = [];
        this.currentStore = this.loadStoredStore();
        this.searchQuery = '';
        this.currentSort = 'match';
        this.currentCategory = 'all';
        this.categories = [];
        this.activeNutritionFilters = new Set();

        // Nutrition filter definitions
        this.nutritionFilters = [
            { id: 'high-protein', label: 'Proteinrikt', field: 'protein', min: 25 },
            { id: 'extra-protein', label: 'Extra protein', field: 'protein', min: 35 },
            { id: 'low-carb', label: 'Låg kolhydrat', field: 'carbs', max: 20 },
            { id: 'low-cal', label: 'Kalorisnålt', field: 'calories', max: 400 },
        ];

        this.elements = {
            recipeGrid: document.getElementById('recipeGrid'),
            searchInput: document.getElementById('searchInput'),
            filterGroup: document.getElementById('filterGroup'),
            lastUpdated: document.getElementById('lastUpdated'),
            recipeCount: document.getElementById('recipeCount'),
            dealCount: document.getElementById('dealCount'),
            sortSelect: document.getElementById('sortSelect'),
            categoryPills: document.getElementById('categoryPills'),
            nutritionPills: document.getElementById('nutritionPills'),
        };

        this.filtersExpanded = false;

        // Validate required elements
        const required = ['recipeGrid', 'searchInput', 'sortSelect', 'categoryPills', 'nutritionPills', 'filterGroup'];
        for (const id of required) {
            if (!this.elements[id]) {
                console.error(`Missing required element: #${id}`);
                return;
            }
        }

        this.init();
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
            this.renderNutritionPills();

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
            const target = /** @type {HTMLInputElement} */ (e.target);
            this.searchQuery = target.value.toLowerCase().trim();
            this.filterRecipes();
        });

        // Sort select
        this.elements.sortSelect.addEventListener('change', (e) => {
            const target = /** @type {HTMLSelectElement} */ (e.target);
            this.currentSort = target.value;
            this.filterRecipes();
        });

        // Category pills (event delegation)
        this.elements.categoryPills.addEventListener('click', (e) => {
            const target = /** @type {HTMLElement} */ (e.target);
            const pill = /** @type {HTMLElement | null} */ (target.closest('.category-pill'));
            if (!pill) return;
            this.elements.categoryPills.querySelectorAll('.category-pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            this.currentCategory = pill.dataset.category;
            this.filterRecipes();
        });

        // Nutrition pills (multi-select)
        this.elements.nutritionPills.addEventListener('click', (e) => {
            const target = /** @type {HTMLElement} */ (e.target);
            const pill = /** @type {HTMLElement | null} */ (target.closest('.nutrition-pill'));
            if (!pill) return;
            const id = pill.dataset.nutrition;
            if (this.activeNutritionFilters.has(id)) {
                this.activeNutritionFilters.delete(id);
                pill.classList.remove('active');
            } else {
                this.activeNutritionFilters.add(id);
                pill.classList.add('active');
            }
            this.filterRecipes();
        });

        // Ingredients accordion (event delegation)
        this.elements.recipeGrid.addEventListener('click', (e) => {
            const target = /** @type {HTMLElement} */ (e.target);
            const accordion = /** @type {HTMLElement | null} */ (target.closest('.ingredients-accordion'));
            if (!accordion) return;

            const isOpen = accordion.classList.toggle('open');
            accordion.setAttribute('aria-expanded', String(isOpen));

            const content = accordion.nextElementSibling;
            if (content && content.classList.contains('ingredients-accordion-content')) {
                content.classList.toggle('open', isOpen);
            }
        });
    }

    renderCategoryPills() {
        const container = this.elements.categoryPills;
        const allPill = `<button class="category-pill active" data-category="all">Alla</button>`;
        const pills = this.categories.map(cat =>
            `<button class="category-pill" data-category="${Utils.escapeHtml(cat)}">${Utils.escapeHtml(cat)}</button>`
        ).join('');
        container.innerHTML = allPill + pills;
    }

    renderNutritionPills() {
        const container = this.elements.nutritionPills;
        const pills = this.nutritionFilters.map(filter => {
            const thresholdText = filter.min ? `≥${filter.min}g` : `≤${filter.max}${filter.field === 'calories' ? ' kcal' : 'g'}`;
            return `<button class="nutrition-pill" data-nutrition="${filter.id}" title="${thresholdText}">${filter.label}</button>`;
        }).join('');
        container.innerHTML = pills;
    }

    parseNutritionValue(str) {
        if (!str) return null;
        const match = str.match(/[\d.]+/);
        return match ? parseFloat(match[0]) : null;
    }

    checkNutritionFilter(recipe, filter) {
        if (!recipe.nutrition) return false;
        const value = this.parseNutritionValue(recipe.nutrition[filter.field]);
        if (value === null) return false;
        if (filter.min !== undefined && value < filter.min) return false;
        if (filter.max !== undefined && value > filter.max) return false;
        return true;
    }

    renderStoreFilters() {
        // Count deals per store
        const storeCounts = {};
        this.deals.forEach(deal => {
            const store = deal.store;
            storeCounts[store] = (storeCounts[store] || 0) + 1;
        });

        // Categorize stores: national chains vs specific stores
        const nationalStores = ['ICA Supermarket', 'ICA Nära', 'ICA Maxi', 'ICA Kvantum', 'Stora Coop', 'Coop', 'Willys'];
        const specificStores = ['ICA Globen', 'Stora Coop Västberga', 'Coop Fruängen'];

        // Filter to only stores that have deals
        const availableNational = nationalStores.filter(s => storeCounts[s]);
        const availableSpecific = specificStores.filter(s => storeCounts[s]);

        const container = this.elements.filterGroup;

        let html = `
            <div class="store-select-wrapper">
                <select id="storeSelect" class="store-select">
                    <option value="all">Alla butiker</option>
        `;

        if (availableNational.length > 0) {
            html += `<optgroup label="Kedjor">`;
            availableNational.forEach(store => {
                const count = storeCounts[store];
                html += `<option value="${Utils.escapeHtml(store)}">${Utils.escapeHtml(store)} (${count})</option>`;
            });
            html += `</optgroup>`;
        }

        if (availableSpecific.length > 0) {
            html += `<optgroup label="Mina butiker">`;
            availableSpecific.forEach(store => {
                const count = storeCounts[store];
                html += `<option value="${Utils.escapeHtml(store)}">${Utils.escapeHtml(store)} (${count})</option>`;
            });
            html += `</optgroup>`;
        }

        html += `
                </select>
                <svg class="store-select-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M6 9l6 6 6-6"/>
                </svg>
            </div>
        `;

        container.innerHTML = html;

        // Validate stored store exists, sync dropdown, apply filter
        const availableStores = [...availableNational, ...availableSpecific];
        if (this.currentStore !== 'all' && !availableStores.includes(this.currentStore)) {
            this.currentStore = 'all';
        }
        const storeSelect = /** @type {HTMLSelectElement|null} */ (document.getElementById('storeSelect'));
        if (storeSelect) {
            storeSelect.value = this.currentStore;
        }
        this.filterRecipes();
        this.bindFilterEvents();
    }

    loadStoredStore() {
        try {
            return localStorage.getItem('selectedStore') || 'all';
        } catch {
            return 'all';
        }
    }

    saveStoredStore(store) {
        try {
            localStorage.setItem('selectedStore', store);
        } catch { /* ignore */ }
    }

    bindFilterEvents() {
        const storeSelect = /** @type {HTMLSelectElement|null} */ (document.getElementById('storeSelect'));
        if (storeSelect) {
            storeSelect.addEventListener('change', () => {
                this.currentStore = storeSelect.value;
                this.saveStoredStore(this.currentStore);
                this.filterRecipes();
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

            // Nutrition filter (all active filters must match)
            let matchesNutrition = true;
            if (this.activeNutritionFilters.size > 0) {
                for (const id of this.activeNutritionFilters) {
                    const filter = this.nutritionFilters.find(f => f.id === id);
                    if (filter && !this.checkNutritionFilter(recipe, filter)) {
                        matchesNutrition = false;
                        break;
                    }
                }
            }

            return matchesSearch && matchesStore && matchesCategory && matchesNutrition;
        });

        this.sortRecipes();
        this.render();
    }

    updateStats() {
        this.elements.recipeCount.textContent = String(this.filteredRecipes.length);
        this.elements.dealCount.textContent = String(this.deals.length);
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

    getImageUrl(image) {
        if (!image) return null;
        if (typeof image === 'string') return image;
        if (Array.isArray(image) && image.length > 0) return image[0];
        return null;
    }

    renderPriceComparison(ing) {
        if (!ing.deal_price) return '';

        const parts = [];
        const price = Utils.escapeHtml(ing.deal_price);
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
            parts.push(`<span class="price-original">${Utils.escapeHtml(ing.ord_pris)}</span>`);
        }

        return `<span class="tag-price">${parts.join(' ')}</span>`;
    }

    renderNutrition(recipe) {
        if (!recipe.nutrition) return '';

        const items = [];
        if (recipe.nutrition.calories) {
            const cal = recipe.nutrition.calories.replace(/ ?(calories|kcal)/gi, '');
            items.push({ label: 'Kalorier', value: cal, unit: 'kcal' });
        }
        if (recipe.nutrition.protein) {
            items.push({ label: 'Protein', value: recipe.nutrition.protein.replace(' g', ''), unit: 'g' });
        }
        if (recipe.nutrition.fat) {
            items.push({ label: 'Fett', value: recipe.nutrition.fat.replace(' g', ''), unit: 'g' });
        }
        if (recipe.nutrition.carbs) {
            items.push({ label: 'Kolhydrater', value: recipe.nutrition.carbs.replace(' g', ''), unit: 'g' });
        }

        if (items.length === 0) return '';

        const itemsHtml = items.map(item => `
            <div class="nutrition-item">
                <span class="nutrition-label">${item.label}</span>
                <span class="nutrition-value">${item.value} ${item.unit}</span>
            </div>
        `).join('');

        return `
            <div class="nutrition-section">
                <div class="nutrition-title">Näringsvärde per portion</div>
                <div class="nutrition-grid">${itemsHtml}</div>
            </div>
        `;
    }

    renderIngredientRows(matchedIngredients) {
        if (!matchedIngredients || matchedIngredients.length === 0) {
            return '<div class="ingredient-row"><span class="ingredient-name">Inga träffar</span></div>';
        }

        return matchedIngredients.map(ing => {
            const storeClass = Utils.getStoreClass(ing.deal_store);
            const storeName = this.getShortStoreName(ing.deal_store);
            const priceDisplay = ing.deal_price || '';
            const originalPrice = ing.ord_pris || '';
            // Strip "sats " prefix from ICA ingredient kit names
            const ingredientName = (ing.ingredient || '').replace(/^sats\s+/i, '');

            return `
                <div class="ingredient-row">
                    <span class="ingredient-name">${Utils.escapeHtml(ingredientName)}</span>
                    <div class="ingredient-deal">
                        <span class="store-badge ${storeClass}">${Utils.escapeHtml(storeName)}</span>
                        <span class="deal-price">${Utils.escapeHtml(priceDisplay)}</span>
                        ${originalPrice ? `<span class="price-original">${Utils.escapeHtml(originalPrice)}</span>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }

    getShortStoreName(store) {
        if (!store) return '';
        // Shorten long store names for badge display
        if (store.startsWith('ICA ')) return 'ICA';
        if (store.startsWith('Stora Coop')) return 'Coop';
        if (store.startsWith('Coop ')) return 'Coop';
        return store;
    }

    createRecipeCard(recipe) {
        const time = this.formatTime(recipe.time);
        const percentage = recipe.match_percentage || 0;
        const circumference = 2 * Math.PI * 22; // radius 22
        const offset = circumference - (percentage / 100) * circumference;

        const imageUrl = this.getImageUrl(recipe.image);
        const imageHtml = imageUrl
            ? `<img class="card-image" src="${Utils.escapeHtml(imageUrl)}" alt="${Utils.escapeHtml(recipe.name)}" loading="lazy">`
            : '';

        const matchedCount = recipe.matched_count || 0;
        const ingredientRowsHtml = this.renderIngredientRows(recipe.matched_ingredients);

        return `
            <article class="recipe-card">
                ${imageHtml}
                <div class="card-header">
                    <span class="card-category">${Utils.escapeHtml(recipe.category) || 'Recept'}</span>
                    <h2 class="card-title">${Utils.escapeHtml(recipe.name)}</h2>
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
                    <button class="ingredients-accordion" aria-expanded="false">
                        <span>${matchedCount} ingrediens${matchedCount !== 1 ? 'er' : ''} på rea</span>
                        <svg class="accordion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M6 9l6 6 6-6"/>
                        </svg>
                    </button>
                    <div class="ingredients-accordion-content">
                        ${ingredientRowsHtml}
                    </div>
                </div>

                ${this.renderNutrition(recipe)}

                <div class="card-footer">
                    <a href="${Utils.escapeHtml(recipe.url)}" target="_blank" rel="noopener" class="recipe-link">
                        Se recept
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M5 12h14M12 5l7 7-7 7"/>
                        </svg>
                    </a>
                    ${recipe.rating ? `
                        <div class="rating">
                            <span class="rating-star">★</span>
                            ${Number(recipe.rating).toFixed(1)}
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
            /** @type {NodeListOf<SVGElement>} */
            const rings = document.querySelectorAll('.score-ring-progress');
            rings.forEach(ring => {
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
    } catch {
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
        } catch { /* ignore */ }
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
        } catch {
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

    // Track previous route for onLeave callbacks
    let previousRoute = null;

    // Set up route handlers
    router.on('/recipes', () => {
        // RecipeApp is always initialized, no action needed
    });

    router.on('/deals', () => {
        dealsApp.init();
    });

    router.on('/lists', () => {
        listsApp.init();
    });

    // Handle route leave callbacks
    const originalOnRouteChange = router.onRouteChange;
    router.onRouteChange = (newRoute) => {
        // Call onLeave for previous route
        if (previousRoute === '/deals') {
            dealsApp.onLeave();
        }
        if (previousRoute === '/lists') {
            listsApp.onLeave();
        }

        previousRoute = newRoute;

        // Call original handler (updates nav active states)
        if (originalOnRouteChange) {
            originalOnRouteChange(newRoute);
        }
    };

    // Initialize router
    router.init().bindNav();

    // Initialize RecipeApp
    new RecipeApp();
});

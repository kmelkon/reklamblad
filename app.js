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

        this.elements = {
            recipeGrid: document.getElementById('recipeGrid'),
            searchInput: document.getElementById('searchInput'),
            filterBtns: document.querySelectorAll('.filter-btn'),
            lastUpdated: document.getElementById('lastUpdated'),
            recipeCount: document.getElementById('recipeCount'),
            dealCount: document.getElementById('dealCount'),
        };

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

            const matchesData = await matchesRes.json();
            const dealsData = await dealsRes.json();

            this.recipes = matchesData.recipes || [];
            this.deals = dealsData || [];
            this.lastUpdated = matchesData.last_updated;
            this.filteredRecipes = [...this.recipes];

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

        // Store filters
        this.elements.filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                this.elements.filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentStore = btn.dataset.store;
                this.filterRecipes();
            });
        });
    }

    filterRecipes() {
        this.filteredRecipes = this.recipes.filter(recipe => {
            // Search filter
            const matchesSearch = !this.searchQuery ||
                recipe.name.toLowerCase().includes(this.searchQuery) ||
                (recipe.category && recipe.category.toLowerCase().includes(this.searchQuery));

            // Store filter
            let matchesStore = this.currentStore === 'all';
            if (!matchesStore && recipe.matched_ingredients) {
                matchesStore = recipe.matched_ingredients.some(
                    ing => ing.deal_store === this.currentStore
                );
            }

            return matchesSearch && matchesStore;
        });

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
        if (store === 'ICA Supermarket') return 'ica';
        if (store === 'Stora Coop') return 'coop';
        return '';
    }

    getImageUrl(image) {
        if (!image) return null;
        if (typeof image === 'string') return image;
        if (Array.isArray(image) && image.length > 0) return image[0];
        return null;
    }

    createRecipeCard(recipe) {
        const time = this.formatTime(recipe.time);
        const percentage = recipe.match_percentage || 0;
        const circumference = 2 * Math.PI * 22; // radius 22
        const offset = circumference - (percentage / 100) * circumference;

        const imageUrl = this.getImageUrl(recipe.image);
        const imageHtml = imageUrl
            ? `<img class="card-image" src="${imageUrl}" alt="${recipe.name}" loading="lazy">`
            : '';

        const matchedHtml = (recipe.matched_ingredients || []).slice(0, 5).map(ing => {
            const storeClass = this.getStoreClass(ing.deal_store);
            const price = ing.deal_price ? `<span class="tag-price">${ing.deal_price}</span>` : '';
            return `<span class="ingredient-tag matched ${storeClass}">${ing.ingredient} ${price}</span>`;
        }).join('');

        const unmatchedHtml = (recipe.unmatched_ingredients || []).slice(0, 3).map(ing =>
            `<span class="ingredient-tag">${ing}</span>`
        ).join('');

        const moreCount = (recipe.unmatched_ingredients || []).length - 3;
        const moreHtml = moreCount > 0 ? `<span class="ingredient-tag">+${moreCount}</span>` : '';

        return `
            <article class="recipe-card">
                ${imageHtml}
                <div class="card-header">
                    <span class="card-category">${recipe.category || 'Recept'}</span>
                    <h2 class="card-title">${recipe.name}</h2>
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
                    <a href="${recipe.url}" target="_blank" rel="noopener" class="recipe-link">
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

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    new RecipeApp();
});

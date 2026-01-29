/**
 * Simple hash-based router for vanilla JS
 */
class Router {
    constructor() {
        this.routes = {};
        this.currentRoute = null;
        this.previousRoute = null;
        this.onRouteChange = null;
        this.scrollPositions = {};

        window.addEventListener('hashchange', () => this.handleRoute());
    }

    /**
     * Register a route handler
     * @param {string} path - Route path (e.g., '/deals')
     * @param {Function} handler - Callback when route is active
     */
    on(path, handler) {
        this.routes[path] = handler;
        return this;
    }

    /**
     * Navigate to a route
     * @param {string} path - Route path
     */
    navigate(path) {
        window.location.hash = path;
    }

    /**
     * Get current route path from hash
     * @returns {string}
     */
    getPath() {
        const hash = window.location.hash.slice(1) || '/';
        return hash.startsWith('/') ? hash : '/' + hash;
    }

    /**
     * Handle route change
     */
    handleRoute() {
        const path = this.getPath();

        // Normalize: treat '/' and '/recipes' as same route
        const normalizedPath = path === '/' ? '/recipes' : path;

        if (normalizedPath === this.currentRoute) return;

        // Save scroll position of previous route
        if (this.currentRoute) {
            this.scrollPositions[this.currentRoute] = window.scrollY;
        }

        this.previousRoute = this.currentRoute;
        this.currentRoute = normalizedPath;

        // Switch visible page
        this.switchPage(normalizedPath);

        // Call route handler if registered
        const handler = this.routes[normalizedPath] || this.routes['/recipes'];
        if (handler) {
            handler(normalizedPath);
        }

        // Call global change listener
        if (this.onRouteChange) {
            this.onRouteChange(normalizedPath);
        }

        // Restore scroll position (after a tick to let page render)
        requestAnimationFrame(() => {
            const savedScroll = this.scrollPositions[normalizedPath] || 0;
            window.scrollTo(0, savedScroll);
        });
    }

    /**
     * Switch visible page container
     * @param {string} path - Route path
     */
    switchPage(path) {
        document.querySelectorAll('.page').forEach(page => {
            const pagePath = page.dataset.page;
            const isActive = pagePath === path || (pagePath === '/recipes' && path === '/');
            page.style.display = isActive ? '' : 'none';
        });
    }

    /**
     * Initialize router and handle initial route
     */
    init() {
        this.handleRoute();
        return this;
    }

    /**
     * Bind navigation elements to update active states
     */
    bindNav() {
        const updateActiveNav = (path) => {
            // Update desktop tabs
            document.querySelectorAll('.nav-tab').forEach(tab => {
                const route = tab.dataset.route;
                const isActive = route === path || (route === '/recipes' && path === '/');
                tab.classList.toggle('active', isActive);
            });

            // Update mobile nav
            document.querySelectorAll('.mobile-nav-item').forEach(item => {
                const route = item.dataset.route;
                const isActive = route === path || (route === '/recipes' && path === '/');
                item.classList.toggle('active', isActive);
            });
        };

        // Update on route change
        this.onRouteChange = updateActiveNav;

        // Set initial state
        updateActiveNav(this.currentRoute || '/recipes');

        return this;
    }
}

// Export singleton instance
const router = new Router();

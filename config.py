"""Shared configuration and constants for the scrapers.

This module centralizes configuration values used across scraper scripts
to avoid magic numbers and enable easy tuning.
"""

# Browser Configuration
BROWSER_CONFIG = {
    'headless': True,
    'viewport': {'width': 1280, 'height': 900},
    'locale': 'sv-SE',
    'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

# Timeout Configuration (milliseconds)
TIMEOUTS = {
    'navigation': 30000,  # Page load
    'network_idle': 20000,  # Network idle state
    'api_request': 10000,  # Individual API requests
    'wait': 2000,  # General waits
    'scroll_step': 500,  # Wait between scrolls
}

# Scraping Configuration
SCRAPING = {
    'max_scroll_iterations': 25,
    'scroll_step_px': 500,
    'inventory_scroll_iterations': 25,
    'inventory_scroll_step': 150,
}

# Image Optimization
CLOUDINARY_TRANSFORMS = 'w_400,f_auto,q_auto'  # Width 400, auto format, auto quality

# Store Configuration
STORES = [
    # National chains
    {
        'name': 'ICA Supermarket',
        'url': 'https://ereklamblad.se/ICA-Supermarket/',
        'method': 'ereklamblad',
        'enabled': True,
    },
    {
        'name': 'ICA Nära',
        'url': 'https://ereklamblad.se/ICA-Nara/',
        'method': 'ereklamblad',
        'enabled': True,
    },
    {
        'name': 'ICA Maxi',
        'url': 'https://ereklamblad.se/ICA-Maxi-Stormarknad/',
        'method': 'inventory',
        'enabled': True,
    },
    {
        'name': 'ICA Kvantum',
        'url': 'https://ereklamblad.se/ICA-Kvantum/',
        'method': 'inventory',
        'enabled': True,
    },
    {
        'name': 'Stora Coop',
        'url': 'https://ereklamblad.se/Stora-Coop/',
        'method': 'inventory',
        'enabled': True,
    },
    {
        'name': 'Coop',
        'url': 'https://ereklamblad.se/Coop/',
        'method': 'inventory',
        'enabled': True,
    },
    {
        'name': 'Willys',
        'url': 'https://ereklamblad.se/Willys/',
        'method': 'inventory',
        'enabled': True,
    },
    # Specific stores
    {
        'name': 'ICA Globen',
        'url': 'https://ereklamblad.se/ICA-Supermarket/butiker/d4d20iz',
        'method': 'store_specific',
        'enabled': True,
    },
    {
        'name': 'Stora Coop Västberga',
        'url': 'https://www.coop.se/butiker-erbjudanden/stora-coop/stora-coop-vastberga/',
        'method': 'coop_api',
        'enabled': True,
    },
    {
        'name': 'Coop Fruängen',
        'url': 'https://www.coop.se/butiker-erbjudanden/coop/coop-fruangen/',
        'method': 'coop_api',
        'enabled': True,
    },
]

# Data Validation Thresholds
VALIDATION = {
    'min_products_per_store': 10,  # Minimum expected products per store
    'max_products_total': 10000,   # Maximum reasonable total products
    'min_total_products': 50,      # Minimum total products to consider scraping successful
    'max_name_length': 200,        # Maximum product name length
    'min_name_length': 2,          # Minimum product name length
    'max_file_size_mb': 20,        # Maximum output file size in MB
}

# Matching Configuration
MATCHING = {
    'default_threshold': 0.6,  # Minimum match score to consider a match
    'exact_match_score': 1.0,
    'substring_match_score': 0.9,
    'synonym_match_score': 0.85,
    'word_overlap_score': 0.75,
    'fuzzy_match_score': 0.7,
    'min_word_length': 4,  # Minimum length for substring matching
}

# Output Files
OUTPUT_FILES = {
    'deals': 'deals.json',
    'recipes': 'recipes.json',
    'recipe_matches': 'recipe_matches.json',
    'recipe_matches_optimized': 'recipe_matches_optimized.json',
}

# Logging Configuration
LOGGING = {
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'date_format': '%Y-%m-%d %H:%M:%S',
}

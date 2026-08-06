# Configuration Guide

## Project Configuration

### Python Scrapers

#### Environment Variables (Optional)

```bash
# Browser configuration
HEADLESS=true  # Run browser in headless mode (default: true)
VIEWPORT_WIDTH=1280  # Browser viewport width (default: 1280)
VIEWPORT_HEIGHT=900  # Browser viewport height (default: 900)

# Timeout configuration
TIMEOUT_NAVIGATION=30000  # Page navigation timeout in ms (default: 30000)
TIMEOUT_NETWORK=20000     # Network idle timeout in ms (default: 20000)

# Scraper configuration
MAX_SCROLL_ITERATIONS=25  # Max scroll attempts (default: 25)
SCROLL_STEP_PX=500        # Pixels to scroll per step (default: 500)
```

#### Configuration File

Create `scraper_config.json` (optional):

```json
{
  "stores": [
    {
      "name": "ICA Supermarket",
      "url": "https://ereklamblad.se/ICA-Supermarket/",
      "method": "ereklamblad",
      "enabled": true
    },
    {
      "name": "Custom Store",
      "url": "https://example.com/store",
      "method": "inventory",
      "enabled": false
    }
  ],
  "timeouts": {
    "navigation": 30000,
    "network": 20000
  }
}
```

### Frontend Configuration

#### Local Storage Keys

The frontend uses localStorage for user preferences:

- `selectedStore`: User's preferred store filter
- `theme`: Light/dark theme preference ('light' or 'dark')

#### Data Files

- `deals.json` - Current deals (~200KB, updated weekly)
- `recipes.json` - Recipe database (~1.7MB, static)
- `recipe_matches.json` - Matched results (~6.5MB, updated weekly)

For production optimization, use `recipe_matches_optimized.json` (~3.1MB).

## Development Setup

### Prerequisites

```bash
# Python 3.12+
python --version

# Node.js 20+ (for linting)
node --version

# Git
git --version
```

### Initial Setup

```bash
# Clone repository
git clone https://github.com/kmelkon/reklamblad.git
cd reklamblad

# Install Python dependencies
pip install playwright requests
playwright install chromium

# Install Node dependencies (for linting)
npm install

# Run linters
npm run lint

# Run tests
python test_match_recipes.py
```

### Running Scrapers

```bash
# Scrape current deals
python scrape_deals.py

# Match recipes to deals
python match_recipes.py

# Validate output
python validate_data.py

# Optimize file size (optional)
python optimize_data.py
```

### Serving Locally

```bash
# Simple HTTP server
python -m http.server 8000

# Visit http://localhost:8000
```

## CI/CD Configuration

### GitHub Actions

**Scrape Workflow** (`.github/workflows/scrape.yml`)
- Runs: Every Monday at 6 AM UTC
- Steps: Install deps → Run tests → Scrape → Match → Validate → Commit

**Lint Workflow** (`.github/workflows/lint.yml`)
- Runs: On push/PR to main
- Steps: ESLint, Stylelint, TypeScript check

### Manual Trigger

Go to Actions → Scrape Deals → Run workflow

## Customization

### Adding New Stores

Edit `scrape_deals.py`:

```python
stores = [
    # ... existing stores
    ('New Store', 'https://example.com/store'),
]
```

### Adding Synonyms

Edit `match_recipes.py`:

```python
SYNONYMS = {
    'kyckling': ['kycklingfile', 'kycklingbrost', ...],
    'new_item': ['variant1', 'variant2'],
}
```

### Adjusting Match Threshold

Edit `match_recipes.py`:

```python
# In find_matching_deals()
matches = find_matching_deals(ing, deals, threshold=0.6)  # Adjust 0.6
```

Lower threshold = more matches (but less accurate)
Higher threshold = fewer matches (but more accurate)

## Performance Tuning

### Reduce Data Size

Use the optimization script:

```bash
python optimize_data.py
```

This reduces `recipe_matches.json` by ~52.5%.

### Frontend Performance

- Enable browser caching (cache data files for 1 hour)
- Use CDN for static assets
- Consider lazy loading for recipe images

### Scraper Performance

- Reduce `MAX_SCROLL_ITERATIONS` if pages load faster
- Increase timeouts if experiencing failures
- Run scrapers in parallel (advanced)

## Troubleshooting

### Scraper Fails

1. Check internet connection
2. Verify target websites haven't changed
3. Increase timeouts
4. Check Playwright installation: `playwright install chromium`

### No Products Found

1. Website structure may have changed
2. Check browser console in non-headless mode
3. Verify API endpoints are accessible
4. Check for rate limiting

### Validation Errors

1. Run `python validate_data.py` to see specific errors
2. Check JSON syntax
3. Verify data types match schema
4. Look for null/missing required fields

### Frontend Issues

1. Check browser console for errors
2. Verify JSON files are valid
3. Clear browser cache
4. Check network tab for failed requests

## Monitoring

### Data Quality Checks

```bash
# Validate data
python validate_data.py

# Check file sizes
ls -lh deals.json recipes.json recipe_matches.json

# Count products
python -c "import json; print(len(json.load(open('deals.json'))))"

# Count recipes
python -c "import json; print(len(json.load(open('recipes.json'))))"
```

### GitHub Actions Status

- Monitor workflow runs in Actions tab
- Check for failed scrapes
- Review commit history for data updates

## Security

### Rate Limiting

The scraper respects rate limits:
- Waits for network idle before proceeding
- Uses reasonable timeouts
- Scrolls gradually to simulate human behavior

### Data Privacy

- No user data is collected
- No cookies are stored
- All data is publicly available grocery deals

### API Keys

This project doesn't require API keys. All data is scraped from public websites.

## Support

For issues or questions:
1. Check existing GitHub Issues
2. Create a new issue with details
3. Include error messages and logs
4. Specify your environment (OS, Python version, etc.)

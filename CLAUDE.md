# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Swedish grocery deals + recipe matcher. Scrapes weekly deals from ICA, Coop, and Willys, then matches them against ~100 ICA recipes to find recipes with ingredients currently on sale. Static site served via GitHub Pages.

## Commands

```bash
# Serve frontend locally
python -m http.server 8000

# Run scrapers (requires playwright)
pip install playwright requests
playwright install chromium
python scrape_deals.py      # Scrape current deals
python match_recipes.py     # Match deals to recipes

# One-time recipe database update
python scrape_recipes.py    # Re-scrape ICA recipes
```

## Architecture

**Data Pipeline** (runs weekly via GitHub Actions):
1. `scrape_deals.py` → `deals.json` - Scrapes ereklamblad.se using Playwright API interception + DOM fallback
2. `match_recipes.py` → `recipe_matches.json` - Fuzzy matches deals to recipe ingredients using synonyms + SequenceMatcher

**Frontend** (vanilla JS, no build step):
- `index.html` / `styles.css` / `app.js` - Single-page app with RecipeApp class
- Features: search, store filter, category pills, sort (match/rating/time), dark mode toggle
- Fetches `recipe_matches.json` + `deals.json` on load

**Ingredient Matching** (`match_recipes.py`):
- `SYNONYMS` dict maps base ingredients to variants (e.g., 'kyckling' → ['kycklingfile', 'kycklingbrost'])
- `IGNORE_WORDS` excludes pantry staples (salt, peppar, olja)
- `FALSE_MATCHES` prevents bad substring matches
- Score thresholds: 1.0 exact, 0.9 substring, 0.85 synonym, 0.75 word overlap, 0.7 fuzzy

**Deal Scraping** (`scrape_deals.py`):
- Two strategies: API interception (Incito JSON, paged-publications) and inventory view (?publication=inventory)
- Stores using inventory view: Willys, ICA Maxi, ICA Kvantum, Stora Coop, Coop
- Falls back to DOM parsing if API capture fails

## Key Files

| File | Description |
|------|-------------|
| `deals.json` | Current deals (updated weekly by CI) |
| `recipes.json` | Recipe database (~100 recipes, static) |
| `recipe_matches.json` | Matched results with metadata |
| `.github/workflows/scrape.yml` | Weekly scrape workflow (Mon 6AM UTC) |

# Veckans Recept

Swedish grocery deals + recipe matcher. Finds recipes with ingredients currently on sale at ICA and Coop.

## How it works

1. **Weekly scrape** - GitHub Actions runs every Monday 6 AM UTC
2. **Deal extraction** - Scrapes ICA Supermarket + Stora Coop from ereklamblad.se
3. **Recipe matching** - Matches ~100 ICA recipes against current deals
4. **Static site** - Frontend served via GitHub Pages

## Local development

```bash
# Serve frontend
python -m http.server 8000
# Open http://localhost:8000

# Run scraper (requires playwright)
pip install playwright requests
playwright install chromium
python scrape_deals.py
python match_recipes.py
```

## Files

| File | Description |
|------|-------------|
| `scrape_deals.py` | Scrapes deals from ereklamblad.se |
| `scrape_recipes.py` | One-time ICA recipe scraper |
| `match_recipes.py` | Matches deals to recipe ingredients |
| `deals.json` | Current deals (updated weekly) |
| `recipes.json` | Recipe database (~100 recipes) |
| `recipe_matches.json` | Matched results (updated weekly) |
| `index.html` | Frontend |

## Manual trigger

Go to Actions > Scrape Deals > Run workflow

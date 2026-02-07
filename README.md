# Veckans Recept

Swedish grocery deals + recipe matcher. Finds recipes with ingredients currently on sale at ICA, Coop, and Willys.

[![Scrape Deals](https://github.com/kmelkon/reklamblad/actions/workflows/scrape.yml/badge.svg)](https://github.com/kmelkon/reklamblad/actions/workflows/scrape.yml)
[![Lint](https://github.com/kmelkon/reklamblad/actions/workflows/lint.yml/badge.svg)](https://github.com/kmelkon/reklamblad/actions/workflows/lint.yml)

## ✨ Features

- 🛒 **Weekly Deals** - Automatically scrapes deals from major Swedish grocery stores
- 🥘 **Recipe Matching** - Finds recipes where ingredients are on sale
- 📊 **Match Percentage** - Shows what % of ingredients are on sale
- 🏪 **Store Filtering** - Filter by your favorite store
- 🌙 **Dark Mode** - Automatic theme switching
- 📱 **Mobile Friendly** - Responsive design
- 🔍 **Search** - Search recipes, ingredients, and deals
- 📝 **Shopping Lists** - Create and manage shopping lists

## 🚀 Quick Start

### View Live Site

Visit [https://kmelkon.github.io/reklamblad/](https://kmelkon.github.io/reklamblad/)

### Local Development

```bash
# Serve frontend
python -m http.server 8000
# Open http://localhost:8000

# Run scraper (requires playwright)
pip install playwright requests
playwright install chromium
python scrape_deals.py
python match_recipes.py

# Run tests
python test_match_recipes.py

# Validate data
python validate_data.py
```

## 📁 Project Structure

| File | Description |
|------|-------------|
| **Frontend** | |
| `index.html` | Main application page |
| `app.js` | Recipe browser (main page) |
| `deals.js` | Deal browser page |
| `lists.js` | Shopping list manager |
| `router.js` | Client-side routing |
| `utils.js` | Shared utilities |
| `styles.css` | All styling |
| **Python Scrapers** | |
| `scrape_deals.py` | Scrapes weekly deals from stores |
| `match_recipes.py` | Matches deals to recipe ingredients |
| `scrape_recipes.py` | One-time recipe database builder |
| `validate_data.py` | Data validation utility |
| `optimize_data.py` | JSON optimization (52% reduction) |
| `test_match_recipes.py` | Unit tests for matching logic |
| **Data** | |
| `deals.json` | Current deals (~200 KB, updated weekly) |
| `recipes.json` | Recipe database (~1.7 MB, static) |
| `recipe_matches.json` | Matched results (~6.5 MB, updated weekly) |
| **Configuration** | |
| `.github/workflows/` | CI/CD workflows |
| `package.json` | Node.js dependencies (linting) |
| `eslint.config.js` | ESLint configuration |
| `tsconfig.json` | TypeScript type checking |

## 🏗️ How it works

1. **Weekly Scrape** - GitHub Actions runs every Monday 6 AM UTC
2. **Deal Extraction** - Scrapes ICA, Coop, Willys from ereklamblad.se and coop.se
3. **Recipe Matching** - Matches ~250 recipes against current deals using fuzzy matching
4. **Static Site** - Frontend served via GitHub Pages

### Matching Algorithm

Ingredients are matched to deals using multiple strategies:

- **Exact Match** (score 1.0): Identical after normalization
- **Substring Match** (score 0.9): One contains the other
- **Synonym Match** (score 0.85): Known ingredient variants
- **Word Overlap** (score 0.75): Significant words in common
- **Fuzzy Match** (score 0.7): Similar spelling

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed documentation.

## 🧪 Testing

```bash
# Run unit tests
python test_match_recipes.py

# Validate data files
python validate_data.py

# Run linters
npm run lint

# Type check JavaScript
npm run typecheck
```

## 📊 Performance

- **Initial Load**: ~2-3s (6.5 MB JSON)
- **Optimized Load**: ~1-1.5s (3.1 MB JSON with optimization)
- **Search Latency**: <50ms
- **Scroll Performance**: 60 FPS with virtual scrolling

## 🔧 Configuration

See [CONFIGURATION.md](CONFIGURATION.md) for detailed configuration options including:

- Environment variables
- Scraper settings
- Timeout configuration
- Store customization
- Match threshold tuning

## 📖 Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and data flow
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration guide
- [CLAUDE.md](CLAUDE.md) - AI assistant context

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python test_match_recipes.py`
5. Run linters: `npm run lint`
6. Submit a pull request

### Development Guidelines

- Write tests for new features
- Update documentation
- Follow existing code style
- Validate data with `validate_data.py`

## 🐛 Troubleshooting

### Scraper Issues

```bash
# Check if Playwright is installed
playwright install chromium

# Run with more verbose output
python scrape_deals.py

# Validate output
python validate_data.py
```

### Frontend Issues

- Clear browser cache
- Check console for errors
- Verify JSON files are valid
- Try in incognito mode

## 📋 Manual Workflow Trigger

Go to [Actions](https://github.com/kmelkon/reklamblad/actions) → Scrape Deals → Run workflow

## 📜 License

MIT License - Feel free to use and modify

## 🙏 Acknowledgments

- Recipe data from [ICA](https://www.ica.se/recept/)
- Deal data from [eReklamblad](https://ereklamblad.se/)
- Built with [Playwright](https://playwright.dev/)

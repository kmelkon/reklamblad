# Architecture Documentation

## System Overview

**Veckans Recept** is a static web application that helps Swedish users find recipes using ingredients currently on sale at local grocery stores.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Actions (CI/CD)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Weekly Scrape│  │   Lint Check │  │  Deploy Site │      │
│  └──────┬───────┘  └──────────────┘  └──────────────┘      │
└─────────┼───────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Python Scrapers                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │scrape_deals  │→ │match_recipes │→ │validate_data │      │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘      │
└─────────┼──────────────────┼───────────────────────────────┘
          │                  │
          ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                     Data Layer (JSON)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  deals.json  │  │ recipes.json │  │recipe_matches│      │
│  │   (~200 KB)  │  │  (~1.7 MB)   │  │  (~6.5 MB)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              Frontend (Vanilla JS + HTML/CSS)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   app.js     │  │  deals.js    │  │  lists.js    │      │
│  │  (Recipes)   │  │  (Browse)    │  │ (Shopping)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │  router.js   │  │  utils.js    │                        │
│  │  (Routing)   │  │ (Utilities)  │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                  GitHub Pages (Static Host)                  │
│              https://kmelkon.github.io/reklamblad/           │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Data Pipeline

#### 1.1 scrape_deals.py

**Purpose**: Scrape current weekly deals from Swedish grocery stores

**Strategy**:
1. **API Interception** (Primary)
   - Uses Playwright to intercept network requests
   - Captures JSON responses from store APIs
   - Most reliable method

2. **Inventory View** (ICA, Coop, Willys)
   - Navigates to `?publication=inventory` endpoint
   - Parses structured product listings
   - Best for price comparison data

3. **DOM Parsing** (Fallback)
   - Extracts visible text from page
   - Used when API interception fails
   - Least reliable but ensures data

**Output**: `deals.json` (~200 KB)
```json
[
  {
    "store": "ICA Supermarket",
    "name": "Kycklingfilé",
    "price": "99:-",
    "unit": "/kg",
    "description": "Färsk",
    "ord_pris": "129:-",
    "jfr_pris": "99:-/kg",
    "image": "https://..."
  }
]
```

#### 1.2 match_recipes.py

**Purpose**: Match recipe ingredients to current deals

**Algorithm**:
1. Load deals and recipes
2. For each recipe ingredient:
   - Normalize text (lowercase, remove diacritics)
   - Check against IGNORE_WORDS (salt, pepper, etc.)
   - Check FALSE_MATCHES (avoid "ris" → "riskakor")
   - Calculate match score:
     - 1.0 = Exact match
     - 0.9 = Substring match
     - 0.85 = Synonym match
     - 0.75 = Word overlap
     - 0.7 = Fuzzy similarity
3. Group matches by store
4. Calculate match percentage

**Output**: `recipe_matches.json` (~6.5 MB)
```json
{
  "last_updated": "2024-02-07T09:00:00Z",
  "total_deals": 850,
  "total_recipes": 250,
  "recipes": [
    {
      "name": "Kycklinggryta",
      "url": "https://...",
      "total_ingredients": 8,
      "matched_count": 5,
      "match_percentage": 62.5,
      "matched_ingredients": [...],
      "unmatched_ingredients": [...]
    }
  ]
}
```

#### 1.3 validate_data.py

**Purpose**: Validate JSON data quality

**Checks**:
- JSON syntax validity
- Required fields present
- Field types correct
- Value ranges reasonable
- No duplicates
- URL format validation

**Exit Codes**:
- 0 = All valid
- 1 = Validation errors

### 2. Frontend Architecture

#### 2.1 Single Page Application (SPA)

**Technology Stack**:
- Vanilla JavaScript (ES2022)
- No build step required
- Hash-based routing
- LocalStorage for preferences

**Pages**:
1. `/recipes` - Recipe browser with match %
2. `/deals` - Deal browser with search
3. `/lists` - Shopping list manager

#### 2.2 Data Flow

```
User Action → Router → Page Controller → Render
                ↓
        Fetch JSON Data (cached)
                ↓
        Filter/Sort Logic
                ↓
        Virtual Scroll (deals page)
                ↓
        Update DOM
```

#### 2.3 Key Features

**Performance**:
- Virtual scrolling for large lists
- Debounced search (300ms)
- Lazy image loading
- Request animation frame for animations

**UX**:
- Dark/light theme with system preference detection
- Responsive design (mobile-first)
- Store filter with localStorage persistence
- Category and nutrition filters
- Weighted rating sort (IMDB-style)

**Accessibility**:
- ARIA labels for all interactive elements
- Keyboard navigation support
- Semantic HTML
- Screen reader friendly

### 3. CI/CD Pipeline

#### 3.1 Weekly Scrape Workflow

```yaml
Schedule: Monday 6 AM UTC
Trigger: Cron or manual dispatch

Steps:
1. Checkout code
2. Setup Python 3.12
3. Install playwright + deps
4. Run unit tests          ← Validation layer
5. Scrape deals           ← Data collection
6. Match recipes          ← Data processing
7. Validate data          ← Quality check
8. Commit & push          ← Deploy
```

**Fail-Safe**:
- Tests run before scraping
- Validation runs before commit
- Partial failures logged but don't block
- Git history preserves all versions

#### 3.2 Lint Workflow

```yaml
Trigger: Push/PR to main

Steps:
1. Checkout code
2. Setup Node.js 20
3. Install dependencies
4. Run ESLint (JS)
5. Run Stylelint (CSS)
6. Run TypeScript check
```

## Data Flow Diagram

```
┌─────────────┐
│ ereklamblad │
│   coop.se   │  Weekly grocery deals (HTML/JSON)
│  willys.se  │
└─────┬───────┘
      │ scrape
      ▼
┌─────────────┐
│ deals.json  │  Normalized deal data
└─────┬───────┘
      │
      │ match
      ▼
┌─────────────┐
│  recipes    │  Recipe ingredient lists
│   .json     │
└─────┬───────┘
      │
      ▼
┌─────────────┐
│   recipe_   │  Matched recipes with deals
│  matches    │
│   .json     │
└─────┬───────┘
      │
      │ fetch
      ▼
┌─────────────┐
│  Frontend   │  Interactive recipe browser
│    (SPA)    │
└─────────────┘
      │
      ▼
┌─────────────┐
│    User     │
└─────────────┘
```

## Technology Decisions

### Why No Build Step?

**Pros**:
- Simpler deployment (no build artifacts)
- Faster iteration (edit & refresh)
- GitHub Pages friendly
- No dependency hell

**Cons**:
- No TypeScript compilation (only checking)
- No bundling (but modern browsers handle ES modules)
- Larger file sizes (but mitigated by gzip)

**Verdict**: For this project size, vanilla JS is sufficient.

### Why Playwright vs Selenium?

**Playwright Advantages**:
- Modern browser automation
- Better API for request interception
- Faster execution
- Better error messages
- Official Python bindings

### Why Static JSON vs Database?

**Pros**:
- Zero server costs
- Instant cold starts
- Cacheable by CDN
- Version controlled
- No query overhead

**Cons**:
- Large file sizes (~6.5 MB)
- Full reload on updates
- No incremental queries

**Mitigation**:
- Optimization script reduces size by 52%
- Weekly updates are acceptable
- Client-side filtering is fast enough

### Why GitHub Actions vs Heroku Scheduler?

**GitHub Actions**:
- Free for public repos
- Integrated with repo
- No additional services
- Version controlled workflows
- Secrets management built-in

## Performance Characteristics

### Scraping Performance

- **Duration**: ~5-10 minutes for all stores
- **Rate**: ~30-50 requests total
- **Concurrency**: Sequential (avoid rate limits)
- **Memory**: ~200-500 MB peak

### Frontend Performance

- **Initial Load**: ~2-3s (6.5 MB JSON)
- **Optimized Load**: ~1-1.5s (3.1 MB JSON)
- **Time to Interactive**: ~1s
- **Search Latency**: <50ms (debounced)
- **Scroll Performance**: 60 FPS (virtual scroll)

### Data Sizes

| File | Size | Optimized | Reduction |
|------|------|-----------|-----------|
| deals.json | 200 KB | - | - |
| recipes.json | 1.7 MB | - | - |
| recipe_matches.json | 6.5 MB | 3.1 MB | 52% |

## Security Considerations

### Scraping

- ✅ Public data only
- ✅ Respects robots.txt
- ✅ Reasonable rate limits
- ✅ No authentication required
- ✅ User-agent identification

### Frontend

- ✅ XSS prevention (escapeHtml)
- ✅ No eval() or innerHTML with user data
- ✅ Content Security Policy friendly
- ✅ HTTPS only (GitHub Pages)
- ✅ No external tracking

### Data

- ✅ No personal information
- ✅ All data public
- ✅ No cookies (except localStorage prefs)
- ✅ No user accounts

## Scalability

### Current Limits

- **Stores**: 10 stores (can add more)
- **Recipes**: 250 recipes (can handle 1000+)
- **Deals**: 850 deals per week (can handle 5000+)
- **Users**: Unlimited (static site)

### Bottlenecks

1. **JSON File Size**: Mitigated by optimization script
2. **Scraping Time**: Could parallelize with care
3. **GitHub Actions Minutes**: 2000/month free tier

### Future Scaling

- Use CDN for JSON files
- Implement pagination for deals
- Split recipes by category
- Add search index for faster queries

## Maintenance

### Weekly Tasks (Automated)

- Scrape deals (GitHub Actions)
- Match recipes (GitHub Actions)
- Validate data (GitHub Actions)
- Deploy updates (Git push)

### Monthly Tasks (Manual)

- Review failed scrapes
- Update store URLs if changed
- Add new synonyms
- Tune match thresholds

### Yearly Tasks (Manual)

- Update recipe database
- Review and remove stale stores
- Update dependencies
- Review and optimize code

## Monitoring

### Key Metrics

1. **Scrape Success Rate**: % of stores successfully scraped
2. **Deal Count**: Should be 500-1000 per week
3. **Match Rate**: Average match % per recipe
4. **File Sizes**: Monitor for unexpected growth
5. **CI/CD Duration**: Track workflow execution time

### Alerts

- Scrape failures (check GitHub Actions)
- Validation errors (check logs)
- Zero products found (critical)
- File size > 10 MB (investigate)

## Future Enhancements

See CONFIGURATION.md for detailed roadmap.

### High Priority

- [ ] Apply optimization in production
- [ ] Add caching headers
- [ ] Improve mobile UX
- [ ] Add offline support

### Medium Priority

- [ ] Split Python code into modules
- [ ] Add more unit tests
- [ ] Improve error recovery
- [ ] Add health check endpoint

### Low Priority

- [ ] Add recipe API
- [ ] Support more stores
- [ ] Add price history
- [ ] Export shopping lists

# Contributing Guide

Thank you for considering contributing to Veckans Recept! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the issue, not the person
- Help others learn and grow

## How Can I Contribute?

### 🐛 Reporting Bugs

**Before submitting a bug:**
1. Check existing issues to avoid duplicates
2. Try to reproduce the issue
3. Check if the issue is already fixed in latest main

**When reporting:**
```markdown
**Describe the bug:**
A clear description of what the bug is.

**To Reproduce:**
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior:**
What you expected to happen.

**Screenshots:**
If applicable, add screenshots.

**Environment:**
- OS: [e.g., macOS 14]
- Browser: [e.g., Chrome 120]
- Python version: [e.g., 3.12]
```

### 💡 Suggesting Features

**Feature requests should include:**
- Clear use case
- Expected behavior
- Potential implementation approach
- Why this benefits users

### 🔧 Code Contributions

#### Getting Started

1. **Fork the repository**
   ```bash
   # Click "Fork" on GitHub
   git clone https://github.com/YOUR_USERNAME/reklamblad.git
   cd reklamblad
   ```

2. **Install dependencies**
   ```bash
   # Python dependencies
   pip install playwright requests
   playwright install chromium
   
   # Node dependencies (for linting)
   npm install
   ```

3. **Create a branch**
   ```bash
   git checkout -b feature/my-feature
   # or
   git checkout -b fix/bug-description
   ```

#### Development Workflow

1. **Make your changes**
   - Write clean, readable code
   - Follow existing code style
   - Add comments for complex logic

2. **Write tests**
   ```bash
   # Add tests in test_match_recipes.py
   # Run tests
   python test_match_recipes.py
   ```

3. **Run linters**
   ```bash
   npm run lint
   # Fix issues automatically
   npm run lint:fix
   ```

4. **Validate data**
   ```bash
   # If you modified scrapers or matchers
   python scrape_deals.py
   python match_recipes.py
   python validate_data.py
   ```

5. **Test locally**
   ```bash
   python -m http.server 8000
   # Visit http://localhost:8000
   ```

#### Code Style

**Python**
- Follow PEP 8
- Use type hints for function parameters
- Add docstrings for all functions
- Maximum line length: 100 characters
- Use descriptive variable names

```python
def match_score(deal_name: str, ingredient: str) -> float:
    """Calculate match score between a deal and an ingredient.
    
    Args:
        deal_name: Name of the deal product
        ingredient: Recipe ingredient to match
        
    Returns:
        Score between 0.0 and 1.0
    """
    # Implementation
```

**JavaScript**
- Use `const` by default, `let` when needed
- No `var`
- Use arrow functions for callbacks
- Add JSDoc comments for classes/methods
- Use strict equality (`===`)

```javascript
/**
 * Calculate match percentage
 * @param {number} matched - Number of matched ingredients
 * @param {number} total - Total ingredients
 * @returns {number} Percentage (0-100)
 */
function calculatePercentage(matched, total) {
    return total > 0 ? (matched / total) * 100 : 0;
}
```

**CSS**
- Use kebab-case for class names
- Group related properties
- Use CSS custom properties for colors
- Mobile-first responsive design

```css
.recipe-card {
    /* Layout */
    display: flex;
    flex-direction: column;
    
    /* Spacing */
    padding: 1rem;
    gap: 0.5rem;
    
    /* Visual */
    background: var(--card-bg);
    border-radius: 8px;
}
```

#### Testing

**Unit Tests**
- Test new matching logic
- Test edge cases
- Test error handling
- Aim for >80% coverage

```python
class TestNewFeature(unittest.TestCase):
    def test_basic_functionality(self):
        """Test basic case"""
        result = my_function('input')
        self.assertEqual(result, 'expected')
    
    def test_edge_case(self):
        """Test edge case"""
        result = my_function('')
        self.assertEqual(result, '')
```

**Manual Testing**
- Test in Chrome, Firefox, Safari
- Test on mobile devices
- Test dark/light themes
- Test with slow network
- Test with disabled JavaScript

#### Commit Messages

Follow conventional commits:

```
feat: add nutrition filter for recipes
fix: correct false match for "ris" and "riskakor"
docs: update architecture documentation
test: add tests for synonym matching
refactor: extract common scraping logic
perf: optimize recipe data loading
chore: update dependencies
```

**Good commits:**
- Clear, concise subject line (<50 chars)
- Detailed body if needed
- Reference issues: `Fixes #123`
- Explain WHY, not just WHAT

**Bad commits:**
- "fix stuff"
- "updates"
- "WIP" (squash before PR)

### 📝 Documentation

Documentation improvements are always welcome!

**What to document:**
- New features
- Configuration options
- API changes
- Architecture decisions
- Troubleshooting steps

**Documentation locations:**
- `README.md` - Overview and quick start
- `ARCHITECTURE.md` - System design
- `CONFIGURATION.md` - Configuration guide
- Code comments - Complex logic
- JSDoc/docstrings - Public APIs

### 🔄 Pull Request Process

1. **Update documentation**
   - Update README if needed
   - Add/update code comments
   - Update CONFIGURATION.md for new options

2. **Ensure tests pass**
   ```bash
   python test_match_recipes.py
   npm run lint
   npm run typecheck
   ```

3. **Update CHANGELOG** (if applicable)
   ```markdown
   ## [Unreleased]
   ### Added
   - New nutrition filter feature
   
   ### Fixed
   - False match bug in ingredient matching
   ```

4. **Create pull request**
   - Use descriptive title
   - Explain what and why
   - Link related issues
   - Add screenshots for UI changes

**PR template:**
```markdown
## Description
Brief description of changes

## Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement

## Testing
- [ ] Tests pass locally
- [ ] Linters pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No breaking changes
```

5. **Respond to feedback**
   - Address review comments
   - Update code as needed
   - Be open to suggestions

### 🏪 Adding New Stores

To add a new grocery store:

1. **Identify data source**
   - Find store's weekly deals page
   - Check if they have an API
   - Verify data is publicly accessible

2. **Add to scraper**
   ```python
   # In scrape_deals.py
   stores = [
       # ... existing stores
       ('New Store', 'https://example.com/deals'),
   ]
   ```

3. **Implement scraping logic**
   - Try API interception first
   - Fall back to DOM parsing
   - Handle errors gracefully

4. **Test thoroughly**
   ```bash
   python scrape_deals.py
   python validate_data.py
   ```

5. **Update documentation**
   - Add to README.md
   - Update CONFIGURATION.md

### 🔤 Adding Synonyms

To improve ingredient matching:

1. **Identify patterns**
   - Look for missed matches in logs
   - Check common ingredient variants

2. **Add to SYNONYMS**
   ```python
   # In match_recipes.py
   SYNONYMS = {
       'kyckling': ['kycklingfile', 'kycklingbrost', ...],
       'new_base': ['variant1', 'variant2', ...],
   }
   ```

3. **Add tests**
   ```python
   def test_new_synonym(self):
       score = match_score('variant1', 'new_base')
       self.assertGreater(score, 0.8)
   ```

4. **Validate impact**
   ```bash
   python test_match_recipes.py
   python match_recipes.py
   ```

### 🎨 UI/UX Improvements

**Before starting:**
1. Create mockup or design
2. Consider accessibility
3. Test on multiple devices
4. Ensure responsive design

**Implementation checklist:**
- [ ] Mobile-friendly
- [ ] Dark mode support
- [ ] Keyboard accessible
- [ ] Screen reader friendly
- [ ] Fast performance
- [ ] Cross-browser compatible

## Development Environment

### Recommended Setup

**Editor**: VSCode with extensions:
- ESLint
- Stylelint
- Python
- Prettier (optional)

**Browser**: Chrome with DevTools

**Python**: 3.12+

**Node**: 20+

### Environment Variables

```bash
# Optional - override defaults
export HEADLESS=false  # See browser during scraping
export VIEWPORT_WIDTH=1920
export TIMEOUT_NAVIGATION=60000
```

## Performance Guidelines

- Minimize JSON file sizes
- Use virtual scrolling for long lists
- Debounce user input
- Lazy load images
- Use CSS transforms for animations
- Avoid unnecessary re-renders

## Security Guidelines

- Never commit secrets or API keys
- Validate all user input
- Escape HTML output
- Use Content Security Policy
- Respect robots.txt
- Implement rate limiting

## Release Process

1. Update version in package.json
2. Update CHANGELOG.md
3. Create GitHub release
4. Tag with version: `v1.2.3`
5. Deploy automatically via GitHub Actions

## Questions?

- Open an issue for questions
- Check existing documentation
- Review closed issues for similar problems

## Thank You!

Your contributions make this project better for everyone. Thank you for taking the time to contribute! 🎉

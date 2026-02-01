#!/usr/bin/env python3
"""Scrape protein-rich recipes from HelloFresh.se."""

import json
import os
import re
import sys
import time
from playwright.sync_api import sync_playwright


def log(msg):
    print(msg, flush=True)

BASE_URL = 'https://www.hellofresh.se'
CATEGORY_URL = f'{BASE_URL}/recipes/proteinrik-recept'


def collect_recipe_urls(page) -> list[str]:
    """Paginate through category to collect all recipe URLs."""
    recipe_urls = set()
    page_num = 1
    prev_count = 0

    log("Collecting recipe URLs...")

    while True:
        url = f'{CATEGORY_URL}?page={page_num}'
        page.goto(url, timeout=30000)
        page.wait_for_load_state('domcontentloaded', timeout=15000)
        time.sleep(2)

        # Extract recipe links (format: /recipes/name-hexid)
        links = page.locator('a[href*="/recipes/"]').all()
        for link in links:
            href = link.get_attribute('href')
            if href and re.match(r'.*/recipes/[a-z].*-[a-f0-9]{20,}$', href):
                if href.startswith('/'):
                    href = BASE_URL + href
                recipe_urls.add(href)

        current_count = len(recipe_urls)
        log(f"  Page {page_num}: {current_count} unique recipes")

        if current_count == prev_count:
            break

        prev_count = current_count
        page_num += 1

    return list(recipe_urls)


def parse_ingredient(ingredient: str) -> str:
    """Extract main ingredient name from HelloFresh ingredient string."""
    # Remove quantity prefix: "2 st ", "150 g ", "1 portionspåse ", etc.
    simplified = re.sub(
        r'^[\d/½¼¾⅓⅔]+\s*(st|g|kg|dl|l|ml|cl|msk|tsk|krm|paket|portionspåse|port)\s+',
        '', ingredient, flags=re.I
    )
    # Remove any remaining leading numbers
    simplified = re.sub(r'^[\d/½¼¾⅓⅔,.\s]+\s+', '', simplified)
    # Remove parenthetical notes
    simplified = re.sub(r'\s*\([^)]*\)', '', simplified)
    # Remove trailing step references like "(steg 4)"
    simplified = re.sub(r'\s*\(steg\s*\d+\)', '', simplified, flags=re.I)

    return simplified.strip().lower()


def extract_recipe_data(page, url: str, retries: int = 2) -> dict | None:
    """Extract recipe data from JSON-LD on recipe page."""
    for attempt in range(retries + 1):
        try:
            page.goto(url, timeout=30000)
            page.wait_for_load_state('domcontentloaded', timeout=15000)

            html = page.content()

            # Find all JSON-LD blocks
            matches = re.findall(
                r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
                html, re.DOTALL
            )

            for m in matches:
                try:
                    data = json.loads(m)
                    if isinstance(data, dict) and data.get('@type') == 'Recipe':
                        nutrition = data.get('nutrition', {})
                        rating_data = data.get('aggregateRating', {})

                        # Parse instructions - HelloFresh uses HowToStep with HTML
                        instructions = []
                        for step in data.get('recipeInstructions', []):
                            if isinstance(step, dict):
                                text = step.get('text', '')
                                # Strip HTML tags
                                text = re.sub(r'<[^>]+>', ' ', text)
                                text = re.sub(r'\s+', ' ', text).strip()
                                if text:
                                    instructions.append({'text': text})
                            elif isinstance(step, str):
                                instructions.append({'text': step})

                        ingredients = data.get('recipeIngredient', [])

                        return {
                            'name': data.get('name', ''),
                            'url': url,
                            'description': data.get('description', ''),
                            'image': data.get('image', ''),
                            'time': data.get('totalTime', ''),
                            'servings': str(data.get('recipeYield', '')),
                            'category': data.get('recipeCategory', ''),
                            'ingredients': ingredients,
                            'rating': float(rating_data.get('ratingValue', 0)) if rating_data else None,
                            'reviews': int(rating_data.get('ratingCount', 0)) if rating_data else None,
                            'instructions': instructions,
                            'simplified_ingredients': [parse_ingredient(ing) for ing in ingredients],
                            'nutrition': {
                                'calories': nutrition.get('calories', ''),
                                'protein': nutrition.get('proteinContent', ''),
                                'fat': nutrition.get('fatContent', ''),
                                'carbs': nutrition.get('carbohydrateContent', ''),
                                'fiber': nutrition.get('fiberContent', ''),
                                'sodium': nutrition.get('sodiumContent', ''),
                            } if nutrition else None,
                            'source': 'hellofresh',
                        }
                except json.JSONDecodeError:
                    continue

        except Exception as e:
            if attempt < retries:
                log(f"    Retry {attempt + 1}/{retries} after error: {e}")
                time.sleep(3 * (attempt + 1))  # Exponential backoff
            else:
                log(f"    Error: {e}")

    return None


def main():
    log("=== HelloFresh Recipe Scraper ===\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Step 1: Collect all recipe URLs
        recipe_urls = collect_recipe_urls(page)
        log(f"\nFound {len(recipe_urls)} unique recipes\n")

        if not recipe_urls:
            log("No recipes found")
            browser.close()
            return

        # Step 2: Scrape each recipe
        recipes = []

        for i, url in enumerate(recipe_urls):
            log(f"[{i+1}/{len(recipe_urls)}] {url.split('/')[-1][:50]}")

            recipe = extract_recipe_data(page, url)

            if recipe:
                recipes.append(recipe)
                log(f"    OK - {len(recipe['ingredients'])} ingredients")
            else:
                log(f"    FAIL")

            time.sleep(1.5)  # Rate limit delay

        browser.close()

    log(f"\n=== Done! ===")
    log(f"Successfully scraped {len(recipes)} recipes")

    # Save to file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, 'hellofresh_recipes.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)
    log(f"Saved to: {output_file}")


if __name__ == '__main__':
    main()

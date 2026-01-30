#!/usr/bin/env python3
"""Update existing recipes with nutrition data from ICA.se."""

import json
import os
import re
import time
from playwright.sync_api import sync_playwright


def get_nutrition(page, url: str) -> dict | None:
    """Fetch nutrition data from recipe page JSON-LD."""
    try:
        page.goto(url, timeout=20000)
        page.wait_for_load_state('domcontentloaded', timeout=10000)
        html = page.content()

        matches = re.findall(
            r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.DOTALL
        )

        for m in matches:
            try:
                data = json.loads(m)
                if isinstance(data, dict) and data.get('@type') == 'Recipe':
                    nutrition = data.get('nutrition', {})
                    if nutrition:
                        return {
                            'calories': nutrition.get('calories', ''),
                            'protein': nutrition.get('proteinContent', ''),
                            'fat': nutrition.get('fatContent', ''),
                            'carbs': nutrition.get('carbohydrateContent', ''),
                        }
            except json.JSONDecodeError:
                continue
    except Exception as e:
        print(f"  Error: {e}")
    return None


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    recipes_file = os.path.join(script_dir, 'recipes.json')

    with open(recipes_file, 'r') as f:
        recipes = json.load(f)

    print(f"Updating nutrition for {len(recipes)} recipes...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        updated = 0
        for i, recipe in enumerate(recipes):
            name = recipe.get('name', 'Unknown')
            url = recipe.get('url', '')

            # Skip if already has nutrition
            if recipe.get('nutrition'):
                print(f"[{i+1}/{len(recipes)}] {name[:40]} - SKIP (has nutrition)")
                continue

            print(f"[{i+1}/{len(recipes)}] {name[:40]}", end='', flush=True)

            nutrition = get_nutrition(page, url)
            if nutrition:
                recipe['nutrition'] = nutrition
                updated += 1
                print(f" - OK ({nutrition['calories']})")
            else:
                print(" - NO DATA")

            time.sleep(0.3)

        browser.close()

    with open(recipes_file, 'w', encoding='utf-8') as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Updated {updated} recipes with nutrition data.")


if __name__ == '__main__':
    main()

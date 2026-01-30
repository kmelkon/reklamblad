#!/usr/bin/env python3
"""Scrape highly-rated recipes (4.5+ stars) from ICA.se with ingredients."""

import json
import os
import re
import time
from playwright.sync_api import sync_playwright
import requests

API_BASE = 'https://apimgw-pub.ica.se/sverige/digx/mdsarecipesearch/v1/page-and-filters'
MIN_RATING = 4.5
BATCH_SIZE = 500


def get_bearer_token() -> str:
    """Get Bearer token by visiting ICA site."""
    token = None

    def capture_token(request):
        nonlocal token
        auth = request.headers.get('authorization', '')
        if auth.startswith('Bearer ') and not token:
            token = auth

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on('request', capture_token)
        page.goto('https://www.ica.se/recept/', timeout=30000)
        page.wait_for_load_state('networkidle', timeout=15000)
        browser.close()

    return token


def get_all_recipe_cards(token: str, min_rating: float = MIN_RATING) -> list[dict]:
    """Fetch all recipe cards with rating >= min_rating using pagination."""
    headers = {'Authorization': token, 'Accept': 'application/json'}
    all_cards = []
    skip = 0

    print(f"Fetching recipes with rating >= {min_rating}...")

    while True:
        url = f'{API_BASE}?url=/&take={BATCH_SIZE}&skip={skip}&onlyEnabled=true'
        resp = requests.get(url, headers=headers)

        if resp.status_code != 200:
            print(f"  API error at skip={skip}: {resp.status_code}")
            break

        data = resp.json()
        cards = data.get('pageDto', {}).get('recipeCards', [])

        if not cards:
            break

        # Filter by rating
        for card in cards:
            rating_data = card.get('rating', {})
            avg_rating = rating_data.get('averageRating', 0) if rating_data else 0
            if avg_rating >= min_rating:
                all_cards.append(card)

        print(f"  Fetched {skip + len(cards)} recipes, {len(all_cards)} match rating filter")
        skip += BATCH_SIZE

        # Small delay between API calls
        time.sleep(0.2)

    return all_cards


def get_recipe_details(page, recipe_url: str) -> dict | None:
    """Get full recipe details from JSON-LD on recipe page."""
    full_url = f'https://www.ica.se{recipe_url}'

    try:
        page.goto(full_url, timeout=20000)
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
                    return {
                        'name': data.get('name', ''),
                        'url': full_url,
                        'description': data.get('description', ''),
                        'image': data.get('image'),
                        'time': data.get('totalTime', ''),
                        'servings': data.get('recipeYield', ''),
                        'category': data.get('recipeCategory', ''),
                        'ingredients': data.get('recipeIngredient', []),
                        'rating': data.get('aggregateRating', {}).get('ratingValue'),
                        'reviews': data.get('aggregateRating', {}).get('reviewCount'),
                        'instructions': normalize_instructions(data.get('recipeInstructions', [])),
                        'nutrition': {
                            'calories': nutrition.get('calories', ''),
                            'protein': nutrition.get('proteinContent', ''),
                            'fat': nutrition.get('fatContent', ''),
                            'carbs': nutrition.get('carbohydrateContent', ''),
                        } if nutrition else None,
                    }
            except json.JSONDecodeError:
                continue

    except Exception as e:
        print(f"    Error fetching {recipe_url}: {e}")

    return None


def normalize_instructions(instructions: list) -> list[dict]:
    """Normalize instructions to list of step objects."""
    result = []
    for step in instructions:
        if isinstance(step, str):
            result.append({'text': step})
        elif isinstance(step, dict):
            normalized = {}
            for key in ('name', 'text', 'image', 'url'):
                if step.get(key):
                    normalized[key] = step[key]
            if normalized:
                result.append(normalized)
    return result


def simplify_ingredient(ingredient: str) -> str:
    """Extract the main ingredient name from a full ingredient string."""
    simplified = re.sub(r'\([^)]*\)', '', ingredient)
    simplified = re.sub(r'^[\d/,.\s]+\s*(g|kg|dl|l|ml|cl|msk|tsk|st|krm|port|burk|paket|förp)\s+', '', simplified, flags=re.I)
    simplified = re.sub(r'^[\d/,.\s]+\s+', '', simplified)
    simplified = re.sub(r'\s*à\s*\d+\s*\w*', '', simplified)
    simplified = re.sub(r'\s*\(?\d+\s*(g|ml|dl)\)?$', '', simplified)

    return simplified.strip().lower()


def main():
    print("=== ICA Recipe Scraper ===\n")

    print("Getting auth token...")
    token = get_bearer_token()
    if not token:
        print("Failed to get token")
        return
    print(f"Got token: {token[:40]}...\n")

    # Fetch all recipe cards with rating filter
    recipe_cards = get_all_recipe_cards(token, MIN_RATING)
    print(f"\nFound {len(recipe_cards)} recipes with rating >= {MIN_RATING}\n")

    if not recipe_cards:
        print("No recipes found")
        return

    # Fetch full details for each recipe
    recipes = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        for i, card in enumerate(recipe_cards):
            title = card.get('title', 'Unknown')
            url = card.get('url', '')
            print(f"[{i+1}/{len(recipe_cards)}] {title}")

            details = get_recipe_details(page, url)

            if details:
                details['simplified_ingredients'] = [
                    simplify_ingredient(ing) for ing in details['ingredients']
                ]
                recipes.append(details)
                print(f"    OK {len(details['ingredients'])} ingredients")
            else:
                print(f"    FAIL")

            time.sleep(0.5)

        browser.close()

    print(f"\n=== Done! ===")
    print(f"Successfully scraped {len(recipes)} recipes")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, 'recipes.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)
    print(f"Saved to: {output_file}")


if __name__ == '__main__':
    main()

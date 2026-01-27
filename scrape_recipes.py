#!/usr/bin/env python3
"""Scrape top 100 recipes from ICA.se with ingredients."""

import json
import os
import re
import time
from playwright.sync_api import sync_playwright
import requests

CATEGORIES = [
    ('/billig/', 'Budget'),
    ('/svensk/', 'Svenska klassiker'),
    ('/till-matlada/', 'Matlada'),
    ('/snabbt/', 'Snabbt'),
    ('/vegetariskt/', 'Vegetariskt'),
    ('/vardagsmat/', 'Vardagsmat'),
    ('/kyckling/', 'Kyckling'),
    ('/fisk/', 'Fisk'),
    ('/pasta/', 'Pasta'),
    ('/soppa/', 'Soppa'),
]

RECIPES_PER_CATEGORY = 15


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


def get_recipe_list(token: str, category_url: str, take: int = 20) -> list[dict]:
    """Get recipe cards from a category."""
    headers = {'Authorization': token, 'Accept': 'application/json'}
    url = f'https://apimgw-pub.ica.se/sverige/digx/mdsarecipesearch/v1/page-and-filters?url={category_url}&take={take}&onlyEnabled=true'

    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"  API error: {resp.status_code}")
        return []

    data = resp.json()
    return data.get('pageDto', {}).get('recipeCards', [])


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
                    }
            except json.JSONDecodeError:
                continue

    except Exception as e:
        print(f"    Error fetching {recipe_url}: {e}")

    return None


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

    all_recipe_cards = []
    seen_ids = set()

    for cat_url, cat_name in CATEGORIES:
        print(f"Fetching category: {cat_name}")
        cards = get_recipe_list(token, cat_url, RECIPES_PER_CATEGORY)
        print(f"  Got {len(cards)} recipes")

        for card in cards:
            rid = card.get('id')
            if rid not in seen_ids:
                seen_ids.add(rid)
                card['ica_category'] = cat_name
                all_recipe_cards.append(card)

    print(f"\nTotal unique recipes: {len(all_recipe_cards)}")

    all_recipe_cards = all_recipe_cards[:100]
    print(f"Processing top {len(all_recipe_cards)} recipes...\n")

    recipes = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        for i, card in enumerate(all_recipe_cards):
            title = card.get('title', 'Unknown')
            url = card.get('url', '')
            print(f"[{i+1}/{len(all_recipe_cards)}] {title}")

            details = get_recipe_details(page, url)

            if details:
                details['ica_category'] = card.get('ica_category', '')
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

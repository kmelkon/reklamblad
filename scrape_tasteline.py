#!/usr/bin/env python3
"""Scrape highly-rated recipes from Tasteline.com via WordPress REST API."""

import json
import os
import time
import requests

API_BASE = 'https://www.tasteline.com/wp-json/wp/v2'
MIN_RATING = 4.0  # Tasteline has fewer high-rated recipes, use 4.0
BATCH_SIZE = 100
REQUEST_DELAY = 0.3  # Be nice to their servers


def fetch_all_pages(endpoint: str, params: dict = None) -> list:
    """Fetch all pages from a paginated WordPress API endpoint."""
    params = params or {}
    params['per_page'] = BATCH_SIZE
    all_items = []
    page = 1

    while True:
        params['page'] = page
        resp = requests.get(f'{API_BASE}/{endpoint}', params=params)

        if resp.status_code == 400:  # Past last page
            break
        if resp.status_code != 200:
            print(f"  API error on {endpoint} page {page}: {resp.status_code}")
            break

        items = resp.json()
        if not items:
            break

        all_items.extend(items)
        print(f"  {endpoint}: fetched page {page} ({len(all_items)} total)")
        page += 1
        time.sleep(REQUEST_DELAY)

    return all_items


def build_lookups() -> tuple[dict, dict]:
    """Build ingredient ID -> name and unit ID -> name lookup tables."""
    print("Building ingredient lookup...")
    ingredients_raw = fetch_all_pages('ingredient')
    ingredients = {i['id']: i['name'] for i in ingredients_raw}
    print(f"  {len(ingredients)} ingredients\n")

    print("Building unit lookup...")
    units_raw = fetch_all_pages('unit')
    units = {u['id']: u['title']['rendered'] for u in units_raw}
    print(f"  {len(units)} units\n")

    return ingredients, units


def parse_recipe(recipe: dict, ingredients_lookup: dict, units_lookup: dict) -> dict | None:
    """Parse a recipe from the API response."""
    meta = recipe.get('meta', {})
    data = meta.get('tasteline_recipe_data', {})

    if not data:
        return None

    recipe_info = data.get('recipe', {})
    rating_data = recipe_info.get('rating', {})
    rating = rating_data.get('rating') if rating_data else None

    # Parse rating (can be string or float)
    if rating is not None:
        try:
            rating = float(rating)
        except (ValueError, TypeError):
            rating = None

    # Parse ingredients (can be dict or list)
    ingredients_data = data.get('ingredients', {})
    ingredients = []
    simplified_ingredients = []

    # Handle both dict and list formats
    if isinstance(ingredients_data, dict):
        ing_items = ingredients_data.values()
    elif isinstance(ingredients_data, list):
        ing_items = ingredients_data
    else:
        ing_items = []

    for ing in ing_items:
        ing_id = ing.get('ingredientId')
        unit_id = ing.get('unitId')
        quantity = ing.get('quantity', '')
        comment = ing.get('comment', '')

        ing_name = ingredients_lookup.get(ing_id, comment or 'unknown')
        unit_name = units_lookup.get(unit_id, '')

        # Build full ingredient string
        parts = []
        if quantity:
            parts.append(str(quantity))
        if unit_name:
            parts.append(unit_name)
        parts.append(ing_name)

        ingredients.append(' '.join(parts))
        simplified_ingredients.append(ing_name.lower())

    # Parse instructions (can be dict or list)
    steps_data = data.get('steps', {})
    instructions = []

    if isinstance(steps_data, dict):
        step_items = steps_data.values()
    elif isinstance(steps_data, list):
        step_items = steps_data
    else:
        step_items = []

    for step in sorted(step_items, key=lambda x: x.get('order', 0) if isinstance(x, dict) else 0):
        if isinstance(step, dict):
            text = step.get('content') or step.get('description', '')
            if text:
                instructions.append({'text': text})

    # Parse time (seconds -> ISO 8601)
    total_duration = recipe_info.get('totalDuration')
    time_iso = None
    if total_duration:
        try:
            minutes = int(total_duration) // 60
            time_iso = f'PT{minutes}M'
        except (ValueError, TypeError):
            pass

    return {
        'name': recipe.get('title', {}).get('rendered', ''),
        'url': recipe.get('link', ''),
        'description': recipe_info.get('description', ''),
        'image': recipe_info.get('image', ''),
        'time': time_iso,
        'servings': recipe_info.get('portions', ''),
        'category': recipe_info.get('category', ''),
        'difficulty': recipe_info.get('difficulty', ''),
        'ingredients': ingredients,
        'simplified_ingredients': simplified_ingredients,
        'instructions': instructions,
        'rating': rating,
        'reviews': int(rating_data.get('votes', 0)) if rating_data else 0,
        'source': 'tasteline',
    }


def main():
    print("=== Tasteline Recipe Scraper ===\n")

    # Build lookup tables
    ingredients_lookup, units_lookup = build_lookups()

    # Fetch all recipes
    print("Fetching recipes...")
    raw_recipes = fetch_all_pages('recipe')
    print(f"\nTotal recipes fetched: {len(raw_recipes)}\n")

    # Parse and filter by rating
    print(f"Parsing recipes with rating >= {MIN_RATING}...")
    recipes = []
    skipped_no_rating = 0
    skipped_low_rating = 0

    for raw in raw_recipes:
        parsed = parse_recipe(raw, ingredients_lookup, units_lookup)

        if not parsed:
            continue

        if parsed['rating'] is None:
            skipped_no_rating += 1
            continue

        if parsed['rating'] < MIN_RATING:
            skipped_low_rating += 1
            continue

        recipes.append(parsed)

    print(f"  Passed filter: {len(recipes)}")
    print(f"  Skipped (no rating): {skipped_no_rating}")
    print(f"  Skipped (rating < {MIN_RATING}): {skipped_low_rating}")

    # Sort by rating
    recipes.sort(key=lambda x: (x['rating'] or 0, x['reviews'] or 0), reverse=True)

    # Save
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, 'tasteline_recipes.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)

    print(f"\n=== Done! ===")
    print(f"Saved {len(recipes)} recipes to: {output_file}")


if __name__ == '__main__':
    main()

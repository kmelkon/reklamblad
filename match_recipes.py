#!/usr/bin/env python3
"""Match current deals to recipes - find recipes with ingredients on sale."""

import json
import os
import re
from datetime import datetime
from difflib import SequenceMatcher

SYNONYMS = {
    'fars': ['blandfars', 'notfars', 'flaskfars', 'kycklingfars', 'kottfars', 'umamifars'],
    'kyckling': ['kycklingfile', 'kycklinglar', 'kycklingbrost', 'kycklingklubba', 'strimlad kyckling', 'kycklinglarfile'],
    'lax': ['laxfile', 'varmrokt lax', 'gravad lax', 'rokt lax'],
    'torsk': ['torskfile', 'torskrygg'],
    'bacon': ['bacon', 'sidflask', 'stekflask'],
    'flask': ['flaskkotlett', 'flaskfile', 'kassler'],
    'ost': ['riven ost', 'mozzarella', 'parmesan', 'parmesanost', 'cheddar', 'vasterbottensost', 'fetaost'],
    'gradde': ['vispgradde', 'matlagningsgradde', 'creme fraiche'],
    'graddfil': ['graddfil', 'creme fraiche'],
    'mjolk': ['mjolk', 'havremjolk', 'lattmjolk'],
    'smor': ['smor'],
    'lok': ['gul lok', 'rodlok', 'purjolok', 'salladslok', 'lokar'],
    'potatis': ['potatis', 'farskpotatis'],
    'tomat': ['tomater', 'krossade tomater', 'hela tomater', 'plommontomater', 'babyplommontomater'],
    'paprika': ['paprika', 'rod paprika', 'gul paprika'],
    'agg': ['agg', 'aggula'],
    'pasta': ['pasta', 'spaghetti', 'penne', 'makaroner', 'tagliatelle', 'lasagne', 'lasagnette'],
    'yoghurt': ['yoghurt', 'naturell yoghurt', 'turkisk yoghurt', 'matyoghurt'],
    'druvor': ['druvor', 'grona druvor', 'roda druvor'],
    'applen': ['applen', 'apple', 'svenska applen'],
    'rakor': ['rakor', 'handskalade rakor', 'skaldjur'],
    'falukorv': ['falukorv', 'korv'],
    'kottbullar': ['kottbullar'],
    'hamburgare': ['hamburgare', 'hamburgarbrod'],
    'broccoli': ['broccoli'],
    'blomkal': ['blomkal'],
    'mango': ['mango'],
    'avokado': ['avokado', 'avokador'],
}

IGNORE_WORDS = {
    'vatten', 'salt', 'peppar', 'olja', 'socker', 'mjol',
    'buljong', 'fond', 'krydda', 'kryddor', 'orter',
}

FALSE_MATCHES = [
    ('ris', 'riskakor'),
    ('ris', 'majskakor'),
    ('brod', 'strobrod'),
    ('agg', 'palagg'),
    ('ost', 'dessertost'),
    ('flask', 'flaskfile'),
]


def normalize(text: str) -> str:
    """Normalize text for matching."""
    text = text.lower().strip()
    # Remove Swedish diacritics for matching
    text = text.replace('å', 'a').replace('ä', 'a').replace('ö', 'o')
    text = re.sub(r'^(farsk|fryst|ekologisk|svensk|riven|hackad|skivad|strimlad|hel|hela)\s+', '', text)
    text = re.sub(r'\s+(farsk|fryst|ekologisk)$', '', text)
    return text


def match_score(deal_name: str, ingredient: str) -> float:
    """Calculate match score between a deal and an ingredient (0-1)."""
    deal_norm = normalize(deal_name)
    ing_norm = normalize(ingredient)

    if ing_norm in IGNORE_WORDS or any(ing_norm.startswith(w) for w in IGNORE_WORDS):
        return 0.0

    for ing_pattern, deal_pattern in FALSE_MATCHES:
        if ing_pattern in ing_norm and deal_pattern in deal_norm:
            return 0.0

    if deal_norm == ing_norm:
        return 1.0

    if len(ing_norm) >= 4:
        if deal_norm in ing_norm or ing_norm in deal_norm:
            return 0.9

    for base, variants in SYNONYMS.items():
        deal_matches = deal_norm == base or any(deal_norm == v or v in deal_norm for v in variants)
        ing_matches = ing_norm == base or any(ing_norm == v or v in ing_norm for v in variants)
        if deal_matches and ing_matches:
            return 0.85

    deal_words = set(deal_norm.split())
    ing_words = set(ing_norm.split())

    common_words = {'med', 'och', 'i', 'pa', 'for', 'av', 'eller', 'ca', 'g', 'kg', 'dl', 'st'}
    deal_words -= common_words
    ing_words -= common_words

    common = deal_words & ing_words
    if common:
        significant = [w for w in common if len(w) > 3]
        if significant:
            return 0.75

    if len(deal_norm) > 5 and len(ing_norm) > 5:
        ratio = SequenceMatcher(None, deal_norm, ing_norm).ratio()
        if ratio > 0.8:
            return ratio * 0.7

    return 0.0


def find_matching_deals(ingredient: str, deals: list[dict], threshold: float = 0.6) -> list[dict]:
    """Find deals that match an ingredient."""
    matches = []

    for deal in deals:
        deal_name = deal.get('name', '')
        score = match_score(deal_name, ingredient)

        if score >= threshold:
            matches.append({
                'deal': deal,
                'score': score,
                'ingredient': ingredient
            })

    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches


def analyze_recipe(recipe: dict, deals: list[dict]) -> dict:
    """Analyze a recipe to find matching deals."""
    ingredients = recipe.get('simplified_ingredients', [])

    matched_ingredients = []
    unmatched_ingredients = []

    for ing in ingredients:
        matches = find_matching_deals(ing, deals)

        if matches:
            best_match = matches[0]
            matched_ingredients.append({
                'ingredient': ing,
                'deal_name': best_match['deal']['name'],
                'deal_price': best_match['deal'].get('price'),
                'deal_store': best_match['deal'].get('store'),
                'match_score': best_match['score']
            })
        else:
            unmatched_ingredients.append(ing)

    match_percentage = len(matched_ingredients) / len(ingredients) * 100 if ingredients else 0

    return {
        'name': recipe.get('name'),
        'url': recipe.get('url'),
        'image': recipe.get('image'),
        'category': recipe.get('ica_category'),
        'total_ingredients': len(ingredients),
        'matched_count': len(matched_ingredients),
        'match_percentage': round(match_percentage, 1),
        'matched_ingredients': matched_ingredients,
        'unmatched_ingredients': unmatched_ingredients,
        'time': recipe.get('time'),
        'servings': recipe.get('servings'),
        'rating': recipe.get('rating'),
        'reviews': recipe.get('reviews'),
    }


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    deals_file = os.path.join(script_dir, 'deals.json')
    recipes_file = os.path.join(script_dir, 'recipes.json')

    with open(deals_file, 'r') as f:
        deals = json.load(f)

    with open(recipes_file, 'r') as f:
        recipes = json.load(f)

    print(f"Loaded {len(deals)} deals and {len(recipes)} recipes\n")

    results = []
    for recipe in recipes:
        analysis = analyze_recipe(recipe, deals)
        results.append(analysis)

    results.sort(key=lambda x: (x['matched_count'], x['match_percentage']), reverse=True)

    # Add metadata
    output = {
        'last_updated': datetime.utcnow().isoformat() + 'Z',
        'total_deals': len(deals),
        'total_recipes': len(recipes),
        'recipes': results
    }

    output_file = os.path.join(script_dir, 'recipe_matches.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Saved to: {output_file}\n")

    print("=" * 60)
    print("TOP RECIPE RECOMMENDATIONS")
    print("=" * 60)

    for i, r in enumerate(results[:10]):
        print(f"\n{i+1}. {r['name']}")
        print(f"   {r['matched_count']}/{r['total_ingredients']} ingredients on sale ({r['match_percentage']}%)")


if __name__ == '__main__':
    main()

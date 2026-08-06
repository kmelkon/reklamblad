#!/usr/bin/env python3
"""Monitor data file performance and quality.

Provides insights into:
- File sizes and growth trends
- Product counts per store
- Match quality metrics
- Data freshness
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any


def format_size(size_bytes: int) -> str:
    """Format bytes into human-readable size.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def analyze_deals(deals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze deals data.
    
    Args:
        deals: List of deal dictionaries
        
    Returns:
        Analysis results dictionary
    """
    # Count by store
    stores = {}
    for deal in deals:
        store = deal.get('store', 'Unknown')
        stores[store] = stores.get(store, 0) + 1
    
    # Count deals with images
    with_images = sum(1 for d in deals if d.get('image'))
    
    # Count deals with prices
    with_prices = sum(1 for d in deals if d.get('price'))
    
    # Count deals with comparison prices
    with_jfr = sum(1 for d in deals if d.get('jfr_pris'))
    with_ord = sum(1 for d in deals if d.get('ord_pris'))
    
    return {
        'total': len(deals),
        'stores': stores,
        'with_images': with_images,
        'image_percentage': (with_images / len(deals) * 100) if deals else 0,
        'with_prices': with_prices,
        'price_percentage': (with_prices / len(deals) * 100) if deals else 0,
        'with_comparison_prices': with_jfr + with_ord,
    }


def analyze_recipes(recipes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze recipes data.
    
    Args:
        recipes: List of recipe dictionaries
        
    Returns:
        Analysis results dictionary
    """
    # Count by source
    sources = {}
    for recipe in recipes:
        source = recipe.get('source', 'unknown')
        sources[source] = sources.get(source, 0) + 1
    
    # Count with ratings
    with_ratings = sum(1 for r in recipes if r.get('rating'))
    
    # Average rating
    ratings = [r['rating'] for r in recipes if r.get('rating')]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    # Count with images
    with_images = sum(1 for r in recipes if r.get('image'))
    
    # Count with nutrition
    with_nutrition = sum(1 for r in recipes if r.get('nutrition'))
    
    return {
        'total': len(recipes),
        'sources': sources,
        'with_ratings': with_ratings,
        'average_rating': round(avg_rating, 2),
        'with_images': with_images,
        'image_percentage': (with_images / len(recipes) * 100) if recipes else 0,
        'with_nutrition': with_nutrition,
        'nutrition_percentage': (with_nutrition / len(recipes) * 100) if recipes else 0,
    }


def analyze_matches(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze recipe matches data.
    
    Args:
        data: Recipe matches dictionary
        
    Returns:
        Analysis results dictionary
    """
    recipes = data.get('recipes', [])
    
    # Match percentage distribution
    match_ranges = {
        '0-20%': 0,
        '21-40%': 0,
        '41-60%': 0,
        '61-80%': 0,
        '81-100%': 0,
    }
    
    for recipe in recipes:
        pct = recipe.get('match_percentage', 0)
        if pct <= 20:
            match_ranges['0-20%'] += 1
        elif pct <= 40:
            match_ranges['21-40%'] += 1
        elif pct <= 60:
            match_ranges['41-60%'] += 1
        elif pct <= 80:
            match_ranges['61-80%'] += 1
        else:
            match_ranges['81-100%'] += 1
    
    # Average match percentage
    match_percentages = [r.get('match_percentage', 0) for r in recipes]
    avg_match = sum(match_percentages) / len(match_percentages) if match_percentages else 0
    
    # Count recipes with at least one match
    with_matches = sum(1 for r in recipes if r.get('matched_count', 0) > 0)
    
    # Data freshness
    last_updated = data.get('last_updated')
    if last_updated:
        updated_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
        age_hours = (datetime.now(timezone.utc) - updated_time).total_seconds() / 3600
        freshness = f"{age_hours:.1f} hours ago"
    else:
        freshness = "Unknown"
    
    return {
        'total_recipes': len(recipes),
        'with_matches': with_matches,
        'match_percentage_avg': round(avg_match, 1),
        'match_distribution': match_ranges,
        'last_updated': last_updated,
        'data_age': freshness,
        'total_deals': data.get('total_deals', 0),
    }


def main():
    """Main monitoring function."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 60)
    print("DATA QUALITY MONITOR")
    print("=" * 60)
    
    # File sizes
    files = ['deals.json', 'recipes.json', 'recipe_matches.json']
    print("\n📦 FILE SIZES")
    print("-" * 60)
    
    for filename in files:
        filepath = os.path.join(script_dir, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"  {filename:25} {format_size(size):>15}")
        else:
            print(f"  {filename:25} {'NOT FOUND':>15}")
    
    # Check if optimized version exists
    opt_file = os.path.join(script_dir, 'recipe_matches_optimized.json')
    if os.path.exists(opt_file):
        opt_size = os.path.getsize(opt_file)
        orig_size = os.path.getsize(os.path.join(script_dir, 'recipe_matches.json'))
        reduction = (1 - opt_size / orig_size) * 100
        print(f"\n  Optimized version available: {format_size(opt_size)} ({reduction:.1f}% smaller)")
    
    # Analyze deals
    deals_file = os.path.join(script_dir, 'deals.json')
    if os.path.exists(deals_file):
        with open(deals_file, 'r', encoding='utf-8') as f:
            deals = json.load(f)
        
        analysis = analyze_deals(deals)
        
        print("\n🛒 DEALS ANALYSIS")
        print("-" * 60)
        print(f"  Total deals: {analysis['total']}")
        print(f"  With images: {analysis['with_images']} ({analysis['image_percentage']:.1f}%)")
        print(f"  With prices: {analysis['with_prices']} ({analysis['price_percentage']:.1f}%)")
        print(f"  With comparison prices: {analysis['with_comparison_prices']}")
        
        print("\n  Deals per store:")
        for store, count in sorted(analysis['stores'].items(), key=lambda x: x[1], reverse=True):
            print(f"    {store:30} {count:>4} deals")
    
    # Analyze recipes
    recipes_file = os.path.join(script_dir, 'recipes.json')
    if os.path.exists(recipes_file):
        with open(recipes_file, 'r', encoding='utf-8') as f:
            recipes = json.load(f)
        
        analysis = analyze_recipes(recipes)
        
        print("\n🥘 RECIPES ANALYSIS")
        print("-" * 60)
        print(f"  Total recipes: {analysis['total']}")
        print(f"  With ratings: {analysis['with_ratings']}")
        print(f"  Average rating: {analysis['average_rating']:.2f}/5.0")
        print(f"  With images: {analysis['with_images']} ({analysis['image_percentage']:.1f}%)")
        print(f"  With nutrition: {analysis['with_nutrition']} ({analysis['nutrition_percentage']:.1f}%)")
        
        print("\n  Recipes per source:")
        for source, count in analysis['sources'].items():
            print(f"    {source:30} {count:>4} recipes")
    
    # Analyze matches
    matches_file = os.path.join(script_dir, 'recipe_matches.json')
    if os.path.exists(matches_file):
        with open(matches_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        analysis = analyze_matches(data)
        
        print("\n🎯 MATCH QUALITY")
        print("-" * 60)
        print(f"  Recipes analyzed: {analysis['total_recipes']}")
        print(f"  Recipes with matches: {analysis['with_matches']}")
        print(f"  Average match %: {analysis['match_percentage_avg']:.1f}%")
        print(f"  Data age: {analysis['data_age']}")
        
        print("\n  Match distribution:")
        for range_label, count in analysis['match_distribution'].items():
            pct = (count / analysis['total_recipes'] * 100) if analysis['total_recipes'] else 0
            bar = "█" * int(pct / 2)
            print(f"    {range_label:10} {count:>4} ({pct:>5.1f}%) {bar}")
    
    print("\n" + "=" * 60)
    print("✓ Monitoring complete")
    print("=" * 60)


if __name__ == '__main__':
    main()

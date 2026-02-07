#!/usr/bin/env python3
"""Optimize recipe_matches.json file size.

This script reduces the size of recipe_matches.json by:
1. Removing redundant data
2. Compressing repeated information
3. Creating a compact format

The frontend can be updated to handle the optimized format.
"""

import json
import os
import sys


def optimize_recipe_matches(input_file: str, output_file: str) -> None:
    """Optimize recipe_matches.json file.
    
    Reduces file size by:
    - Removing null/empty fields
    - Deduplicating store names
    - Shortening field names
    - Removing redundant nested data
    
    Args:
        input_file: Path to original recipe_matches.json
        output_file: Path to save optimized version
    """
    print(f"Loading {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    original_size = os.path.getsize(input_file)
    print(f"Original size: {original_size / 1024 / 1024:.2f} MB")
    
    # Build store index for deduplication
    stores = set()
    for recipe in data.get('recipes', []):
        for ing in recipe.get('matched_ingredients', []):
            if ing.get('deal_store'):
                stores.add(ing['deal_store'])
    
    store_to_id = {store: idx for idx, store in enumerate(sorted(stores))}
    id_to_store = list(sorted(stores))
    
    print(f"Found {len(stores)} unique stores")
    
    # Optimize recipes
    optimized_recipes = []
    for recipe in data.get('recipes', []):
        opt_recipe = {
            'name': recipe['name'],
            'url': recipe['url'],
        }
        
        # Only include non-null, non-empty fields
        optional_fields = [
            'image', 'category', 'source', 'time', 'servings', 
            'rating', 'reviews', 'nutrition'
        ]
        for field in optional_fields:
            if recipe.get(field):
                opt_recipe[field] = recipe[field]
        
        # Match statistics
        opt_recipe['total_ingredients'] = recipe['total_ingredients']
        opt_recipe['matched_count'] = recipe['matched_count']
        opt_recipe['match_percentage'] = recipe['match_percentage']
        
        # Optimize matched ingredients (biggest space saver)
        if recipe.get('matched_ingredients'):
            opt_matched = []
            for ing in recipe['matched_ingredients']:
                # Use store ID instead of name
                store_id = store_to_id.get(ing['deal_store'])
                
                opt_ing = {
                    'ingredient': ing['ingredient'],
                    'deal_name': ing['deal_name'],
                    'store_id': store_id,  # Use ID instead of string
                }
                
                # Only include non-null prices
                if ing.get('deal_price'):
                    opt_ing['price'] = ing['deal_price']
                if ing.get('ord_pris'):
                    opt_ing['ord_pris'] = ing['ord_pris']
                if ing.get('jfr_pris'):
                    opt_ing['jfr_pris'] = ing['jfr_pris']
                if ing.get('deal_unit'):
                    opt_ing['unit'] = ing['deal_unit']
                if ing.get('match_score'):
                    # Round to 2 decimals to save space
                    opt_ing['score'] = round(ing['match_score'], 2)
                
                opt_matched.append(opt_ing)
            
            opt_recipe['matched_ingredients'] = opt_matched
        
        # Keep unmatched ingredients (small)
        if recipe.get('unmatched_ingredients'):
            opt_recipe['unmatched_ingredients'] = recipe['unmatched_ingredients']
        
        optimized_recipes.append(opt_recipe)
    
    # Build optimized output
    optimized_data = {
        'last_updated': data.get('last_updated'),
        'total_deals': data.get('total_deals'),
        'total_recipes': data.get('total_recipes'),
        'stores': id_to_store,  # Store index
        'recipes': optimized_recipes,
    }
    
    # Save optimized version
    print(f"Saving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(optimized_data, f, ensure_ascii=False, separators=(',', ':'))
    
    optimized_size = os.path.getsize(output_file)
    print(f"Optimized size: {optimized_size / 1024 / 1024:.2f} MB")
    print(f"Reduction: {(1 - optimized_size / original_size) * 100:.1f}%")
    
    # Also create a pretty-printed version for debugging
    debug_file = output_file.replace('.json', '_debug.json')
    with open(debug_file, 'w', encoding='utf-8') as f:
        json.dump(optimized_data, f, ensure_ascii=False, indent=2)
    print(f"Debug version saved to {debug_file}")


def main():
    """Main entry point."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, 'recipe_matches.json')
    output_file = os.path.join(script_dir, 'recipe_matches_optimized.json')
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found")
        sys.exit(1)
    
    optimize_recipe_matches(input_file, output_file)
    print("\nOptimization complete!")
    print("\nTo use the optimized version:")
    print("1. Update frontend to handle 'store_id' and 'stores' array")
    print("2. Replace recipe_matches.json with recipe_matches_optimized.json")
    print("3. Update scrape workflow to run this optimization script")


if __name__ == '__main__':
    main()

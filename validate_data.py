#!/usr/bin/env python3
"""Data validation utilities for JSON files.

Validates that deals.json and recipes.json conform to expected schemas
and contain reasonable data.
"""

import json
import sys
from typing import Any


def validate_deal(deal: dict, index: int) -> list[str]:
    """Validate a single deal object.
    
    Args:
        deal: Deal dictionary to validate
        index: Position in deals array (for error reporting)
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Required fields
    if 'store' not in deal or not deal['store']:
        errors.append(f"Deal {index}: Missing 'store' field")
    if 'name' not in deal or not deal['name']:
        errors.append(f"Deal {index}: Missing 'name' field")
    
    # Optional but should be properly formatted if present
    if 'price' in deal and deal['price']:
        price = deal['price']
        if not isinstance(price, str):
            errors.append(f"Deal {index}: 'price' should be string, got {type(price)}")
    
    # Name length validation
    if deal.get('name'):
        name_len = len(deal['name'])
        if name_len < 2:
            errors.append(f"Deal {index}: name too short ({name_len} chars)")
        if name_len > 200:
            errors.append(f"Deal {index}: name too long ({name_len} chars)")
    
    # Image URL validation
    if deal.get('image'):
        img = deal['image']
        if not isinstance(img, str):
            errors.append(f"Deal {index}: 'image' should be string")
        elif not (img.startswith('http://') or img.startswith('https://')):
            errors.append(f"Deal {index}: 'image' should be http(s) URL")
    
    return errors


def validate_recipe(recipe: dict, index: int) -> list[str]:
    """Validate a single recipe object.
    
    Args:
        recipe: Recipe dictionary to validate
        index: Position in recipes array (for error reporting)
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Required fields
    required = ['name', 'url']
    for field in required:
        if field not in recipe or not recipe[field]:
            errors.append(f"Recipe {index}: Missing '{field}' field")
    
    # URL validation
    if recipe.get('url'):
        url = recipe['url']
        if not isinstance(url, str):
            errors.append(f"Recipe {index}: 'url' should be string")
        elif not (url.startswith('http://') or url.startswith('https://')):
            errors.append(f"Recipe {index}: 'url' should be http(s) URL")
    
    # simplified_ingredients should be a list
    if 'simplified_ingredients' in recipe:
        ings = recipe['simplified_ingredients']
        if not isinstance(ings, list):
            errors.append(f"Recipe {index}: 'simplified_ingredients' should be list")
        else:
            for i, ing in enumerate(ings):
                if not isinstance(ing, str):
                    errors.append(f"Recipe {index}: ingredient {i} should be string")
    
    # Numeric fields validation (can be string or number)
    numeric_fields = ['rating', 'reviews']
    for field in numeric_fields:
        if field in recipe and recipe[field] is not None:
            val = recipe[field]
            if not isinstance(val, (int, float)):
                errors.append(f"Recipe {index}: '{field}' should be numeric")
            elif val < 0:
                errors.append(f"Recipe {index}: '{field}' should be non-negative")
    
    # Servings can be string (e.g., "4", "2-4", "8 våfflor") or number
    if 'servings' in recipe and recipe['servings'] is not None:
        val = recipe['servings']
        if not isinstance(val, (str, int)):
            errors.append(f"Recipe {index}: 'servings' should be string or integer")
    
    return errors


def validate_recipe_match(match: dict, index: int) -> list[str]:
    """Validate a single recipe match object.
    
    Args:
        match: Recipe match dictionary to validate
        index: Position in matches array (for error reporting)
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Required fields from recipe
    required = ['name', 'url', 'total_ingredients', 'matched_count', 'match_percentage']
    for field in required:
        if field not in match:
            errors.append(f"Match {index}: Missing '{field}' field")
    
    # Validate match percentage
    if 'match_percentage' in match:
        pct = match['match_percentage']
        if not isinstance(pct, (int, float)):
            errors.append(f"Match {index}: 'match_percentage' should be numeric")
        elif pct < 0 or pct > 100:
            errors.append(f"Match {index}: 'match_percentage' out of range (got {pct})")
    
    # Validate counts
    total = match.get('total_ingredients', 0)
    matched = match.get('matched_count', 0)
    if matched > total:
        errors.append(f"Match {index}: matched_count ({matched}) > total_ingredients ({total})")
    
    # Validate ingredients arrays
    if 'matched_ingredients' in match:
        if not isinstance(match['matched_ingredients'], list):
            errors.append(f"Match {index}: 'matched_ingredients' should be list")
    
    if 'unmatched_ingredients' in match:
        if not isinstance(match['unmatched_ingredients'], list):
            errors.append(f"Match {index}: 'unmatched_ingredients' should be list")
    
    return errors


def validate_deals_file(filepath: str) -> tuple[bool, list[str]]:
    """Validate deals.json file.
    
    Args:
        filepath: Path to deals.json
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return False, [f"File not found: {filepath}"]
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except Exception as e:
        return False, [f"Error reading file: {e}"]
    
    if not isinstance(data, list):
        errors.append("Root element should be an array")
        return False, errors
    
    if len(data) == 0:
        errors.append("Warning: Deals array is empty")
    
    # Validate each deal
    for i, deal in enumerate(data):
        errors.extend(validate_deal(deal, i))
    
    # Check for duplicates
    seen = set()
    for i, deal in enumerate(data):
        key = (deal.get('store'), deal.get('name'))
        if key in seen:
            errors.append(f"Deal {i}: Duplicate (store={key[0]}, name={key[1]})")
        seen.add(key)
    
    return len(errors) == 0, errors


def validate_recipes_file(filepath: str) -> tuple[bool, list[str]]:
    """Validate recipes.json file.
    
    Args:
        filepath: Path to recipes.json
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return False, [f"File not found: {filepath}"]
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except Exception as e:
        return False, [f"Error reading file: {e}"]
    
    if not isinstance(data, list):
        errors.append("Root element should be an array")
        return False, errors
    
    if len(data) == 0:
        errors.append("Warning: Recipes array is empty")
    
    # Validate each recipe
    for i, recipe in enumerate(data):
        errors.extend(validate_recipe(recipe, i))
    
    return len(errors) == 0, errors


def validate_recipe_matches_file(filepath: str) -> tuple[bool, list[str]]:
    """Validate recipe_matches.json file.
    
    Args:
        filepath: Path to recipe_matches.json
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return False, [f"File not found: {filepath}"]
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except Exception as e:
        return False, [f"Error reading file: {e}"]
    
    if not isinstance(data, dict):
        errors.append("Root element should be an object")
        return False, errors
    
    # Check required top-level fields
    if 'recipes' not in data:
        errors.append("Missing 'recipes' field")
        return False, errors
    
    if not isinstance(data['recipes'], list):
        errors.append("'recipes' should be an array")
        return False, errors
    
    # Validate each match
    for i, match in enumerate(data['recipes']):
        errors.extend(validate_recipe_match(match, i))
    
    return len(errors) == 0, errors


def main():
    """Run validation on all data files."""
    import os
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    files_to_validate = [
        ('deals.json', validate_deals_file),
        ('recipes.json', validate_recipes_file),
        ('recipe_matches.json', validate_recipe_matches_file),
    ]
    
    all_valid = True
    
    for filename, validator in files_to_validate:
        filepath = os.path.join(script_dir, filename)
        print(f"\nValidating {filename}...")
        
        is_valid, errors = validator(filepath)
        
        if is_valid:
            print(f"  ✓ {filename} is valid")
        else:
            print(f"  ✗ {filename} has errors:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"    - {error}")
            if len(errors) > 10:
                print(f"    ... and {len(errors) - 10} more errors")
            all_valid = False
    
    if all_valid:
        print("\n✓ All files validated successfully")
        sys.exit(0)
    else:
        print("\n✗ Validation failed")
        sys.exit(1)


if __name__ == '__main__':
    main()

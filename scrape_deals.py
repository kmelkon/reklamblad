#!/usr/bin/env python3
"""Scrape current deals from ereklamblad.se and coop.se."""

import json
import os
import re
from playwright.sync_api import sync_playwright


def scrape_coop_se(page, store_name: str, coop_url: str) -> list[dict]:
    """Scrape deals from coop.se store page using their API."""
    print(f"\n=== Scraping {store_name} (coop.se) ===")
    print(f"URL: {coop_url}")

    offers_data = []

    def handle_response(response):
        if 'dke/offers' in response.url and 'json' in response.headers.get('content-type', ''):
            try:
                offers_data.extend(response.json())
            except Exception:
                pass

    page.on('response', handle_response)

    try:
        page.goto(coop_url, timeout=30000)
        page.wait_for_load_state('networkidle', timeout=20000)
    except Exception as e:
        print(f"  Navigation error: {e}")

    page.remove_listener('response', handle_response)

    products = []
    for offer in offers_data:
        content = offer.get('content', {})
        price_info = offer.get('priceInformation', {})

        name = content.get('title', '')
        brand = content.get('brand', '')
        if brand and brand.lower() not in name.lower():
            name = f"{name} ({brand})"

        # Build price string
        price_val = price_info.get('discountValue')
        min_amount = price_info.get('minimumAmount', 1)
        unit = price_info.get('unit', 'st')

        if price_val:
            if min_amount > 1:
                price = f"{min_amount} för {price_val}:-"
            else:
                price = f"{price_val}:-"
        else:
            price = None

        # Image URL
        image = content.get('imageUrl', '')
        if image and image.startswith('//'):
            image = 'https:' + image

        # Description and comparison price
        description = content.get('description', '')
        amount_info = content.get('amountInformation', '')
        if amount_info:
            description = f"{amount_info} {description}".strip()

        jfr_pris = content.get('comparativePriceText', '')

        if name:
            products.append({
                'store': store_name,
                'name': name.strip(),
                'price': price,
                'unit': unit if unit else None,
                'description': description if description else None,
                'ord_pris': None,
                'jfr_pris': jfr_pris if jfr_pris else None,
                'image': image if image else None,
            })

    print(f"  Found {len(products)} products via coop.se API")
    return products


def scrape_ereklamblad(page, store_name: str, url: str) -> list[dict]:
    """Scrape deals from ereklamblad.se using API interception."""
    print(f"\n=== Scraping {store_name} ===")
    print(f"URL: {url}")

    captured_responses = []

    def handle_response(response):
        """Capture API responses containing product data."""
        resp_url = response.url
        if any(pattern in resp_url for pattern in ['tjek.com', 'incito', 'paged-publications']):
            try:
                ct = response.headers.get('content-type', '')
                if 'json' in ct:
                    data = response.json()
                    captured_responses.append({
                        'url': resp_url,
                        'data': data
                    })
                    print(f"  Captured: {resp_url[:70]}...")
            except Exception:
                pass

    page.on('response', handle_response)

    try:
        page.goto(url, timeout=30000)
        page.wait_for_load_state('networkidle', timeout=20000)

        # Scroll through page to trigger lazy-loading of all sections
        scroll_height = page.evaluate('document.body.scrollHeight')
        viewport_height = 900
        scroll_pos = 0

        while scroll_pos < scroll_height:
            scroll_pos += viewport_height
            page.evaluate(f'window.scrollTo(0, {scroll_pos})')
            page.wait_for_timeout(500)
            scroll_height = page.evaluate('document.body.scrollHeight')

        page.wait_for_timeout(2000)
        page.wait_for_load_state('networkidle', timeout=10000)

    except Exception as e:
        print(f"  Navigation warning: {e}")

    products = extract_products_from_api(captured_responses, store_name)

    if products:
        print(f"  Found {len(products)} products via API")
        return products

    print("  API extraction failed, trying DOM fallback...")
    return scrape_dom_fallback(page, store_name)


def extract_products_from_api(responses: list, store_name: str) -> list[dict]:
    """Extract product info from captured API responses."""
    products = []

    for resp in responses:
        data = resp.get('data')
        if not data:
            continue

        url = resp.get('url', '')

        if 'incito' in url or 'generate_incito' in url:
            offers = find_incito_offers(data)
            for offer in offers:
                product = parse_offer_texts(offer.get('texts', []), store_name, offer.get('image'))
                if product:
                    products.append(product)

        if 'paged-publications' in url:
            page_products = parse_paged_publication(data, store_name)
            products.extend(page_products)

    return products


def find_incito_offers(obj, depth: int = 0) -> list[dict]:
    """Find offer groups in Incito JSON by looking for role='offer'.

    Returns list of dicts with 'texts' and 'image' keys.
    """
    if depth > 30:
        return []

    offers = []

    if isinstance(obj, dict):
        role = obj.get('role', '')

        if role == 'offer':
            texts = collect_texts(obj)
            if texts:
                image = find_background_image(obj)
                offers.append({'texts': texts, 'image': image})
        else:
            for key in ['child_views', 'children', 'root_view']:
                if key in obj:
                    offers.extend(find_incito_offers(obj[key], depth + 1))
            for v in obj.values():
                if isinstance(v, (dict, list)) and v not in [obj.get('child_views'), obj.get('children')]:
                    offers.extend(find_incito_offers(v, depth + 1))

    elif isinstance(obj, list):
        for item in obj:
            offers.extend(find_incito_offers(item, depth + 1))

    return offers


def find_background_image(obj, depth: int = 0) -> str | None:
    """Find first background_image URL in nested object."""
    if depth > 15:
        return None

    if isinstance(obj, dict):
        # Check for background_image with actual image URL (not section loader)
        bg = obj.get('background_image')
        if bg and isinstance(bg, str) and 'image-transformer-api' in bg:
            return bg

        # Search in child_views first (images are typically there)
        for key in ['child_views', 'children']:
            if key in obj:
                result = find_background_image(obj[key], depth + 1)
                if result:
                    return result

        # Then search other values
        for k, v in obj.items():
            if k not in ['child_views', 'children'] and isinstance(v, (dict, list)):
                result = find_background_image(v, depth + 1)
                if result:
                    return result

    elif isinstance(obj, list):
        for item in obj:
            result = find_background_image(item, depth + 1)
            if result:
                return result

    return None


def collect_texts(obj) -> list[str]:
    """Collect all text strings from a nested object."""
    texts = []

    if isinstance(obj, dict):
        if 'text' in obj and isinstance(obj['text'], str):
            texts.append(obj['text'])
        for v in obj.values():
            texts.extend(collect_texts(v))
    elif isinstance(obj, list):
        for item in obj:
            texts.extend(collect_texts(item))

    return texts


def parse_offer_texts(texts: list[str], store_name: str, image: str | None = None) -> dict | None:
    """Parse offer text list into structured product data."""
    if not texts:
        return None

    name = texts[0] if texts else None

    if name and re.match(r'^\d+\s*/\s*\d+$', name):
        name = texts[1] if len(texts) > 1 else None

    if not name or len(name) < 2:
        return None

    price = None
    unit = None
    description_parts = []
    ord_pris = None
    jfr_pris = None

    for t in texts[1:]:
        if re.match(r'^\d+:-$', t):
            price = t
        elif t in ['/kg', '/st', '/liter']:
            unit = t
        elif re.match(r'^\d+\s+för$', t):
            unit = t
        elif '|' in t:
            description_parts.append(t)
            ord_match = re.search(r'Ord\.pris\s+([\d:,.-]+)\s*kr', t)
            if ord_match:
                ord_pris = ord_match.group(1)
            jfr_match = re.search(r'Jfr pris\s+([\d:,.-]+)', t)
            if jfr_match:
                jfr_pris = jfr_match.group(1)
        elif 'Ord.pris' in t or 'Jfr pris' in t:
            description_parts.append(t)
            ord_match = re.search(r'Ord\.pris\s+([\d:,.-]+)\s*kr', t)
            if ord_match:
                ord_pris = ord_match.group(1)
            jfr_match = re.search(r'Jfr pris\s+([\d:,.-]+)', t)
            if jfr_match:
                jfr_pris = jfr_match.group(1)

    return {
        'store': store_name,
        'name': name.strip(),
        'price': price,
        'unit': unit,
        'description': ' | '.join(description_parts) if description_parts else None,
        'ord_pris': ord_pris,
        'jfr_pris': jfr_pris,
        'image': image,
    }


def parse_paged_publication(data, store_name: str) -> list[dict]:
    """Parse paged publication format (used by Coop)."""
    products = []

    if isinstance(data, dict):
        hotspots = data.get('hotspots', [])
        for hs in hotspots:
            offer = hs.get('offer', {})
            if offer:
                name = offer.get('heading', '')
                price = offer.get('pricing', {}).get('price')
                pre_price = offer.get('pricing', {}).get('pre_price')
                unit = offer.get('quantity', {}).get('unit', {}).get('symbol', '')

                # Try to find image in offer or hotspot
                image = None
                for img_key in ['image', 'images', 'photo']:
                    if img_key in offer and offer[img_key]:
                        img = offer[img_key]
                        if isinstance(img, str):
                            image = img
                        elif isinstance(img, list) and img:
                            first = img[0]
                            if isinstance(first, str):
                                image = first
                            elif isinstance(first, dict):
                                image = first.get('url') or first.get('src')
                        elif isinstance(img, dict):
                            image = img.get('url') or img.get('src')
                        break

                if name:
                    products.append({
                        'store': store_name,
                        'name': name.strip(),
                        'price': f"{price}:-" if price else None,
                        'unit': unit if unit else None,
                        'description': f"Ord.pris {pre_price}:-" if pre_price else None,
                        'image': image,
                    })

    return products


def build_offer_image_map(page, chain_url: str) -> dict:
    """Build offer_id -> image URL mapping from chain inventory view."""
    offer_images = {}
    inventory_url = f"{chain_url.rstrip('/')}?publication=inventory"

    try:
        page.goto(inventory_url, timeout=30000)
        page.wait_for_load_state('networkidle', timeout=20000)
        page.wait_for_timeout(1000)

        # Scroll to load all products
        for i in range(25):
            page.evaluate(f'window.scrollTo(0, {i * 500})')
            page.wait_for_timeout(100)

        links = page.query_selector_all('a[href*="offer="]')
        for link in links:
            href = link.get_attribute('href')
            img = link.query_selector('img')

            if href and img:
                offer_match = re.search(r'offer=([a-zA-Z0-9_-]+)', href)
                if offer_match:
                    offer_id = offer_match.group(1)
                    img_src = img.get_attribute('src')
                    if img_src:
                        offer_images[offer_id] = img_src
    except Exception as e:
        print(f"  Error building image map: {e}")

    return offer_images


def scrape_store_specific(page, store_name: str, store_url: str, offer_images: dict = None) -> list[dict]:
    """Scrape a specific store by finding its active publication."""
    print(f"\n=== Scraping {store_name} (store-specific) ===")
    print(f"Store URL: {store_url}")

    try:
        page.goto(store_url, timeout=30000)
        page.wait_for_load_state('networkidle', timeout=15000)

        # Find active publication link (contains ?publication= and current store's location)
        links = page.query_selector_all('a[href*="publication="]')
        pub_url = None
        for link in links:
            href = link.get_attribute('href')
            if href and 'publication=' in href and 'inventory' not in href:
                pub_url = href
                break

        if not pub_url:
            print("  No active publication found")
            return []

        full_url = f"https://ereklamblad.se{pub_url}" if pub_url.startswith('/') else pub_url
        print(f"  Found publication: {full_url}")

        # If we have offer images, use paged-publications API for better matching
        if offer_images:
            products = scrape_publication_with_images(page, store_name, full_url, offer_images)
            if products:
                return products

        return scrape_ereklamblad(page, store_name, full_url)

    except Exception as e:
        print(f"  Error: {e}")
        return []


def scrape_publication_with_images(page, store_name: str, pub_url: str, offer_images: dict) -> list[dict]:
    """Scrape publication using paged-publications API and match with inventory images."""
    import urllib.request

    # Extract publication ID from URL
    pub_match = re.search(r'publication=([a-zA-Z0-9_-]+)', pub_url)
    if not pub_match:
        return []

    pub_id = pub_match.group(1)
    print(f"  Using paged-publications API with image matching...")

    products = []
    seen_offers = set()

    # Fetch all pages
    for page_num in range(1, 20):
        try:
            api_url = f'https://publication-viewer.tjek.com/api/paged-publications/{pub_id}/{page_num}'
            req = urllib.request.Request(api_url, headers={'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())

                for hs in data.get('hotspots', []):
                    offer = hs.get('offer', {})
                    offer_id = offer.get('id')
                    name = offer.get('name', '')

                    if not name or offer_id in seen_offers:
                        continue
                    seen_offers.add(offer_id)

                    # Parse name and price from "Product Name, SEK 99" format
                    price = None
                    clean_name = name
                    price_match = re.search(r',\s*(?:SEK\s*)?(\d+(?:[,.]\d+)?)\s*$', name)
                    if price_match:
                        price = f"{price_match.group(1).replace(',', '.')}:-"
                        clean_name = name[:price_match.start()].strip()
                    elif name.endswith(', Medlemspris'):
                        clean_name = name.replace(', Medlemspris', '').strip()

                    # Get image from offer_images map
                    image = offer_images.get(offer_id)

                    products.append({
                        'store': store_name,
                        'name': clean_name,
                        'price': price,
                        'unit': None,
                        'description': None,
                        'ord_pris': None,
                        'jfr_pris': None,
                        'image': image,
                    })
        except urllib.error.HTTPError:
            break  # No more pages
        except Exception:
            continue

    matched = sum(1 for p in products if p.get('image'))
    print(f"  Found {len(products)} products, {matched} with images ({100*matched//len(products) if products else 0}%)")
    return products


def scrape_inventory_view(page, store_name: str, base_url: str) -> list[dict]:
    """Scrape inventory view which has structured product data (Willys, ICA Maxi, ICA Kvantum)."""
    print(f"\n=== Scraping {store_name} (inventory view) ===")

    products = []
    inventory_url = f"{base_url.rstrip('/')}?publication=inventory"
    print(f"URL: {inventory_url}")

    try:
        page.goto(inventory_url, timeout=30000)
        page.wait_for_load_state('networkidle', timeout=20000)
        page.wait_for_timeout(2000)

        # Scroll to load all products
        for i in range(25):
            page.evaluate(f'window.scrollTo(0, {i * 500})')
            page.wait_for_timeout(150)
        page.wait_for_timeout(1000)

        links = page.query_selector_all('a[href*="offer="]')
        print(f"  Found {len(links)} product links")

        for link in links:
            try:
                text = link.inner_text()
                lines = [l.strip().replace('\xa0', ' ') for l in text.split('\n') if l.strip()]

                if not lines:
                    continue

                name = lines[0]
                if len(name) < 2 or len(name) > 100:
                    continue

                # Parse price and details
                price = None
                description = None
                jfr_pris = None
                ord_pris = None

                for line in lines[1:]:
                    # Price line: "19,90 kr" or "Medlemspris 79 kr"
                    price_match = re.search(r'(\d+[,.]?\d*)\s*kr$', line)
                    if price_match and not price:
                        price_val = price_match.group(1).replace(',', '.')
                        price = f"{price_val}:-"

                    # Details line with Jämförpris
                    if 'Jämförpris' in line or 'jämförpris' in line:
                        description = line
                        jfr_match = re.search(r'[Jj]ämförpris\s*([\d:,.]+)\s*kr', line)
                        if jfr_match:
                            jfr_pris = jfr_match.group(1)

                    # Lägsta 30-dgrspris (use as ord_pris for comparison)
                    if '30-dgr' in line.lower() or 'lägsta' in line.lower():
                        if not description:
                            description = line
                        else:
                            description += ' | ' + line
                        ord_match = re.search(r'[Ll]ägsta\s+30-dgrspris\s*([\d:,.-]+)\s*kr', line)
                        if ord_match:
                            ord_pris = ord_match.group(1)

                    # Weight/unit info: "1 kg • 19,90 kr/kg"
                    if '•' in line and 'kr/' in line:
                        if not description:
                            description = line
                        # Extract jfr_pris from "19,90 kr/kg"
                        unit_match = re.search(r'([\d,]+)\s*kr/(kg|st|liter)', line)
                        if unit_match and not jfr_pris:
                            jfr_pris = unit_match.group(1)

                # Try to get image from link
                image = None
                try:
                    img = link.query_selector('img')
                    if img:
                        image = img.get_attribute('src')
                except Exception:
                    pass

                products.append({
                    'store': store_name,
                    'name': name.strip(),
                    'price': price,
                    'unit': None,
                    'description': description,
                    'ord_pris': ord_pris,
                    'jfr_pris': jfr_pris,
                    'image': image,
                })
            except Exception:
                continue

    except Exception as e:
        print(f"  Error scraping inventory: {e}")

    print(f"  Found {len(products)} products via inventory")
    return products


def scrape_dom_fallback(page, store_name: str) -> list[dict]:
    """Fallback: parse product data from visible DOM content."""
    products = []

    try:
        content = page.inner_text('body')
        lines = [l.strip() for l in content.split('\n') if l.strip()]

        for line in lines:
            match = re.match(r'^(.+?),\s*SEK\s*([\d.]+)$', line)
            if match:
                name, price = match.groups()
                if len(name) > 2 and len(name) < 100:
                    products.append({
                        'store': store_name,
                        'name': name.strip(),
                        'price': f"{price}:-",
                        'unit': None,
                        'description': None,
                        'ord_pris': None,
                        'jfr_pris': None,
                        'image': None,
                    })
                continue

            match = re.match(r'^(.+?),\s*Medlemspris$', line)
            if match:
                name = match.group(1)
                if len(name) > 2 and len(name) < 100:
                    products.append({
                        'store': store_name,
                        'name': name.strip(),
                        'price': 'Medlemspris',
                        'unit': None,
                        'description': None,
                        'ord_pris': None,
                        'jfr_pris': None,
                        'image': None,
                    })
                continue

            match = re.match(r'^(.+?)\s+(\d+)[:\-]+\s*$', line)
            if match:
                name, price = match.groups()
                if len(name) > 2 and len(name) < 100:
                    products.append({
                        'store': store_name,
                        'name': name.strip(),
                        'price': f"{price}:-",
                        'unit': None,
                        'description': None,
                        'ord_pris': None,
                        'jfr_pris': None,
                        'image': None,
                    })

    except Exception as e:
        print(f"  DOM fallback error: {e}")

    print(f"  Found {len(products)} products via DOM")
    return products


def main():
    # National chain pages
    stores = [
        ('ICA Supermarket', 'https://ereklamblad.se/ICA-Supermarket/'),
        ('ICA Nära', 'https://ereklamblad.se/ICA-Nara/'),
        ('ICA Maxi', 'https://ereklamblad.se/ICA-Maxi-Stormarknad/'),
        ('ICA Kvantum', 'https://ereklamblad.se/ICA-Kvantum/'),
        ('Stora Coop', 'https://ereklamblad.se/Stora-Coop/'),
        ('Coop', 'https://ereklamblad.se/Coop/'),
        ('Willys', 'https://ereklamblad.se/Willys/'),
        # Specific stores (ICA via ereklamblad, Coop via coop.se for better data)
        ('ICA Globen', 'https://ereklamblad.se/ICA-Supermarket/butiker/d4d20iz'),
        ('Stora Coop Västberga', 'https://www.coop.se/butiker-erbjudanden/stora-coop/stora-coop-vastberga/'),
        ('Coop Fruängen', 'https://www.coop.se/butiker-erbjudanden/coop/coop-fruangen/'),
    ]

    all_products = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale='sv-SE',
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = context.new_page()

        # Stores that use inventory view for better price data
        inventory_stores = {'Willys', 'ICA Maxi', 'ICA Kvantum', 'Stora Coop', 'Coop'}

        for store_name, url in stores:
            try:
                if 'coop.se/butiker-erbjudanden' in url:
                    # Use coop.se API for store-specific Coop stores
                    products = scrape_coop_se(page, store_name, url)
                elif '/butiker/' in url:
                    # ereklamblad store-specific pages
                    products = scrape_store_specific(page, store_name, url)
                elif store_name in inventory_stores:
                    products = scrape_inventory_view(page, store_name, url)
                else:
                    products = scrape_ereklamblad(page, store_name, url)
                all_products.extend(products)
            except Exception as e:
                print(f"Error scraping {store_name}: {e}")

        browser.close()

    # Deduplicate by name
    seen = set()
    unique_products = []
    for p in all_products:
        key = (p['store'], p['name'])
        if key not in seen:
            seen.add(key)
            unique_products.append(p)

    print("\n" + "=" * 60)
    print("DEALS FOUND")
    print("=" * 60)

    for product in unique_products:
        price_str = f" - {product['price']}" if product.get('price') else ""
        unit_str = f" {product['unit']}" if product.get('unit') else ""
        print(f"[{product['store']}] {product['name']}{price_str}{unit_str}")

    print(f"\nTotal: {len(unique_products)} unique products")

    # Save to JSON (relative path for repo)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, 'deals.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_products, f, ensure_ascii=False, indent=2)
    print(f"Saved to: {output_file}")


if __name__ == '__main__':
    main()

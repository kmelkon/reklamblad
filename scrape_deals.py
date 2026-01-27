#!/usr/bin/env python3
"""Scrape current deals from ereklamblad.se (ICA Supermarket & Stora Coop)."""

import json
import os
import re
from playwright.sync_api import sync_playwright


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
            for offer_texts in offers:
                product = parse_offer_texts(offer_texts, store_name)
                if product:
                    products.append(product)

        if 'paged-publications' in url:
            page_products = parse_paged_publication(data, store_name)
            products.extend(page_products)

    return products


def find_incito_offers(obj, depth: int = 0) -> list[list[str]]:
    """Find offer groups in Incito JSON by looking for role='offer'."""
    if depth > 30:
        return []

    offers = []

    if isinstance(obj, dict):
        role = obj.get('role', '')

        if role == 'offer':
            texts = collect_texts(obj)
            if texts:
                offers.append(texts)
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


def parse_offer_texts(texts: list[str], store_name: str) -> dict | None:
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

                if name:
                    products.append({
                        'store': store_name,
                        'name': name.strip(),
                        'price': f"{price}:-" if price else None,
                        'unit': unit if unit else None,
                        'description': f"Ord.pris {pre_price}:-" if pre_price else None,
                    })

    return products


def scrape_willys_inventory(page, store_name: str, base_url: str) -> list[dict]:
    """Scrape Willys inventory view which has structured product data."""
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
                        if 'Medlemspris' in line:
                            price = 'Medlemspris'
                        else:
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

                products.append({
                    'store': store_name,
                    'name': name.strip(),
                    'price': price,
                    'unit': None,
                    'description': description,
                    'ord_pris': ord_pris,
                    'jfr_pris': jfr_pris,
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
                    })

    except Exception as e:
        print(f"  DOM fallback error: {e}")

    print(f"  Found {len(products)} products via DOM")
    return products


def main():
    stores = [
        ('ICA Supermarket', 'https://ereklamblad.se/ICA-Supermarket/'),
        ('ICA Nära', 'https://ereklamblad.se/ICA-Nara/'),
        ('ICA Maxi', 'https://ereklamblad.se/ICA-Maxi-Stormarknad/'),
        ('ICA Kvantum', 'https://ereklamblad.se/ICA-Kvantum/'),
        ('Stora Coop', 'https://ereklamblad.se/Stora-Coop/'),
        ('Coop', 'https://ereklamblad.se/Coop/'),
        ('Willys', 'https://ereklamblad.se/Willys/'),
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

        for store_name, url in stores:
            try:
                if store_name == 'Willys':
                    products = scrape_willys_inventory(page, store_name, url)
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

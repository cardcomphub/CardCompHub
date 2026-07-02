import os
import re
import sys
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from supabase import create_client, Client

# 🔐 WORKER AUTHENTICATION
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, SCRAPER_API_KEY]):
    raise ValueError("❌ Execution failed: Missing required environment variables in execution space.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_ebay_via_proxy(search_query, player_name):
    print(f"📡 Routing proxy query for: '{search_query}'...")
    encoded_query = search_query.replace(" ", "+")
    ebay_url = f"https://www.ebay.com/sch/i.html?_nkw={encoded_query}&LH_Complete=1&LH_Sold=1"

    # 🇺🇸 GUARDRAIL 1: Force a US IP address to prevent foreign currency conversion glitches
    proxy_params = {'api_key': SCRAPER_API_KEY, 'url': ebay_url, 'country_code': 'us'}
    try:
        response = requests.get('http://api.scraperapi.com', params=proxy_params, timeout=30)
        if response.status_code != 200: return [], None

        soup = BeautifulSoup(response.text, 'html.parser')
        listings = soup.find_all(class_=lambda x: x and ('s-item' in x or 's-card' in x))

        parsed_comps = []
        first_discovered_image = None
        player_last_name = player_name.split()[-1].lower() if player_name else ""

        for item in listings:
            title_el = item.find(class_=lambda x: x and 'title' in x.lower())
            price_el = item.find(class_=lambda x: x and 'price' in x.lower())

            if not title_el or not price_el: continue

            title = title_el.text.strip()
            price_text = price_el.text.strip().upper()

            if "SHOP ON EBAY" in title.upper() or not title: continue
            if player_last_name and player_last_name not in title.lower(): continue

            # 🛡️ GUARDRAIL 2: Hard-skip any foreign currency text strings that slip through
            foreign_currencies = ["MXN", "C $", "AU $", "EUR", "£", "GBP", "CAD"]
            if any(foreign in price_text for foreign in foreign_currencies):
                continue

            # 📸 Image Extraction
            image_el = item.find('img')
            listing_specific_img = None
            if image_el:
                listing_specific_img = image_el.get('data-src') or image_el.get('src') or image_el.get('data-delayed-src')
                if listing_specific_img and ("gif" in listing_specific_img or "placeholder" in listing_specific_img):
                    listing_specific_img = None
            if listing_specific_img and not first_discovered_image:
                first_discovered_image = listing_specific_img

            # 💰 Price Parsing
            clean_price = price_text.split('TO')[0]
            price_match = re.search(r'\d+(?:\.\d{2})?', clean_price.replace(',', ''))

            # 🗓️ THE DATE FIX: Target the exact eBay HTML class for sold dates
            parsed_date = datetime.now(timezone.utc).isoformat()
            positive_span = item.find("span", class_=lambda x: x and 'POSITIVE' in x.upper())
            date_text = positive_span.text.strip() if positive_span else item.text

            # Regex captures: Sold Apr 16, 2026 OR Sold Jun 2
            date_match = re.search(r'(?:Sold|Ended)\s*([A-Za-z]{3})\s+(\d{1,2})(?:,\s*(\d{4}))?', date_text, re.IGNORECASE)
            if date_match:
                month = date_match.group(1)
                day = date_match.group(2)
                year = date_match.group(3) if date_match.group(3) else str(datetime.now(timezone.utc).year)
                try: 
                    parsed_date = datetime.strptime(f"{month} {day} {year}", "%b %d %Y").replace(tzinfo=timezone.utc).isoformat()
                except Exception: 
                    pass

            if price_match:
                parsed_comps.append({
                    "title": title, 
                    "price": float(price_match.group()),
                    "date": parsed_date,
                    "listing_image": listing_specific_img
                })
        return parsed_comps, first_discovered_image
    except Exception as e:
        print(f"❌ Proxy pipeline network anomaly: {e}")
        return [], None

# 🛡️ THE NEW SMART CLASSIFIER (Strict Un-split Phrase Matching)
def classify_comp(ebay_title, card_year, brand, series, player_name, card_number, variants):
    title_lower = ebay_title.lower()
    
    # Replace non-alphanumeric with spaces, then collapse multiple spaces into one for perfect phrase matching
    title_alphanum = re.sub(r'[^a-z0-9\s]', ' ', title_lower)
    title_alphanum = re.sub(r'\s+', ' ', title_alphanum).strip()

    # 🧱 GENERATE THE 4 UN-SPLIT EXACT TOKENS
    year_token = str(card_year).strip()
    
    brand_token = re.sub(r'[^a-z0-9\s]', ' ', brand.lower())
    brand_token = re.sub(r'\s+', ' ', brand_token).strip()
    
    series_token = re.sub(r'[^a-z0-9\s]', ' ', series.lower())
    series_token = re.sub(r'\s+', ' ', series_token).strip()
    
    card_num_token = str(card_number).lower().replace("#", "").strip()

    # 1. 🗓️ STRICT YEAR ENFORCEMENT
    if year_token not in title_alphanum:
        return None

    # 2. 👤 PLAYER NAME ENFORCEMENT
    player_parts = re.sub(r'[^a-z0-9\s]', ' ', player_name.lower()).split()
    if not all(part in title_alphanum for part in player_parts): 
        return None

    # 3. 🔢 SMART CARD NUMBER MATCHING
    has_card_num = False
    if len(card_num_token) > 1:
        # Handles complex variants (e.g. 'AK-17' matches 'AK17' or 'AK 17') by stripping spaces/hyphens
        stripped_title = re.sub(r'[\s\-]', '', title_lower)
        stripped_num = re.sub(r'[\s\-]', '', card_num_token)
        has_card_num = stripped_num in stripped_title
    elif len(card_num_token) == 1:
        # Uses word boundaries for single digits so card #9 doesn't trigger on a "PSA 9" string
        has_card_num = bool(re.search(rf'\b{card_num_token}\b', title_alphanum))

    # 4. 🗂️ STRICT SERIES PHRASE MATCHING (Un-split Token)
    has_series = False
    if series_token and series_token != "base":
        # Requires the exact unbroken phrase (e.g., "rookie recruits") to be in the title
        has_series = series_token in title_alphanum
    else:
        has_series = True

    if not (has_card_num or has_series): 
        return None

    # 5. Check for specific parallel variants FIRST
    base_variant_id = None
    matched_variant_id = None

    # Sort variants so longer names evaluate before short names
    sorted_variants = sorted(variants, key=lambda v: len(v['variant_name']), reverse=True)

    for variant in sorted_variants:
        v_name = variant['variant_name'].lower().strip()
        if v_name == "base":
            base_variant_id = variant['id']
            continue

        variant_clean = re.sub(r'\(.*?\)', '', v_name).strip().replace("refractors", "refractor")
        variant_parts = variant_clean.split()

        if all(v_part in title_alphanum for v_part in variant_parts):
            matched_variant_id = variant['id']
            break

    # 6. FALLBACK TO BASE
    if matched_variant_id:
        return matched_variant_id
    elif base_variant_id:
        trash_keywords = ["lot", "bulk", "set", "auto", "signed", "autograph", "patch", "jersey", "relic", "1/1", "one of one"]
        parallel_keywords = ["pandora", "gold", "prizm", "refractor", "silver", "holo", "mosaic", "parallel", "tie-dye", "geometric", "ruby", "sapphire", "x-fractor"]

        if not any(kw in title_alphanum for kw in parallel_keywords + trash_keywords):
            return base_variant_id

    return None

def run_pipeline(target_year, target_brand, target_series):
    print(f"🚀 Running sync for Matrix Target: {target_year} {target_brand} {target_series}...")
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    today_comps_response = supabase.table("price_comps") \
        .select("variant_id") \
        .gte("created_at", f"{today_str}T00:00:00+00:00") \
        .execute()

    variants_updated_today = {item['variant_id'] for item in (today_comps_response.data or [])}

    set_response = supabase.table("card_sets").select("id").eq("

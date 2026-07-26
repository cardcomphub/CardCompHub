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
            
            # HTML parsing for player name locally
            if player_last_name and player_last_name not in title.lower(): continue

            # 📸 Image Extraction
            image_el = item.find('img')
            listing_specific_img = None
            if image_el:
                listing_specific_img = image_el.get('data-src') or image_el.get('src') or image_el.get('data-delayed-src')
                if listing_specific_img and ("gif" in listing_specific_img or "placeholder" in listing_specific_img):
                    listing_specific_img = None
            
            # Lock in the very first valid image found for the master card record
            if listing_specific_img and not first_discovered_image:
                first_discovered_image = listing_specific_img

            # 💰 NEW Price Parsing: Anchor strictly to the dollar sign
            price_match = re.search(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', price_text)

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
                clean_price = float(price_match.group(1).replace(',', ''))
                
                parsed_comps.append({
                    "title": title, 
                    "price": clean_price,
                    "date": parsed_date,
                    "listing_image": listing_specific_img
                })
                
        return parsed_comps, first_discovered_image
    except Exception as e:
        print(f"❌ Proxy pipeline network anomaly: {e}")
        return [], None


# 🛡️ THE SMART CLASSIFIER 
def classify_comp(ebay_title, card_year, brand, series, player_name, card_number, variants, is_extreme_length):
    title_lower = ebay_title.lower()
    
    title_alphanum = re.sub(r'[^a-z0-9\s]', ' ', title_lower)
    title_alphanum = re.sub(r'\s+', ' ', title_alphanum).strip()
    title_words = set(title_alphanum.split())

    hobby_aliases = {
        "autograph": ["autograph", "autographs", "auto", "autos"],
        "autographs": ["autograph", "autographs", "auto", "autos"],
        "autographed": ["autograph", "autographs", "auto", "autos"],
        "auto": ["autograph", "autographs", "auto", "autos"],
        "autos": ["autograph", "autographs", "auto", "autos"],
        "material": ["materials"],
        "materials": ["material"]
    }

    def words_present(required_words, pool):
        for w in required_words:
            allowed_forms = hobby_aliases.get(w, [w])
            if not any(form in pool for form in allowed_forms):
                return False
        return True

    # 1. 👤 EXACT PLAYER NAME ENFORCEMENT
    player_parts = re.sub(r'[^a-z0-9\s]', ' ', player_name.lower()).split()
    if not all(part in title_words for part in player_parts): 
        return None

    # 🎯 2. STRICT YEAR ENFORCEMENT
    found_years = re.findall(r'\b(202[0-9])\b', title_lower)
    if found_years and str(card_year) not in found_years:
        print(f"  ⏭️ YEAR MISMATCH SKIPPED: Listing year {found_years} doesn't match matrix target {card_year}")
        return None

    # 3. 🗂️ STRICT SERIES MATCHING 
    if not is_extreme_length:
        series_clean = re.sub(r'[^a-z0-9\s]', ' ', series.lower())
        series_clean = re.sub(r'\s+', ' ', series_clean).strip()
        
        if series_clean and series_clean != "base":
            series_words = series_clean.split()
            if not words_present(series_words, title_words):
                return None

    # 4. 🔍 VARIANT SEARCH
    matched_variant_id = None
    sorted_variants = sorted(variants, key=lambda v: len(v['variant_name']), reverse=True)

    for variant in sorted_variants:
        v_name = variant['variant_name'].lower().strip()
        variant_clean = re.sub(r'\(.*?\)', '', v_name).strip().replace("refractors", "refractor")
        variant_parts = variant_clean.split()

        if v_name in ["base", "standard", "raw", "unnumbered"]:
            continue

        if words_present(variant_parts, title_words):
            matched_variant_id = variant['id']
            break

    # 5. 🟢 ROUTING & FALLBACK
    if matched_variant_id:
        return matched_variant_id
        
    if variants:
        base_match = next((v['id'] for v in variants if v['variant_name'].lower().strip() == 'base'), None)
        if base_match:
            return base_match
        
        return sorted_variants[-1]['id']

    return None

def run_pipeline(target_year, target_brand, target_series):
    print(f"🚀 Running sync for Matrix Target: {target_year} {target_brand} {target_series}...")
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    today_comps_response = supabase.table("price_comps") \
        .select("variant_id") \
        .gte("created_at", f"{today_str}T00:00:00+00:00") \
        .execute()

    variants_updated_today = {item['variant_id'] for item in (today_comps_response.data or [])}

    set_response = supabase.table("card_sets").select("id").eq("year", target_year).eq("brand", target_brand).eq("series", target_series).execute()

    if not set_response.data:
        print("❌ Set not found in database. Exiting matrix job.")
        return

    target_set_id = set_response.data[0]['id']

    response = supabase.table("base_cards").select(
        "id, player_name, card_number, image_url, slug, card_variants(id, variant_name, variant_category)"
    ).eq("set_id", target_set_id).execute()
    cards = response.data

    for card in cards:
        clean_player_name = re.sub(r"^['\"]|['\"]$", "", card['player_name']).strip()

        # ⚖️ Calculate Theoretical Length
        max_variant_len = max([len(v['variant_name']) for v in card['card_variants']]) if card['card_variants'] else 0
        theoretical_length = len(f"{target_year} {target_brand} {target_series} {clean_player_name}") + max_variant_len + 1
        
        is_extreme_length = theoretical_length > 80

        # ✂️ DYNAMIC URL GENERATION
        if is_extreme_length:
            search_term = f"{target_year} {target_brand} {target_series}"
        else:
            search_term = f"{target_year} {target_brand} {target_series} {clean_player_name}"

        raw_comps, live_card_image = fetch_ebay_via_proxy(search_term, card['player_name'])

        if not raw_comps:
            time.sleep(1)
            continue

        # 📸 MASTER IMAGE UPDATE LOGIC
        if live_card_image:
            current_image = card.get('image_url') or ""
            # Update only if empty or if it contains a placeholder indicator
            if not current_image or "placeholder" in current_image.lower() or "default" in current_image.lower():
                try:
                    # Updates the 'image_url' column in the 'base_cards' table specifically
                    supabase.table("base_cards").update({"image_url": live_card_image}).eq("id", card["id"]).execute()
                    print(f"  📸 Updated master card image for {clean_player_name}")
                    card['image_url'] = live_card_image 
                except Exception as img_err:
                    print(f"  ⚠️ Failed to update master image in Supabase: {img_err}")

        price_entries = []
        for comp in raw_comps:
            if comp['price'] > 10000: continue

            matched_variant_id = classify_comp(
                ebay_title=comp['title'],
                card_year=target_year,
                brand=target_brand,
                series=target_series,
                player_name=clean_player_name,
                card_number=card['card_number'],
                variants=card['card_variants'],
                is_extreme_length=is_extreme_length 
            )

            if not matched_variant_id: continue

            grade = "RAW"
            if "psa 10" in comp['title'].lower(): grade = "PSA 10"
            elif "psa 9" in comp['title'].lower(): grade = "PSA 9"

            price_entries.append({
                "variant_id": matched_variant_id,
                "sale_price": comp['price'],
                "sale_date": comp['date'],
                "grade": grade,
                "sale_image_url": comp['listing_image'] or None
            })

        if price_entries:
            variant_groups = {}
            for entry in price_entries:
                vid = entry['variant_id']
                if vid not in variant_groups: variant_groups[vid] = []
                variant_groups[vid].append(entry)

            for vid, entries in variant_groups.items():
                if vid in variants_updated_today: continue

                try:
                    existing_comps = supabase.table("price_comps").select("sale_price, sale_date").eq("variant_id", vid).execute()
                    existing_data = existing_comps.data or []
                    existing_fingerprints = set(f"{float(c['sale_price'])}_{c['sale_date']}" for c in existing_data)

                    # 📈 Server-side Dynamic Median Evaluation
                    historical_prices = sorted([float(c['sale_price']) for c in existing_data])
                    median_price = 0
                    if historical_prices:
                        mid = len(historical_prices) // 2
                        median_price = historical_prices[mid] if len(historical_prices) % 2 != 0 else (historical_prices[mid - 1] + historical_prices[mid]) / 2.0

                    max_allowed_price = median_price * 5 if median_price > 0 else float('inf')

                    unique_new_entries = []
                    for entry in entries:
                        sale_price = float(entry['sale_price'])
                        fingerprint = f"{sale_price}_{entry['sale_date']}"
                        
                        if fingerprint not in existing_fingerprints:
                            unique_new_entries.append(entry)
                            existing_fingerprints.add(fingerprint)

                    if unique_new_entries:
                        supabase.table("price_comps").insert(unique_new_entries[:10]).execute()
                        print(f"✅ SUCCESS: Added {len(unique_new_entries)} new sales for {clean_player_name}")
                    else:
                        print(f"⏩ SKIP: No new unique sales found for {clean_player_name}.")

                except Exception as db_write_error:
                    print(f"⚠️ Database write skipped: {db_write_error}")

        time.sleep(1)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("❌ Error: Missing matrix arguments. Usage: python update_by_set.py <year> <brand> <series>")
        sys.exit(1)

    target_year = sys.argv[1]
    target_brand = sys.argv[2]
    target_series = sys.argv[3]

    run_pipeline(target_year, target_brand, target_series)

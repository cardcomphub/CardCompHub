import os
import re
import sys
import time
import hashlib
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
    clean_query = search_query.replace("'", "").replace("’", "")
    print(f"📡 Routing proxy query for: '{clean_query}'...")
    
    encoded_query = clean_query.replace(" ", "+")
    ebay_url = f"https://www.ebay.com/sch/i.html?_nkw={encoded_query}&LH_Complete=1&LH_Sold=1"

    # 🇺🇸 THE FIX: Added 'premium': 'true' to use Residential Proxies and bypass the eBay Login Wall
    proxy_params = {
        'api_key': SCRAPER_API_KEY, 
        'url': ebay_url, 
        'country_code': 'us', 
        'device_type': 'desktop',
        'premium': 'true' 
    }
    
    # 🎯 Anti-Captcha / Anti-Login Wall Auto-Retry Loop
    for attempt in range(3):
        try:
            response = requests.get('http://api.scraperapi.com', params=proxy_params, timeout=60)
            if response.status_code != 200: 
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            listings = soup.find_all(lambda tag: tag.name in ['li', 'div'] and tag.get('class') and any('s-item' in c or 's-card' in c for c in tag.get('class')))

            # Intercept empty pages and check for eBay bot-blockers or login walls
            if not listings:
                html_lower = response.text.lower()
                if "captcha" in html_lower or "verify you are a human" in html_lower or "signin.ebay.com" in html_lower or "sign in to view" in html_lower:
                    print(f"  🛑 eBay Login/Captcha Wall hit. Retrying with fresh Residential IP ({attempt+1}/3)...")
                    time.sleep(3)
                    continue
                else:
                    break # Genuine 0 results found on eBay

            parsed_comps = []
            first_discovered_image = None
            
            player_parts = re.sub(r'[^a-z0-9\s]', ' ', player_name.lower()).split()
            suffixes = {"jr", "sr", "ii", "iii", "iv", "v"}
            core_parts = [p for p in player_parts if p not in suffixes]
            player_last_name = core_parts[-1] if core_parts else ""

            for item in listings:
                title_el = item.find(class_=lambda c: c and 'title' in str(c).lower() and 'subtitle' not in str(c).lower())
                price_el = item.find(class_=lambda c: c and 'price' in str(c).lower())

                if not title_el or not price_el: continue

                title = title_el.get_text(separator=" ").strip()
                price_text = price_el.get_text(separator=" ").strip().upper()

                if "SHOP ON EBAY" in title.upper() or not title: continue
                if player_last_name and player_last_name not in title.lower(): continue

                # 🆔 THE DEDUPLICATION FIX
                ebay_id = None
                for a_tag in item.find_all('a', href=True):
                    href = a_tag['href']
                    id_match = re.search(r'/itm/(?:[^?]+/)?(\d{11,14})', href)
                    if not id_match:
                        id_match = re.search(r'item(?:id)?=(\d{11,14})', href)
                    if id_match:
                        ebay_id = id_match.group(1)
                        break
                
                # Synthetic Hash Fallback
                if not ebay_id:
                    raw_str = f"{title}_{price_text}"
                    ebay_id = "SYN-" + hashlib.md5(raw_str.encode('utf-8')).hexdigest()[:12]

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
                price_match = re.search(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', price_text)

                # 🗓️ Date Parsing safely scans the entire text block
                parsed_date = datetime.now(timezone.utc).isoformat()
                date_match = re.search(r'(?:Sold|Ended)\s*([A-Za-z]{3})\s+(\d{1,2})(?:,\s*(\d{4}))?', item.get_text(separator=" "), re.IGNORECASE)
                
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
                        "listing_image": listing_specific_img,
                        "ebay_id": ebay_id
                    })
                    
            return parsed_comps, first_discovered_image
        except Exception as e:
            print(f"❌ Proxy pipeline network anomaly: {e}")
            
    return [], None


# 🛡️ THE SMART CLASSIFIER 
def classify_comp(ebay_title, card_year, brand, series, player_name, card_number, variants, is_extreme_length):
    title_lower = ebay_title.lower().replace("'", "").replace("’", "")
    
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
    suffixes = {"jr", "sr", "ii", "iii", "iv", "v"}
    core_player_parts = [p for p in player_parts if p not in suffixes]
    
    if not all(part in title_words for part in core_player_parts): 
        return None

    # 2. 🎯 STRICT YEAR ENFORCEMENT
    found_years = re.findall(r'\b(202[0-9])\b', title_lower)
    if found_years and str(card_year) not in found_years:
        return None

    # 3. 🗂️ STRICT SERIES MATCHING (Apostrophe safe)
    if not is_extreme_length:
        series_clean = series.lower().replace("'", "").replace("’", "")
        series_clean = re.sub(r'[^a-z0-9\s]', ' ', series_clean).strip()
        
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

def run_pipeline(target_year, target_brand, target_series, target_sport):
    print(f"🚀 Running sync for Matrix Target: {target_year} {target_brand} {target_series} ({target_sport})...")
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    today_comps_response = supabase.table("price_comps") \
        .select("variant_id") \
        .gte("created_at", f"{today_str}T00:00:00+00:00") \
        .execute()

    variants_updated_today = {item['variant_id'] for item in (today_comps_response.data or [])}

    set_response = supabase.table("card_sets").select("id")\
        .eq("year", target_year)\
        .eq("brand", target_brand)\
        .eq("series", target_series)\
        .eq("sport", target_sport)\
        .execute()

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

        if is_extreme_length:
            search_term = f"{target_year} {target_brand} {target_series}"
        else:
            search_term = f"{target_year} {target_brand} {target_series} {clean_player_name}"

        raw_comps, live_card_image = fetch_ebay_via_proxy(search_term, card['player_name'])

        if not raw_comps:
            print(f"  ⚠️ No raw comps scraped for {clean_player_name}.")
            time.sleep(1)
            continue

        if live_card_image:
            current_image = card.get('image_url') or ""
            if not current_image or "placeholder" in current_image.lower() or "default" in current_image.lower():
                try:
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
                "sale_image_url": comp['listing_image'] or None,
                "ebay_id": comp['ebay_id']
            })

        if not price_entries:
            print(f"  ⏭️ {len(raw_comps)} listings scraped, but 0 passed the strict classifier for {clean_player_name}.")

        if price_entries:
            variant_groups = {}
            for entry in price_entries:
                vid = entry['variant_id']
                if vid not in variant_groups: variant_groups[vid] = []
                variant_groups[vid].append(entry)

            for vid, entries in variant_groups.items():
                if vid in variants_updated_today: continue

                try:
                    existing_comps = supabase.table("price_comps").select("sale_price, sale_date, ebay_id").eq("variant_id", vid).execute()
                    existing_data = existing_comps.data or []
                    
                    existing_ids = set(c['ebay_id'] for c in existing_data if c.get('ebay_id'))
                    existing_fingerprints = set(f"{float(c['sale_price'])}_{c['sale_date']}" for c in existing_data)

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
                        
                        if entry['ebay_id'] not in existing_ids and fingerprint not in existing_fingerprints:
                            unique_new_entries.append(entry)
                            existing_ids.add(entry['ebay_id'])
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
    if len(sys.argv) < 5:
        print("❌ Error: Missing matrix arguments. Usage: python update_by_set.py <year> <brand> <series> <sport>")
        sys.exit(1)

    target_year = sys.argv[1]
    target_brand = sys.argv[2]
    target_series = sys.argv[3]
    target_sport = sys.argv[4]

    run_pipeline(target_year, target_brand, target_series, target_sport)

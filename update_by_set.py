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

def parse_supabase_timestamp(ts_string):
    if not ts_string:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    clean_ts = ts_string.replace('Z', '+00:00')
    if '.' in clean_ts:
        base_part, tz_part = clean_ts.split('.', 1)
        if '+' in tz_part: tz_offset = '+' + tz_part.split('+', 1)[1]
        elif '-' in tz_part: tz_offset = '-' + tz_part.split('-', 1)[1]
        else: tz_offset = '+00:00'
        clean_ts = f"{base_part}{tz_offset}"
    return datetime.fromisoformat(clean_ts)

def fetch_ebay_via_proxy(search_query, player_name):
    print(f"📡 Routing proxy query for: '{search_query}'...")
    encoded_query = search_query.replace(" ", "+")
    ebay_url = f"https://www.ebay.com/sch/i.html?_nkw={encoded_query}&LH_Complete=1&LH_Sold=1"
    
    proxy_params = {'api_key': SCRAPER_API_KEY, 'url': ebay_url}
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
            image_el = item.find('img')
            
            if title_el and price_el:
                title = title_el.text.strip()
                price_text = price_el.text.strip()
                
                if "Shop on eBay" in title or not title: continue
                if player_last_name and player_last_name not in title.lower(): continue
                
                listing_specific_img = None
                if image_el:
                    listing_specific_img = image_el.get('data-src') or image_el.get('src') or image_el.get('data-delayed-src')
                    if listing_specific_img and ("gif" in listing_specific_img or "placeholder" in listing_specific_img):
                        listing_specific_img = None
                if listing_specific_img and not first_discovered_image:
                    first_discovered_image = listing_specific_img
                
                clean_price = price_text.split('to')[0]
                price_match = re.search(r'\d+(?:\.\d{2})?', clean_price.replace(',', ''))
                
                # 🛠️ FIX 1: NEW DATE PARSER
                parsed_date = datetime.now(timezone.utc).isoformat()
                date_match = re.search(r'(?:Sold|Ended).*?([A-Za-z]{3})\s+(\d+)(?:,\s+(\d{4}))?', item.text, re.IGNORECASE)
                
                if date_match:
                    month = date_match.group(1)
                    day = date_match.group(2)
                    # If eBay hides the year, default to the current year
                    year = date_match.group(3) if date_match.group(3) else str(datetime.now(timezone.utc).year)
                    try: 
                        parsed_date = datetime.strptime(f"{month} {day} {year}", "%b %d %Y").replace(tzinfo=timezone.utc).isoformat()
                    except: 
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

# 🛡️ THE NEW STRICT VERIFICATION GATE
def verify_strict_comp(ebay_title, card_year, brand, series, player_name, card_number, variant_name):
    title_clean = ebay_title.lower()

    if str(card_year) not in title_clean: return False

    num_pattern = rf'(?:^|\s|#){re.escape(str(card_number))}(?:\s|$|,)'
    if not re.search(num_pattern, title_clean): return False

    core_series = series.lower().replace("panini", "").replace("topps", "").replace("bowman", "").strip().split()[0]
    if core_series and core_series not in title_clean: return False

    player_parts = player_name.lower().replace("'", "").replace(".", "").split()
    title_normalized = title_clean.replace("'", "").replace(".", "")
    if not all(part in title_normalized for part in player_parts): return False

    variant_clean = re.sub(r'\(.*?\)', '', variant_name).lower().strip()
    
    if variant_clean != "base":
        variant_parts = variant_clean.split()
        if not all(v_part in title_clean for v_part in variant_parts): return False
    else:
        trash_keywords = ["lot", "bulk", "set", "auto", "signed", "autograph", "patch", "jersey", "relic", "1/1", "one of one"]
        parallel_keywords = ["pandora", "gold", "prizm", "refractor", "silver", "holo", "mosaic", "parallel", "tie-dye"]
        if any(kw in title_clean for kw in trash_keywords + parallel_keywords): return False

    return True

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
        variants = card['card_variants']
        clean_player_name = re.sub(r"^['\"]|['\"]$", "", card['player_name']).strip()

        for variant in variants:
            variant_id = variant['id']
            variant_name = variant['variant_name']
            
            if variant_id in variants_updated_today: continue

            if variant_name.lower() == 'base':
                search_term = f"{target_year} {target_brand} {target_series} {clean_player_name} #{card['card_number']}"
            else:
                clean_variant_string = re.sub(r'\(.*?\)', '', variant_name).strip()
                search_term = f"{target_year} {target_brand} {target_series} {clean_player_name} #{card['card_number']} {clean_variant_string}"

            raw_comps, live_card_image = fetch_ebay_via_proxy(search_term, card['player_name'])
            
            if not raw_comps:
                time.sleep(1)
                continue
                
            if live_card_image and ("placeholder" in card.get('image_url', '') or not card.get('image_url')):
                supabase.table("base_cards").update({"image_url": live_card_image}).eq("id", card["id"]).execute()
                card['image_url'] = live_card_image 

            price_entries = []
            for comp in raw_comps:
                if comp['price'] > 10000: continue

                is_valid = verify_strict_comp(
                    ebay_title=comp['title'],
                    card_year=target_year,
                    brand=target_brand,
                    series=target_series,
                    player_name=clean_player_name,
                    card_number=card['card_number'],
                    variant_name=variant_name
                )

                if not is_valid: continue

                grade = "Raw"
                if "psa 10" in comp['title'].lower(): grade = "PSA 10"
                elif "psa 9" in comp['title'].lower(): grade = "PSA 9"
                
                price_entries.append({
                    "variant_id": variant_id,
                    "sale_price": comp['price'],
                    "sale_date": comp['date'],
                    "grade": grade,
                    # 🛠️ FIX 2: IMAGE FALLBACK FIX (Uses None instead of master image)
                    "sale_image_url": comp['listing_image'] or None
                })

            # 🛠️ FIX 3: DEDUPLICATION GATE
            if price_entries:
                try:
                    # Fetch existing comps for this variant
                    existing_comps = supabase.table("price_comps").select("sale_price, sale_date").eq("variant_id", variant_id).execute()
                    
                    # Create a set of unique fingerprints (Price + Date)
                    existing_fingerprints = set(f"{float(c['sale_price'])}_{c['sale_date']}" for c in (existing_comps.data or []))
                    
                    unique_new_entries = []
                    for entry in price_entries:
                        fingerprint = f"{float(entry['sale_price'])}_{entry['sale_date']}"
                        if fingerprint not in existing_fingerprints:
                            unique_new_entries.append(entry)
                            existing_fingerprints.add(fingerprint) # Add to set to prevent duplicates within the same batch
                    
                    if unique_new_entries:
                        supabase.table("price_comps").insert(unique_new_entries[:10]).execute()
                        print(f"✅ SUCCESS: Added {len(unique_new_entries)} new sales for {clean_player_name} #{card['card_number']} ({variant_name})")
                    else:
                        print(f"⏩ SKIP: No new unique sales found for {clean_player_name} ({variant_name}).")
                        
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

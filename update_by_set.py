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
            
            if not title_el or not price_el: continue
                
            title = title_el.text.strip()
            price_text = price_el.text.strip()
            
            if "Shop on eBay" in title or not title: continue
            if player_last_name and player_last_name not in title.lower(): continue
            
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
            clean_price = price_text.split('to')[0]
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

# 🛡️ THE NEW SMART CLASSIFIER (Handles Parallels & Base Fallback)
def classify_comp(ebay_title, card_year, brand, series, player_name, card_number, variants):
    title_clean = ebay_title.lower().replace("'", "").replace(".", "")
    
    # 1. Player Name MUST match
    player_parts = player_name.lower().replace("'", "").replace(".", "").split()
    if not all(part in title_clean for part in player_parts): return None
    
    # 2. MATCH FORGIVENESS: Must match EITHER card number OR core series
    # (Fixes the $1,750 Emeka sale that omitted the "GG-16")
    clean_card_num = str(card_number).lower().replace("#", "").strip()
    has_card_num = clean_card_num and clean_card_num in title_clean.replace("#", "")
    
    core_series = series.lower().replace("panini", "").replace("topps", "").replace("bowman", "").strip().split()[0]
    has_series = core_series and core_series in title_clean
    
    if not (has_card_num or has_series): return None

    # 3. Check for specific parallel variants FIRST
    base_variant_id = None
    matched_variant_id = None
    
    # Sort variants so longer names (like "Gold Refractor") evaluate before "Refractor"
    sorted_variants = sorted(variants, key=lambda v: len(v['variant_name']), reverse=True)
    
    for variant in sorted_variants:
        v_name = variant['variant_name'].lower().strip()
        if v_name == "base":
            base_variant_id = variant['id']
            continue
            
        # Standardize Topps plurals (e.g., "Refractors" -> "Refractor")
        variant_clean = re.sub(r'\(.*?\)', '', v_name).strip().replace("refractors", "refractor")
        variant_parts = variant_clean.split()
        
        # If ALL parts of the variant name are in the title, assign it to that parallel
        if all(v_part in title_clean for v_part in variant_parts):
            matched_variant_id = variant['id']
            break
            
    # 4. FALLBACK TO BASE
    if matched_variant_id:
        return matched_variant_id
    elif base_variant_id:
        # If it didn't match a specific parallel, ensure it isn't carrying trash keywords before applying to Base
        trash_keywords = ["lot", "bulk", "set", "auto", "signed", "autograph", "patch", "jersey", "relic", "1/1", "one of one"]
        parallel_keywords = ["pandora", "gold", "prizm", "refractor", "silver", "holo", "mosaic", "parallel", "tie-dye", "geometric", "ruby", "sapphire", "x-fractor"]
        
        if not any(kw in title_clean for kw in parallel_keywords + trash_keywords):
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

        # 🎯 NEW BATCH QUERY: We only hit the ScraperAPI ONCE per base card now.
        search_term = f"{target_year} {target_brand} {target_series} {clean_player_name}"
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

            # Send the comp to the classifier to figure out which bucket it belongs in
            matched_variant_id = classify_comp(
                ebay_title=comp['title'],
                card_year=target_year,
                brand=target_brand,
                series=target_series,
                player_name=clean_player_name,
                card_number=card['card_number'],
                variants=card['card_variants']
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

        # 🎯 NEW GROUPED DEDUPLICATION: Push all variants at once
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
                    existing_fingerprints = set(f"{float(c['sale_price'])}_{c['sale_date']}" for c in (existing_comps.data or []))
                    
                    unique_new_entries = []
                    for entry in entries:
                        fingerprint = f"{float(entry['sale_price'])}_{entry['sale_date']}"
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

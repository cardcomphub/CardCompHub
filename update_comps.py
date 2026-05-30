import os
import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from supabase import create_client, Client

# 🔐 WORKER AUTHENTICATION: Loaded dynamically via runtime execution environment containers
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, SCRAPER_API_KEY]):
    raise ValueError("❌ Execution failed: Missing required environment variables in execution space.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def find_matching_variant(title_lower, variants):
    """Intelligently matches an eBay title to the correct database variant ID by breaking down keyword tokens."""
    sorted_variants = sorted(variants, key=lambda x: 0 if x['variant_name'].lower() == 'base' else 1, reverse=True)
    
    for v in sorted_variants:
        v_name = v['variant_name'].lower()
        if v_name == 'base':
            continue
            
        keyword_root = re.sub(r'\s*\(.*?\)', '', v_name).strip()
        is_match = False
        
        if keyword_root in title_lower:
            is_match = True
        elif "stat line" in keyword_root and "stat" in title_lower:
            is_match = True
        elif "jersey number" in keyword_root and ("jersey" in title_lower or "patch" in title_lower or "serial" in title_lower):
            is_match = True
        elif "downtown" in keyword_root and "downtown" in title_lower:
            is_match = True
        elif "autograph" in keyword_root and ("auto" in title_lower or "sig" in title_lower or "ink" in title_lower or "signed" in title_lower):
            is_match = True
        elif "memorabilia" in keyword_root and ("jersey" in title_lower or "patch" in title_lower or "relic" in title_lower or "material" in title_lower):
            is_match = True

        serial_match = re.search(r'\(.*?\/(\d+)\)', v_name)
        if is_match and serial_match:
            serial_limit = serial_match.group(1)
            if serial_limit not in title_lower and f"/{serial_limit}" not in title_lower:
                is_match = False 

        if is_match:
            return v['id']
            
    base_var = next((v for v in variants if v['variant_name'].lower() == 'base'), None)
    return base_var['id'] if base_var else None


def fetch_ebay_via_proxy(search_query, player_name):
    """Routes queries through proxy networks, extracting prices, true dates, and unique item listing images."""
    print(f"📡 Routing proxy query for: '{search_query}'...")
    
    encoded_query = search_query.replace(" ", "+")
    ebay_url = f"https://www.ebay.com/sch/i.html?_nkw={encoded_query}&LH_Complete=1&LH_Sold=1"
    
    proxy_params = {
        'api_key': SCRAPER_API_KEY,
        'url': ebay_url
      }
    
    try:
        response = requests.get('http://api.scraperapi.com', params=proxy_params, timeout=30)
        if response.status_code != 200:
            print(f"❌ Proxy node issue. Status code: {response.status_code}")
            return [], None
            
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
                
                if "Shop on eBay" in title or not title:
                    continue
                if player_last_name and player_last_name not in title.lower():
                    continue
                
                listing_specific_img = None
                if image_el:
                    listing_specific_img = image_el.get('data-src') or image_el.get('src') or image_el.get('data-delayed-src')
                    if listing_specific_img and ("gif" in listing_specific_img or "placeholder" in listing_specific_img):
                        listing_specific_img = None
                
                if listing_specific_img and not first_discovered_image:
                    first_discovered_image = listing_specific_img
                
                clean_price = price_text.split('to')[0]
                price_match = re.search(r'\d+(?:\.\d{2})?', clean_price.replace(',', ''))
                
                parsed_date = datetime.now(timezone.utc).isoformat()
                date_match = re.search(r'(?:Sold|Ended)\s+([A-Za-z]{3})\s+(\d+),\s+(\d{4})', item.text, re.IGNORECASE)
                
                if date_match:
                    month, day, year = date_match.group(1), date_match.group(2), date_match.group(3)
                    try:
                        parsed_date = datetime.strptime(f"{month} {day} {year}", "%b %d %Y").replace(tzinfo=timezone.utc).isoformat()
                    except:
                        pass

                if price_match:
                    price_float = float(price_match.group())
                    parsed_comps.append({
                        "title": title, 
                        "price": price_float,
                        "date": parsed_date,
                        "listing_image": listing_specific_img
                    })
                        
        return parsed_comps, first_discovered_image
    except Exception as e:
        print(f"❌ Proxy pipeline network anomaly: {e}")
        return [], None


def run_pipeline():
    print("🚀 Running data stream sync loop...")
    
    # 🌟 1. SCHEMA UPDATE: Included 'last_updated' in the select parameters tree
    response = supabase.table("base_cards").select(
        "id, player_name, card_number, image_url, slug, last_updated, card_sets(year, brand, series), card_variants(id, variant_name, variant_category)"
    ).execute()
    cards = response.data

    # Isolate current calendar day key token in UTC formatting (YYYY-MM-DD)
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    for card in cards:
        set_info = card['card_sets']
        variants = card['card_variants']
        last_updated_raw = card.get('last_updated')

        # 🌟 2. THE API DATE GATE: Skip extraction loops if a sweep already finished today
        if last_updated_raw:
            last_updated_date = last_updated_raw.split('T')[0]
            if last_updated_date == today_str:
                print(f"⏩ SKIP (#{card['card_number']}) was already swept today ({today_str}). Protecting API limits.")
                continue

        search_term = f"{set_info['year']} {set_info['brand']} {set_info['series']} {card['player_name']} #{card['card_number']}"
        raw_comps, live_card_image = fetch_ebay_via_proxy(search_term, card['player_name'])
        
        # If no comps are active right now, write back today's date anyway to stop infinite retries on the same day
        if not raw_comps:
            now_iso = datetime.now(timezone.utc).isoformat()
            supabase.table("base_cards").update({"last_updated": now_iso}).eq("id", card["id"]).execute()
            continue
            
        if live_card_image and ("placeholder" in card.get('image_url', '') or not card.get('image_url')):
            supabase.table("base_cards").update({"image_url": live_card_image}).eq("id", card["id"]).execute()

        base_var = next((v for v in variants if v['variant_name'].lower() == 'base'), None)
        base_variant_id = base_var['id'] if base_var else None

        price_entries = []
        for comp in raw_comps:
            if comp['price'] > 10000:
                continue

            title_lower = comp['title'].lower()
            matched_variant_id = find_matching_variant(title_lower, variants)
            
            if matched_variant_id:
                if matched_variant_id == base_variant_id:
                    trash_keywords = [
                        "lot", "bulk", "set of", "bundle", "complete set", 
                        "auto", "signed", "autograph", "patch", "jersey", "relic",
                        "1/1", "one of one", "printing plate"
                    ]
                    if any(word in title_lower for word in trash_keywords):
                        continue
                
                grade = "Raw"
                if "psa 10" in title_lower: grade = "PSA 10"
                elif "psa 9" in title_lower: grade = "PSA 9"
                
                price_entries.append({
                    "variant_id": matched_variant_id,
                    "sale_price": comp['price'],
                    "sale_date": comp['date'],
                    "grade": grade,
                    "sale_image_url": comp['listing_image'] or card['image_url']
                })

        if price_entries:
            try:
                supabase.table("price_comps").insert(price_entries[:10]).execute()
                print(f"📊 Successfully updated database with localized layout metrics rows for {card['player_name']}!")
            except Exception as db_write_error:
                print(f"⚠️ Database write skipped dynamically for {card['player_name']}: {db_write_error}")

        # 🌟 3. TIMESTAMP RECORD LOCK: Safely write back a completion log stamp to base_cards
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            supabase.table("base_cards").update({"last_updated": now_iso}).eq("id", card["id"]).execute()
        except Exception as timestamp_error:
            print(f"⚠️ Failed to update completion timestamp loop for {card['player_name']}: {timestamp_error}")
            
        time.sleep(1)

if __name__ == "__main__":
    run_pipeline()
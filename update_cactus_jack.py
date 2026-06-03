import os
import re
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
    raise ValueError("❌ Execution failed: Missing required environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_ebay_via_proxy(search_query, player_name):
    """Routes explicit queries through proxy networks, extracting raw pricing metrics."""
    print(f"📡 Routing proxy query for: '{search_query}'...")
    encoded_query = search_query.replace(" ", "+")
    ebay_url = f"https://www.ebay.com/sch/i.html?_nkw={encoded_query}&LH_Complete=1&LH_Sold=1"
    
    try:
        response = requests.get('http://api.scraperapi.com', params={'api_key': SCRAPER_API_KEY, 'url': ebay_url}, timeout=30)
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
                if "Shop on eBay" in title or not title:
                    continue
                if player_last_name and player_last_name not in title.lower():
                    continue
                
                listing_specific_img = None
                if image_el:
                    listing_specific_img = image_el.get('data-src') or image_el.get('src') or image_el.get('data-delayed-src')
                
                if listing_specific_img and not first_discovered_image:
                    first_discovered_image = listing_specific_img
                
                price_match = re.search(r'\d+(?:\.\d{2})?', price_el.text.replace(',', ''))
                parsed_date = datetime.now(timezone.utc).isoformat()
                date_match = re.search(r'(?:Sold|Ended)\s+([A-Za-z]{3})\s+(\d+),\s+(\d{4})', item.text, re.IGNORECASE)
                
                if date_match:
                    try:
                        parsed_date = datetime.strptime(f"{date_match.group(1)} {date_match.group(2)} {date_match.group(3)}", "%b %d %Y").replace(tzinfo=timezone.utc).isoformat()
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


def run_pipeline():
    print("🌵 Starting PAGINATED Cactus Jack Sync Pipeline...")

    raw_cards = []
    start_row = 0
    page_size = 1000

    # 🚀 FIX: Loop query ranges to break past Supabase max_rows restrictions
    while True:
        print(f"🔄 Loading records {start_row} to {start_row + page_size}...")
        response = supabase.table("base_cards").select(
            "id, player_name, card_number, image_url, slug, card_sets(year, brand, series), card_variants(id, variant_name, variant_category)"
        ).range(start_row, start_row + page_size - 1).execute()
        
        page_data = response.data or []
        raw_cards.extend(page_data)
        
        # If we get back fewer records than the page size, we've hit the absolute bottom of the table
        if len(page_data) < page_size:
            break
            
        start_row += page_size
    
    # 🎯 TARGETED FILTER: Isolate entries belonging to the Cactus Jack series run
    cards = [
        c for c in raw_cards 
        if c.get('card_sets') and 'cactus jack' in str(c['card_sets'].get('series', '')).lower()
    ]
    
    print(f"📦 Successfully isolated {len(cards)} total Cactus Jack cards out of {len(raw_cards)} master rows fetched.")

    if not cards:
        print("⚠️ No Cactus Jack cards matched the filter logic.")
        return

    for card in cards:
        set_info = card['card_sets']
        variants = card['card_variants']
        clean_player_name = re.sub(r"^['\"]|['\"]$", "", card['player_name']).strip()

        for variant in variants:
            variant_id = variant['id']
            variant_name = variant['variant_name']

            if variant_name.lower() == 'base':
                search_term = f"{set_info['year']} {set_info['brand']} {set_info['series']} {clean_player_name} #{card['card_number']}"
            else:
                clean_variant_string = re.sub(r'\(.*?\)', '', variant_name).strip()
                search_term = f"{set_info['year']} {set_info['brand']} {set_info['series']} {clean_player_name} #{card['card_number']} {clean_variant_string}"

            raw_comps, live_card_image = fetch_ebay_via_proxy(search_term, card['player_name'])
            
            if not raw_comps:
                time.sleep(1)
                continue
                
            if live_card_image and ("placeholder" in card.get('image_url', '') or not card.get('image_url')):
                supabase.table("base_cards").update({"image_url": live_card_image}).eq("id", card["id"]).execute()
                card['image_url'] = live_card_image 

            price_entries = []
            for comp in raw_comps:
                if comp['price'] > 10000:
                    continue

                title_lower = comp['title'].lower()

                if variant_name.lower() == 'base':
                    trash_keywords = ["lot", "bulk", "set of", "bundle", "complete set", "auto", "signed", "autograph", "patch", "jersey", "relic", "1/1", "one of one", "printing plate"]
                    if any(word in title_lower for word in trash_keywords):
                        continue
                else:
                    clean_token = re.sub(r'\(.*?\)', '', variant_name).lower().strip()
                    if "autograph" in clean_token and not any(x in title_lower for x in ["auto", "sig", "ink", "signed", "autograph"]):
                        continue
                    elif "memorabilia" in clean_token and not any(x in title_lower for x in ["jersey", "patch", "relic", "material"]):
                        continue
                    elif clean_token not in title_lower and "autograph" not in clean_token and "memorabilia" not in clean_token:
                        continue

                grade = "Raw"
                if "psa 10" in title_lower: grade = "PSA 10"
                elif "psa 9" in title_lower: grade = "PSA 9"
                
                price_entries.append({
                    "variant_id": variant_id,
                    "sale_price": comp['price'],
                    "sale_date": comp['date'],
                    "grade": grade,
                    "sale_image_url": comp['listing_image'] or card['image_url']
                })

            if price_entries:
                try:
                    supabase.table("price_comps").insert(price_entries[:10]).execute()
                    print(f"✅ SUCCESS: Updated {clean_player_name} #{card['card_number']} ({variant_name})!")
                except Exception as db_write_error:
                    print(f"⚠️ Database write skipped: {db_write_error}")
                
            time.sleep(1)

if __name__ == "__main__":
    run_pipeline()
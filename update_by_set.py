import os
import re
import sys
import asyncio
import aiohttp
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

# ==========================================
# 1. ASYNCHRONOUS NETWORK FETCHER
# ==========================================
async def fetch_ebay_via_proxy(session, search_query, player_name):
    """Routes explicit queries through proxy networks concurrently."""
    print(f"📡 Routing proxy query for: '{search_query}'...")
    encoded_query = search_query.replace(" ", "+")
    ebay_url = f"https://www.ebay.com/sch/i.html?_nkw={encoded_query}&LH_Complete=1&LH_Sold=1"
    
    try:
        # Replaced requests.get with aiohttp session.get
        async with session.get('http://api.scraperapi.com', params={'api_key': SCRAPER_API_KEY, 'url': ebay_url}, timeout=30) as response:
            if response.status != 200:
                print(f"❌ Proxy node issue. Status code: {response.status}")
                return [], None
            
            # await the text response without blocking the thread
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
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


# ==========================================
# 2. ASYNCHRONOUS VARIANT PROCESSOR
# ==========================================
async def process_variant(session, sem, card, variant, set_info):
    """Processes a single variant card concurrently."""
    # The semaphore acts as a traffic light so we don't bombard the API
    async with sem:
        clean_player_name = re.sub(r"^['\"]|['\"]$", "", card['player_name']).strip()
        variant_id = variant['id']
        variant_name = variant['variant_name']
        last_scraped = variant.get('last_scraped_at')

        # 🛡️ THE ROADBLOCK: Skip variant if already scraped within 24h
        if last_scraped:
            last_scraped_dt = datetime.fromisoformat(last_scraped.replace('Z', '+00:00'))
            time_delta = datetime.now(timezone.utc) - last_scraped_dt
            if time_delta.total_seconds() < 86400:
                print(f"⏭️ Skipping {clean_player_name} ({variant_name}) - Updated < 24h ago.")
                return

        if variant_name.lower() == 'base':
            search_term = f"{set_info['year']} {set_info['brand']} {set_info['series']} {clean_player_name} #{card['card_number']}"
        else:
            clean_variant_string = re.sub(r'\(.*?\)', '', variant_name).strip()
            search_term = f"{set_info['year']} {set_info['brand']} {set_info['series']} {clean_player_name} #{card['card_number']} {clean_variant_string}"

        # Fetch pricing data asynchronously
        raw_comps, live_card_image = await fetch_ebay_via_proxy(session, search_term, card['player_name'])
        
        # ⏳ TIMESTAMP REFRESH: Supabase operations are inherently synchronous in Python. 
        # We wrap them in asyncio.to_thread() so they run in the background and don't freeze our other concurrent requests!
        try:
            await asyncio.to_thread(
                lambda: supabase.table("card_variants")
                .update({"last_scraped_at": datetime.now(timezone.utc).isoformat()})
                .eq("id", variant_id).execute()
            )
        except Exception as ts_error:
            print(f"⚠️ Timestamp update skipped: {ts_error}")

        if not raw_comps:
            return
            
        # Optional Image Update
        if live_card_image and ("placeholder" in card.get('image_url', '') or not card.get('image_url')):
            await asyncio.to_thread(
                lambda: supabase.table("base_cards")
                .update({"image_url": live_card_image})
                .eq("id", card["id"]).execute()
            )
            card['image_url'] = live_card_image 

        # Filter Trash Keywords
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

        # Final Insert Push
        if price_entries:
            try:
                await asyncio.to_thread(
                    lambda: supabase.table("price_comps").insert(price_entries[:10]).execute()
                )
                print(f"✅ SUCCESS: Updated {clean_player_name} #{card['card_number']} ({variant_name})!")
            except Exception as db_write_error:
                print(f"⚠️ Database write skipped: {db_write_error}")


# ==========================================
# 3. ASYNC ORCHESTRATOR 
# ==========================================
async def async_main():
    if len(sys.argv) < 4:
        print("❌ Error: Missing arguments. Syntax: python update_by_set.py <year> <brand> '<series>'")
        return
        
    tgt_year = sys.argv[1].strip()
    tgt_brand = sys.argv[2].strip()
    tgt_series = sys.argv[3].strip()
    
    print(f"🚀 Target Confirmed: Fetching cards matching [{tgt_year} {tgt_brand} {tgt_series}]...")

    cards = []
    start_row = 0
    page_size = 1000

    # 1. Fetch the target data payload synchronously (fast enough to do outside the async loop)
    while True:
        response = supabase.table("base_cards").select(
            "id, player_name, card_number, image_url, slug, card_sets!inner(year, brand, series), card_variants(id, variant_name, variant_category, last_scraped_at)"
        ).eq("card_sets.year", tgt_year)\
         .eq("card_sets.brand", tgt_brand)\
         .eq("card_sets.series", tgt_series)\
         .range(start_row, start_row + page_size - 1).execute()
        
        page_data = response.data or []
        cards.extend(page_data)
        if len(page_data) < page_size:
            break
        start_row += page_size
    
    print(f"📦 Successfully loaded {len(cards)} target card rows into task processing memory.")

    if not cards:
        print("⚠️ Search complete. 0 records matched this constraint matrix inside your DB.")
        return

    # 2. Build our Concurrent Task List
    tasks = []
    
    # 🚦 Semaphore limits the script to max 15 active outbound connections at a single time
    # This prevents ScraperAPI from ratelimiting your account for DDoS-like behavior
    sem = asyncio.Semaphore(5) 
    
    # Use a single network session to cleanly manage all 15 concurrent pipelines
    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:
        for card in cards:
            set_info = card['card_sets']
            for variant in card['card_variants']:
                # Queue up a concurrent task for every variant
                task = process_variant(session, sem, card, variant, set_info)
                tasks.append(task)
                
        # 3. Fire all pipelines simultaneously
        print(f"🔥 Igniting {len(tasks)} concurrent pipelines...")
        await asyncio.gather(*tasks)

def run_pipeline():
    # Bootstrap the async loop from standard Python
    asyncio.run(async_main())

if __name__ == "__main__":
    run_pipeline()
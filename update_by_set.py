import os
import re
import sys
import asyncio
import aiohttp
import urllib.parse
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
    clean_query = re.sub(r'\s+', ' ', search_query).strip()
    print(f"📡 Routing proxy query for: '{clean_query}'...")
    
    # 1. Let Python safely build the exact eBay URL parameters
    ebay_params = {
        "_nkw": clean_query,
        "LH_Complete": "1",
        "LH_Sold": "1"
    }
    ebay_query_string = urllib.parse.urlencode(ebay_params)
    ebay_url = f"https://www.ebay.com/sch/i.html?{ebay_query_string}"
    
    # 2. Wrap the ENTIRE eBay URL so ScraperAPI can read it perfectly without breaking
    safe_ebay_url = urllib.parse.quote(ebay_url, safe='')
    
    # 3. Build the final ScraperAPI URL manually as a single, absolute string
    scraper_url = f"http://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url={safe_ebay_url}"
    
    try:
        # 4. Pass the EXACT string to aiohttp. DO NOT use the params={} dictionary.
        async with session.get(scraper_url, timeout=45) as response:
            if response.status != 200:
                print(f"❌ [HTTP ERROR] Status code: {response.status} for query: {clean_query}")
                return None, None
            
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # --- 🛑 X-RAY DEBUG LOGGING START 🛑 ---
            page_title = soup.title.string.strip() if soup.title else "NO TITLE FOUND"
            listings = soup.find_all(class_=lambda x: x and ('s-item' in x or 's-card' in x))
            
            print(f"🔍 [DEBUG] '{clean_query}' | Page Title: {page_title} | HTML Size: {len(html)} bytes | Listings Found: {len(listings)}")
            
            if len(listings) == 0:
                page_text = soup.get_text(separator=' ', strip=True)[:250]
                print(f"🚨 [WARNING] 0 LISTINGS HTML SNIPPET: {page_text}...")
            # --- 🛑 X-RAY DEBUG LOGGING END 🛑 ---
            
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
        print(f"❌ [NETWORK TIMEOUT/CRASH] Pipeline anomaly: {e}")
        return None, None


# ==========================================
# 2. ASYNCHRONOUS VARIANT PROCESSOR
# ==========================================
async def process_variant(session, sem, card, variant, set_info):
    """Processes a single variant card concurrently."""
    try:
        async with sem:
            clean_player_name = re.sub(r"^['\"]|['\"]$", "", card['player_name']).strip()
            variant_id = variant['id']
            variant_name = variant['variant_name']
            last_scraped = variant.get('last_scraped_at')

            # Skip checking if updated within the last 24 hours
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

            raw_comps, live_card_image = await fetch_ebay_via_proxy(session, search_term, card['player_name'])
            
            # Case 1: True Proxy Crash/Network Dropout -> Save timestamp to retry later
            if raw_comps is None:
                print(f"⚠️ Proxy node failed entirely for {clean_player_name} ({variant_name}). Skipping timestamp to allow retry later.")
                return
                
            # Case 2: Successful pull, but zero listings found on market
            if len(raw_comps) == 0:
                print(f"ℹ️ Zero sold listings extracted for {clean_player_name} ({variant_name}).")
                # Update timestamp so we don't burn credits checking empty cards
                try:
                    await asyncio.to_thread(
                        lambda: supabase.table("card_variants")
                        .update({"last_scraped_at": datetime.now(timezone.utc).isoformat()})
                        .eq("id", variant_id).execute()
                    )
                except Exception:
                    pass
                return
                
            # Optional Image Syncing Update
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

            # Final Database Updates
            if price_entries:
                try:
                    await asyncio.to_thread(
                        lambda: supabase.table("price_comps").insert(price_entries[:10]).execute()
                    )
                    
                    await asyncio.to_thread(
                        lambda: supabase.table("card_variants")
                        .update({"last_scraped_at": datetime.now(timezone.utc).isoformat()})
                        .eq("id", variant_id).execute()
                    )
                    print(f"✅ SUCCESS: Updated {clean_player_name} #{card['card_number']} ({variant_name}) in Supabase!")
                except Exception as db_write_error:
                    print(f"⚠️ [DB WRITE ERROR]: {db_write_error}")
            else:
                print(f"ℹ️ No valid comps found for {clean_player_name} ({variant_name}) after filtering out trash keywords.")
                # Lock out the card if it had sales, but they were all spam/trash keywords
                try:
                    await asyncio.to_thread(
                        lambda: supabase.table("card_variants")
                        .update({"last_scraped_at": datetime.now(timezone.utc).isoformat()})
                        .eq("id", variant_id).execute()
                    )
                except Exception:
                    pass

    except Exception as fatal_error:
        print(f"💥 [FATAL THREAD ERROR] Variant {variant.get('variant_name', 'Unknown')} crashed: {fatal_error}")


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

    tasks = []
    sem = asyncio.Semaphore(5)  # Restricts execution to max 5 concurrent external connections
    connector = aiohttp.TCPConnector(limit=5)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        for card in cards:
            set_info = card['card_sets']
            for variant in card['card_variants']:
                task = process_variant(session, sem, card, variant, set_info)
                tasks.append(task)
                
        print(f"🔥 Igniting {len(tasks)} concurrent pipelines...")
        await asyncio.gather(*tasks)


def run_pipeline():
    asyncio.run(async_main())


if __name__ == "__main__":
    run_pipeline()
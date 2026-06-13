import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY") 

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
TARGET_URL = "https://www.beckett.com/news/sports-card-release-calendar/"

def scrape_calendar():
    print("📡 Fetching master calendar from Beckett...")
    
    if not SCRAPER_API_KEY:
        print("❌ No ScraperAPI key found! Aborting.")
        return

    # Using ScraperAPI to bypass Cloudflare and render the HTML tables
    proxy_params = {
        'api_key': SCRAPER_API_KEY, 
        'url': TARGET_URL, 
        'premium': 'true',
        'render': 'true'
    }
    
    try:
        response = requests.get('http://api.scraperapi.com', params=proxy_params)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Beckett groups releases into HTML tables
        tables = soup.find_all('table')
        print(f"📊 Found {len(tables)} tables on the calendar page.")
        
        current_year = datetime.now().year
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                
                # Ensure it's a valid data row (Date | Product | Sport)
                if len(cols) >= 3:
                    date_text = cols[0].text.strip()
                    set_name = cols[1].text.strip()
                    sport = cols[2].text.strip()
                    
                    # Skip header rows or empty sets
                    if "Date" in date_text or "Product" in set_name or not set_name:
                        continue
                        
                    # Filter for only your targeted sports
                    sport_lower = sport.lower()
                    sport_code = ""
                    if "baseball" in sport_lower: sport_code = "MLB"
                    elif "basketball" in sport_lower: sport_code = "NBA"
                    elif "football" in sport_lower: sport_code = "NFL"
                    else: continue # Skip hockey, wrestling, etc.
                    
                    # Parse the Date
                    db_date = None
                    status = "Scheduled"
                    
                    if "TBD" in date_text.upper():
                        status = "TBD"
                    else:
                        try:
                            # Try to convert "June 15" into "2026-06-15"
                            parsed_date = datetime.strptime(f"{date_text} {current_year}", "%B %d %Y")
                            db_date = parsed_date.strftime("%Y-%m-%d")
                        except ValueError:
                            # If the date is vague like "Late June", save it as the status instead
                            status = date_text

                    release_data = {
                        "set_name": set_name,
                        "sport": sport_code,
                        "release_date": db_date,
                        "status": status,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Push to database
                    try:
                        supabase.table("card_releases").upsert(release_data, on_conflict="set_name").execute()
                        print(f"  ✅ SAVED: {set_name} | Date: {db_date} | Status: {status}")
                    except Exception as e:
                        print(f"  ❌ DB ERROR for '{set_name}': {e}")
                        
    except Exception as e:
        print(f"❌ Scrape failed: {e}")

if __name__ == "__main__":
    scrape_calendar()
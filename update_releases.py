import feedparser
import re
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY") 

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BECKETT_FEEDS = {
    "MLB": "https://www.beckett.com/news/category/baseball/feed/",
    "NBA": "https://www.beckett.com/news/category/basketball/feed/",
    "NFL": "https://www.beckett.com/news/category/football/feed/"
}

def extract_date_from_article(article_url):
    """Opens the Beckett article and hunts for the exact release date."""
    if not SCRAPER_API_KEY:
        return None, "Scheduled"
        
    try:
        print(f"    🔍 Deep Scraping article for date...")
        proxy_params = {'api_key': SCRAPER_API_KEY, 'url': article_url}
        response = requests.get('http://api.scraperapi.com', params=proxy_params)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Grab all the text in the article
        text_content = soup.get_text()
        
        # Look for "Release Date: June 15, 2026"
        match_full = re.search(r'Release Date:\s*([A-Za-z]+ \d{1,2}, \d{4})', text_content, re.IGNORECASE)
        if match_full:
            parsed = datetime.strptime(match_full.group(1), "%B %d, %Y")
            return parsed.strftime("%Y-%m-%d"), "Scheduled"
            
        # Look for "Release Date: June 15" (If they forgot the year, assume current year)
        match_partial = re.search(r'Release Date:\s*([A-Za-z]+ \d{1,2})', text_content, re.IGNORECASE)
        if match_partial:
            current_year = datetime.now().year
            parsed = datetime.strptime(f"{match_partial.group(1)}, {current_year}", "%B %d, %Y")
            return parsed.strftime("%Y-%m-%d"), "Scheduled"
            
        if "TBD" in text_content.upper() or "To Be Determined" in text_content:
            return None, "TBD"
            
    except Exception as e:
        print(f"    ❌ Failed to extract date: {e}")
        
    return None, "Scheduled" # Fallback if no date is found

def sync_beckett_releases():
    for sport, feed_url in BECKETT_FEEDS.items():
        print(f"\n{'='*40}")
        print(f"📡 Fetching {sport} feed from Beckett...")
        
        if SCRAPER_API_KEY:
            proxy_params = {'api_key': SCRAPER_API_KEY, 'url': feed_url}
            try:
                response = requests.get('http://api.scraperapi.com', params=proxy_params)
                parsed_feed = feedparser.parse(response.text)
            except Exception as e:
                print(f"❌ Proxy request failed: {e}")
                continue
        else:
            parsed_feed = feedparser.parse(feed_url)
        
        for entry in parsed_feed.entries:
            title = entry.title
            title_lower = title.lower()
            
            if "details" in title_lower or "checklist" in title_lower or "release" in title_lower:
                if "release dates" in title_lower and "information" in title_lower:
                    continue
                
                # 1. Get the perfect Set Name
                clean_set_name = re.sub(r'(?i)(checklist|details|release date|team set lists|guide|image gallery|and|,|-).*', '', title).strip()
                
                print(f"👀 Found: {clean_set_name}")
                
                # 2. Deep Scrape the article for the exact Date
                db_date, status = extract_date_from_article(entry.link)
                
                release_data = {
                    "set_name": clean_set_name,
                    "sport": sport,
                    "release_date": db_date,
                    "status": status,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                # 3. Push to Database
                try:
                    supabase.table("card_releases").upsert(release_data, on_conflict="set_name").execute()
                    print(f"  ✅ SAVED: {clean_set_name} | Date: {db_date} | Status: {status}")
                except Exception as e:
                    print(f"  ❌ DB ERROR for '{clean_set_name}': {e}")

if __name__ == "__main__":
    sync_beckett_releases()
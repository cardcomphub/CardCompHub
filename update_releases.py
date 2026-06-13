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
    if not SCRAPER_API_KEY:
        return None, "Scheduled"
        
    try:
        print(f"    🔍 Deep Scraping article for date...")
        proxy_params = {'api_key': SCRAPER_API_KEY, 'url': article_url}
        response = requests.get('http://api.scraperapi.com', params=proxy_params)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        text_content = soup.get_text(separator='|')
        
        match = re.search(r'Release Date:?\s*([^|]+)', text_content, re.IGNORECASE)
        
        if not match:
            if "TBD" in text_content.upper() or "To Be Determined" in text_content:
                return None, "TBD"
            return None, "Scheduled"
            
        raw_date = match.group(1).strip()
        
        if "TBD" in raw_date.upper():
            return None, "TBD"
            
        # THE SNIPER REGEX: Hunts only for "Month + Number" inside the garbage text
        month_regex = r'(?i)(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,?\s*\d{4})?'
        date_match = re.search(month_regex, raw_date)
        
        if date_match:
            # Strip out commas to make parsing math perfectly clean
            clean_date_str = date_match.group(0).replace(',', '').strip() 
            
            try:
                # If the author included the year (e.g., "June 10 2026")
                if re.search(r'\d{4}', clean_date_str):
                    parsed = datetime.strptime(clean_date_str, "%B %d %Y")
                # If they only wrote "June 10", default to the current year
                else:
                    parsed = datetime.strptime(clean_date_str, "%B %d")
                    parsed = parsed.replace(year=datetime.now().year)
                    
                return parsed.strftime("%Y-%m-%d"), "Scheduled"
            except ValueError:
                pass
                
        # If it's complete nonsense (like a period), clean off the "subject to change" fluff and save it
        clean_status = re.sub(r'(?i)\(subject to change\):?\s*', '', raw_date).strip()[:30]
        return None, clean_status if clean_status else "Scheduled"
            
    except Exception as e:
        print(f"    ❌ Failed to extract date: {e}")
        
    return None, "Scheduled"

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
                
                clean_set_name = re.sub(r'(?i)(checklist|details|release date|team set lists|guide|image gallery|and|,|-).*', '', title).strip()
                print(f"👀 Found: {clean_set_name}")
                
                db_date, status = extract_date_from_article(entry.link)
                
                release_data = {
                    "set_name": clean_set_name,
                    "sport": sport,
                    "release_date": db_date,
                    "status": status,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                try:
                    supabase.table("card_releases").upsert(release_data, on_conflict="set_name").execute()
                    print(f"  ✅ SAVED: {clean_set_name} | Date: {db_date} | Status: {status}")
                except Exception as e:
                    print(f"  ❌ DB ERROR for '{clean_set_name}': {e}")

if __name__ == "__main__":
    sync_beckett_releases()
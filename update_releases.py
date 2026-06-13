import feedparser
import re
import os
import requests
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

def sync_beckett_releases():
    for sport, feed_url in BECKETT_FEEDS.items():
        print(f"\n{'='*40}")
        print(f"📡 Fetching {sport} feed from Beckett...")
        
        parsed_feed = None
        
        if SCRAPER_API_KEY:
            print("🕵️ Routing through ScraperAPI (Premium Pool)...")
            # Using premium=true to force residential IPs and bypass Cloudflare
            proxy_params = {
                'api_key': SCRAPER_API_KEY, 
                'url': feed_url, 
                'premium': 'true',
                'keep_headers': 'true'
            }
            headers = {'Accept': 'application/rss+xml, application/xml'}
            
            try:
                response = requests.get('http://api.scraperapi.com', params=proxy_params, headers=headers)
                print(f"HTTP Status: {response.status_code}")
                
                # Check if Beckett intercepted us with a firewall page
                if "<html" in response.text[:50].lower():
                    print("⚠️ ALERT: Beckett served an HTML firewall page instead of the RSS feed!")
                    print(f"Snippet: {response.text[:150]}...")
                
                parsed_feed = feedparser.parse(response.text)
            except Exception as e:
                print(f"❌ Proxy request failed: {e}")
                continue
        else:
            print("⚠️ No ScraperAPI key found! Trying direct connection (high risk of block)...")
            parsed_feed = feedparser.parse(feed_url)
        
        print(f"📊 Total items pulled from RSS: {len(parsed_feed.entries)}")
        
        for entry in parsed_feed.entries:
            title = entry.title
            title_lower = title.lower()
            
            # X-RAY: Print everything it sees before the filter deletes it
            print(f"  👀 Saw: {title}")
            
            if "details" in title_lower or "checklist" in title_lower or "release" in title_lower:
                if "release dates" in title_lower and "information" in title_lower:
                    continue
                
                clean_set_name = re.sub(r'(?i)(checklist|details|release date|team set lists|guide|image gallery|and|,|-).*', '', title).strip()
                
                release_data = {
                    "set_name": clean_set_name,
                    "sport": sport,
                    "status": "Scheduled",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                try:
                    supabase.table("card_releases").upsert(release_data, on_conflict="set_name").execute()
                    print(f"  ✅ SAVED TO DB: {clean_set_name}")
                except Exception as e:
                    print(f"  ❌ DATABASE ERROR for '{clean_set_name}': {e}")

if __name__ == "__main__":
    sync_beckett_releases()
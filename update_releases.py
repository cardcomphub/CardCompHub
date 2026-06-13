import feedparser
import re
import os
from datetime import datetime, timezone
from supabase import create_client

# 1. Grab credentials dynamically from GitHub Actions environment
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BECKETT_FEEDS = {
    "MLB": "https://www.beckett.com/news/category/baseball/feed/",
    "NBA": "https://www.beckett.com/news/category/basketball/feed/",
    "NFL": "https://www.beckett.com/news/category/football/feed/"
}

def sync_beckett_releases():
    for sport, feed_url in BECKETT_FEEDS.items():
        print(f"\n📡 Fetching {sport} feed from Beckett...")
        parsed_feed = feedparser.parse(feed_url)
        
        for entry in parsed_feed.entries:
            title = entry.title
            title_lower = title.lower()
            
            # Filter: Only grab articles announcing set details or checklists
            if "details" in title_lower or "checklist" in title_lower or "release" in title_lower:
                
                # Skip the generic monthly roundup articles
                if "release dates" in title_lower and "information" in title_lower:
                    continue
                
                # Clean the title: Remove the blog text to leave just the Set Name
                clean_set_name = re.sub(r'(?i)(checklist|details|release date|team set lists|guide|image gallery|and|,|-).*', '', title).strip()
                
                print(f"✅ Extracted: [{sport}] {clean_set_name}")
                
                # Prep the payload to match your database schema perfectly
                release_data = {
                    "set_name": clean_set_name,
                    "sport": sport,
                    "status": "Scheduled",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                # 2. ACTUALLY PUSH TO SUPABASE
                try:
                    supabase.table("card_releases").upsert(release_data, on_conflict="set_name").execute()
                    print(f"💾 Saved {clean_set_name} to database!")
                except Exception as e:
                    print(f"❌ Error saving {clean_set_name}: {e}")

if __name__ == "__main__":
    sync_beckett_releases()
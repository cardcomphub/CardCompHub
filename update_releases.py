import feedparser
import re
from datetime import datetime, timezone
# from supabase import create_client

# supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 1. Define the targeted Beckett feeds
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
            
            # 2. Filter: Only grab articles announcing set details or checklists
            if "details" in title_lower or "checklist" in title_lower or "release" in title_lower:
                
                # Skip the generic monthly roundup articles (e.g., "2024 Baseball Card Release Dates")
                if "release dates" in title_lower and "information" in title_lower:
                    continue
                
                # 3. Clean the title: Remove the blog text to leave just the Set Name
                # Example: "2024 Panini Prizm Football Checklist and Details" -> "2024 Panini Prizm Football"
                clean_set_name = re.sub(r'(?i)(checklist|details|release date|team set lists|guide|image gallery|and|,|-).*', '', title).strip()
                
                print(f"✅ Extracted: [{sport}] {clean_set_name}")
                
                # 4. Prep the payload for your database
                release_data = {
                    "set_name": clean_set_name,
                    "sport": sport,
                    "article_url": entry.link, # Save the Beckett link so users can read more
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                # 5. Push to Supabase (Uncomment when ready)
                # supabase.table("card_releases").upsert(release_data, on_conflict="set_name").execute()

if __name__ == "__main__":
    sync_beckett_releases()
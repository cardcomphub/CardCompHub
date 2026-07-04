import feedparser
import re
import os
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from supabase import create_client
from openai import OpenAI

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY") 
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = OpenAI(api_key=OPENAI_API_KEY)

BECKETT_FEEDS = {
    "MLB": "https://www.beckett.com/news/category/baseball/feed/",
    "NBA": "https://www.beckett.com/news/category/basketball/feed/",
    "NFL": "https://www.beckett.com/news/category/football/feed/"
}

def extract_data_with_ai(article_url):
    """Deep scrapes the article and uses AI to extract dates, hits, and pack art."""
    if not SCRAPER_API_KEY or not OPENAI_API_KEY:
        return {"release_date": None, "status": "Scheduled", "image_url": None, "hits": []}
        
    try:
        print(f"    🔍 Scraping & Analyzing article...")
        # 1. Fetch the raw HTML via ScraperAPI
        proxy_params = {'api_key': SCRAPER_API_KEY, 'url': article_url}
        response = requests.get('http://api.scraperapi.com', params=proxy_params)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 2. Extract Text (truncate to save tokens, first 10,000 chars is plenty)
        text_content = soup.get_text(separator='\n', strip=True)[:10000]
        
        # 3. Extract all potential image URLs to give the AI options for the pack art
        images = []
        for img in soup.find_all('img'):
            src = img.get('src')
            # Filter out tiny icons, gifs, and base64 junk
            if src and src.startswith('http') and not src.endswith('.gif'):
                images.append(src)
        
        # 4. Prompt the AI to do the heavy lifting
        system_prompt = """
        You are an expert sports card data extractor. I will provide the raw text of an article announcing a new sports card set, along with a list of image URLs found on the page.
        
        Extract the following information and return ONLY a valid JSON object matching this schema:
        {
            "release_date": "YYYY-MM-DD string, or 'TBD' if unknown",
            "status": "'Scheduled', 'Delayed', or 'TBD'",
            "image_url": "The single best URL from the provided image list that represents the product's box, pack, or main promo art. Return null if none fit.",
            "hits": ["An array of strings", "List the guaranteed box hits", "e.g., '2 Autographs', '1 Memorabilia Card', '10 Inserts'"]
        }
        """
        
        user_content = f"ARTICLE TEXT:\n{text_content}\n\nIMAGE URLs FOUND:\n{json.dumps(images[:15])}"

        completion = ai_client.chat.completions.create(
            model="gpt-4o-mini", # Fast, cheap, and highly capable for this
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        )
        
        # 5. Parse the AI response
        ai_data = json.loads(completion.choices[0].message.content)
        
        # Format date for the database
        db_date = None
        if ai_data.get("release_date") and ai_data["release_date"] != "TBD":
            db_date = ai_data["release_date"]
            
        return {
            "release_date": db_date,
            "status": ai_data.get("status", "Scheduled"),
            "image_url": ai_data.get("image_url"),
            "hits": ai_data.get("hits", [])
        }
            
    except Exception as e:
        print(f"    ❌ AI Extraction Failed: {e}")
        return {"release_date": None, "status": "Scheduled", "image_url": None, "hits": []}

def sync_beckett_releases():
    # A standard User-Agent so Beckett doesn't instantly block our direct RSS request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for sport, feed_url in BECKETT_FEEDS.items():
        print(f"\n{'='*40}")
        print(f"📡 Fetching {sport} feed from Beckett...")
        
        # 🎯 THE FIX: Fetch the RSS feed directly. Do NOT use ScraperAPI for XML feeds.
        try:
            response = requests.get(feed_url, headers=headers, timeout=15)
            parsed_feed = feedparser.parse(response.content)
            
            if not parsed_feed.entries:
                print(f"⚠️ Warning: No entries found for {sport}. The feed might be temporarily blocked or empty.")
                continue
                
        except Exception as e:
            print(f"❌ Failed to fetch {sport} feed: {e}")
            continue
        
        for entry in parsed_feed.entries:
            title = entry.title
            title_lower = title.lower()
            
            if "details" in title_lower or "checklist" in title_lower or "release" in title_lower:
                if "release dates" in title_lower and "information" in title_lower:
                    continue
                
                clean_set_name = re.sub(r'(?i)(checklist|details|release date|team set lists|guide|image gallery|and|,|-).*', '', title).strip()
                print(f"👀 Found: {clean_set_name}")
                
                # Hand it off to the AI Pipeline
                ai_data = extract_data_with_ai(entry.link)
                
                release_data = {
                    "set_name": clean_set_name,
                    "sport": sport,
                    "release_date": ai_data["release_date"],
                    "status": ai_data["status"],
                    "image_url": ai_data["image_url"],
                    "hits": ai_data["hits"],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                try:
                    supabase.table("card_releases").upsert(release_data, on_conflict="set_name").execute()
                    print(f"  ✅ SAVED: {clean_set_name} | Hits Found: {len(ai_data['hits'])}")
                except Exception as e:
                    print(f"  ❌ DB ERROR for '{clean_set_name}': {e}")

if __name__ == "__main__":
    sync_beckett_releases()

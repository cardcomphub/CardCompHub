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

# 🎯 THE FIX: Changed from /feed/ to the standard HTML category pages
BECKETT_CATEGORIES = {
    "MLB": "https://www.beckett.com/news/category/baseball/",
    "NBA": "https://www.beckett.com/news/category/basketball/",
    "NFL": "https://www.beckett.com/news/category/football/"
}

def extract_data_with_ai(article_url):
    """Deep scrapes the article and uses AI to extract dates, hits, and pack art."""
    if not SCRAPER_API_KEY or not OPENAI_API_KEY:
        return {"release_date": None, "status": "Scheduled", "image_url": None, "hits": []}
        
    try:
        print(f"    🔍 Scraping & Analyzing article...")
        proxy_params = {'api_key': SCRAPER_API_KEY, 'url': article_url}
        response = requests.get('http://api.scraperapi.com', params=proxy_params)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        text_content = soup.get_text(separator='\n', strip=True)[:10000]
        
        images = []
        for img in soup.find_all('img'):
            src = img.get('src')
            if src and src.startswith('http') and not src.endswith('.gif'):
                images.append(src)
        
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
            model="gpt-4o-mini",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        )
        
        ai_data = json.loads(completion.choices[0].message.content)
        
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
    for sport, category_url in BECKETT_CATEGORIES.items():
        print(f"\n{'='*40}")
        print(f"📡 Fetching {sport} category page from Beckett...")
        
        # 🎯 THE FIX: Scrape the HTML directly using ScraperAPI
        proxy_params = {'api_key': SCRAPER_API_KEY, 'url': category_url}
        try:
            response = requests.get('http://api.scraperapi.com', params=proxy_params, timeout=45)
            soup = BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"❌ Failed to fetch {sport} page: {e}")
            continue
            
        seen_links = set()
        
        # Hunt for all article links on the page
        for a_tag in soup.find_all('a'):
            title = a_tag.get_text(strip=True)
            link = a_tag.get('href', '')
            
            # Skip empty links, non-urls, or duplicates
            if not title or not link.startswith('http') or link in seen_links:
                continue
                
            title_lower = title.lower()
            
            # Filter for release/checklist articles
            if "details" in title_lower or "checklist" in title_lower or "release" in title_lower:
                if "release dates" in title_lower and "information" in title_lower:
                    continue
                    
                seen_links.add(link) # Prevent scraping the same article twice
                
                clean_set_name = re.sub(r'(?i)(checklist|details|release date|team set lists|guide|image gallery|and|,|-).*', '', title).strip()
                print(f"👀 Found: {clean_set_name}")
                
                # Hand it off to the AI Pipeline
                ai_data = extract_data_with_ai(link)
                
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
                    print(f"  ✅ SAVED: {clean_set_name} | Date: {ai_data['release_date']} | Hits: {len(ai_data['hits'])}")
                except Exception as e:
                    print(f"  ❌ DB ERROR for '{clean_set_name}': {e}")

if __name__ == "__main__":
    sync_beckett_releases()

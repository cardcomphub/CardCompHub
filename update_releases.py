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

BECKETT_URLS = {
    "MLB": "https://www.beckett.com/news/category/baseball/",
    "NBA": "https://www.beckett.com/news/category/basketball/",
    "NFL": "https://www.beckett.com/news/category/football/"
}

def extract_data_with_ai(article_url):
    """Deep scrapes the article and uses AI to write an article and extract images/checklists."""
    if not SCRAPER_API_KEY or not OPENAI_API_KEY:
        return None
        
    try:
        print(f"    🧠 AI processing article content...")
        proxy_params = {'api_key': SCRAPER_API_KEY, 'url': article_url}
        response = requests.get('http://api.scraperapi.com', params=proxy_params)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        text_content = soup.get_text(separator='\n', strip=True)[:10000]
        
        # Extract Images
        images = []
        for img in soup.find_all('img'):
            src = img.get('src')
            if src and src.startswith('http') and not src.endswith('.gif') and 'logo' not in src.lower():
                images.append(src)
                
        # Extract potential checklist links (Excel, PDF, CSV)
        links = []
        for a in soup.find_all('a'):
            href = a.get('href')
            if href and ('.xls' in href or '.pdf' in href or '.csv' in href):
                links.append(href)
        
        system_prompt = """
        You are an expert sports card journalist and data auditor. I will provide the raw HTML text from a product announcement, a list of image URLs, and a list of file links.
        
        Extract the details and return ONLY a valid JSON object matching this exact schema:
        {
            "set_name": "Clean product name (e.g., '2026 Topps Chrome Baseball')",
            "sport": "Determine the sport. Choose exactly one: 'MLB', 'NBA', 'NFL', or 'OTHER'. If the set is Hockey, Soccer, Racing, UFC, Wrestling, or Non-Sport, you MUST output 'OTHER'.",
            "release_date": "YYYY-MM-DD string, or 'TBD' if unknown",
            "status": "'Scheduled', 'Delayed', or 'TBD'",
            "hits": ["Array of strings", "e.g., '2 Autographs', '1 Memorabilia Card'"],
            "image_urls": ["url1", "url2"],
            "checklist_url": "Look at the file links and the text. If there is a direct link to download the official checklist (usually an .xlsx, .csv, or .pdf), provide the URL here. If the checklist is not out yet, return null.",
            "article_body": "A 2 to 3 paragraph SEO-friendly blog post written in HTML format (using <p>, <h3>, <ul>). Do not include an <h1>."
        }
        """
        
        user_content = f"ARTICLE TEXT:\n{text_content}\n\nFILE LINKS FOUND:\n{json.dumps(links)}\n\nIMAGE URLs FOUND:\n{json.dumps(images[:20])}"

        completion = ai_client.chat.completions.create(
            model="gpt-4o-mini", 
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        )
        
        return json.loads(completion.choices[0].message.content)
            
    except Exception as e:
        print(f"    ❌ AI Extraction Failed: {e}")
        return None

def sync_beckett_releases():
    processed_urls = set()
    
    for default_sport, url in BECKETT_URLS.items():
        print(f"\n{'='*50}")
        print(f"📡 Crawling {default_sport} category via ScraperAPI...")
        
        try:
            proxy_params = {'api_key': SCRAPER_API_KEY, 'url': url}
            response = requests.get('http://api.scraperapi.com', params=proxy_params)
            soup = BeautifulSoup(response.text, 'html.parser')
            
        except Exception as e:
            print(f"❌ Failed to fetch {default_sport} HTML: {e}")
            continue
        
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href')
            title = a_tag.get_text().strip()
            
            if not href or not title:
                continue
                
            title_lower = title.lower()
            
            is_valid_topic = 'details' in title_lower or 'checklist' in title_lower
            has_modern_year = re.search(r'202[4-9]', title)
            is_not_garbage = 'guide' not in title_lower and 'upcoming' not in title_lower and 'index' not in title_lower
            
            if is_valid_topic and has_modern_year and is_not_garbage:
                if href in processed_urls:
                    continue
                    
                processed_urls.add(href)
                print(f"👀 Discovered Valid Set: {title}")
                
                ai_data = extract_data_with_ai(href)
                
                if not ai_data:
                    continue
                
                final_sport = ai_data.get("sport", "OTHER").upper()
                if final_sport not in ["MLB", "NBA", "NFL"]:
                    print(f"  ⏭️ SKIPPED: '{title}' was categorized as '{final_sport}'.")
                    continue
                
                db_date = None
                if ai_data.get("release_date") and ai_data["release_date"] != "TBD":
                    db_date = ai_data["release_date"]
                
                raw_name = ai_data.get("set_name", title)
                clean_slug = re.sub(r'[^a-z0-9\s-]', '', raw_name.lower()).strip()
                clean_slug = re.sub(r'[\s-]+', '-', clean_slug)
                    
                release_data = {
                    "set_name": raw_name,
                    "slug": clean_slug,
                    "sport": final_sport,
                    "release_date": db_date,
                    "status": ai_data.get("status", "Scheduled"),
                    "hits": ai_data.get("hits", []),
                    "image_urls": ai_data.get("image_urls", []), 
                    "checklist_url": ai_data.get("checklist_url"), 
                    "article_body": ai_data.get("article_body", ""), 
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                try:
                    supabase.table("card_releases").upsert(release_data, on_conflict="slug").execute()
                    print(f"  ✅ SAVED: {raw_name} | Slug: {clean_slug}")
                except Exception as e:
                    print(f"  ❌ DB ERROR for '{title}': {e}")

if __name__ == "__main__":
    sync_beckett_releases()

import os
import json
import requests

SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY") or "PASTE_YOUR_API_KEY_HERE"

TARGET_QUERY = "2025 Topps Chrome Tecmo Tony Dorsett"
print(f"📡 Requesting Structured JSON for: '{TARGET_QUERY}'...")

endpoint = "https://api.scraperapi.com/structured/ebay/search/v2"
params = {
    'api_key': SCRAPER_API_KEY, 
    'query': TARGET_QUERY, 
    'country_code': 'us',
    'show_only': 'completed_items,sold_items'
}

response = requests.get(endpoint, params=params, timeout=60)

print(f"\n--- 📊 DIAGNOSTIC RESULTS ---")
print(f"1. HTTP Status Code: {response.status_code}")

try:
    data = response.json()
    print("\n2. JSON Response Structure:")
    
    if isinstance(data, list):
        print(f"  • Returned a LIST with {len(data)} items.")
    elif isinstance(data, dict):
        print(f"  • Returned a DICTIONARY with keys: {list(data.keys())}")
        if "error" in data:
            print(f"  🛑 ScraperAPI Error Message: {data['error']}")
    else:
        print(f"  • Returned unknown type: {type(data)}")

    # Save the exact JSON to disk
    with open("debug_scraper_structured.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        
    print(f"\n3. Full JSON saved to 'debug_scraper_structured.json'.")
    
except Exception as e:
    print(f"\n❌ Failed to parse JSON. Raw response:\n{response.text[:500]}")

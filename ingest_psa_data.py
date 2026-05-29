import os
import time
import requests
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "your-anon-key")
PSA_TOKEN = os.environ.get("PSA_API_TOKEN", "your_actual_psa_bearer_token_here")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {
    "Authorization": f"Bearer {PSA_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def fetch_psa_cert_with_retry(cert_num, max_retries=3):
    """Fetches certificate data from PSA with exponential backoff for 429 errors."""
    # 🛠️ FIXED: Updated path format to follow PSA's REST parameters directory layout
    psa_url = f"https://api.psacard.com/publicapi/cert/GetByCertNumber/{str(cert_num).strip()}"
    delay = 2
    
    for attempt in range(max_retries):
        try:
            response = requests.get(psa_url, headers=HEADERS)
            
            # Handle standard successful operations
            if response.status_code == 200:
                return response.json()
                
            # Handle rate limiting throttling intercepts
            if response.status_code == 429:
                print(f"⏳ Rate limited (429) on cert #{cert_num}. Attempt {attempt + 1}/{max_retries}.")
                
                # Check if the PSA server specified a exact 'Retry-After' wait window in headers
                retry_after = response.headers.get("Retry-After")
                wait_time = int(retry_after) if retry_after else delay
                
                print(f"💤 Backing off network loops. Pausing execution for {wait_time} seconds...")
                time.sleep(wait_time)
                delay *= 2  # Double the delay window length for the next fallback pass
                continue
                
            print(f"❌ PSA API rejected request for #{cert_num}. Status Code: {response.status_code}")
            return None
            
        except Exception as e:
            print(f"⚠️ Connection glitch during request: {str(e)}")
            time.sleep(delay)
            continue
            
    print(f"🛑 Max retries exhausted for cert #{cert_num}. Daily 100-call quota may be full.")
    return None

def ingest_by_certificates(cert_list):
    print(f"🚀 Starting advanced ingestion pipeline for {len(cert_list)} rows...")
    
    for cert_num in cert_list:
        print(f"\n🔍 Processing Certificate: #{cert_num}")
        time.sleep(1.5) # Paced rhythm buffer protects master connection threads
        
payload = fetch_psa_cert_with_retry(cert_num)
        if not payload or payload.get("IsValidRequest") is False:
            print(f"⚠️ Certificate #{cert_num} could not be matched or returned empty results.")
            continue
            
        # Target data root block cleanly
        cert_details = payload.get("PSACertificate") if payload.get("PSACertificate") else payload
        spec_id = cert_details.get("SpecId")
        player_name = cert_details.get("Subject", "").strip()
        card_number = cert_details.get("CardNumber", "").strip()
        official_image = cert_details.get("CertImageUrlFront", "")

        if not spec_id:
            print(f"⚠️ No master SpecId returned for tracking sequence.")
            continue

        print(f"Match Confirmed: {player_name} #{card_number} (Spec ID: {spec_id})")

        # Sync against your base_cards checklist database rows
        card_match = supabase.table("base_cards") \
            .select("id, image_url") \
            .ilike("player_name", f"%{player_name}%") \
            .eq("card_number", card_number) \
            .execute()

        if not card_match.data:
            print(f"⏩ Identity token matching skipped for '{player_name}'. Row absence handled.")
            continue

        target_card_id = card_match.data[0]["id"]
        current_image = card_match.data[0].get("image_url")

        # Map details to Supabase parent profiles
        update_payload = {"psa_spec_id": spec_id}
        if not current_image and official_image:
            update_payload["image_url"] = official_image
            print("📸 Injecting high-resolution official layout scan...")

        supabase.table("base_cards").update(update_payload).eq("id", target_card_id).execute()
        print(f"✅ Successfully mapped base_cards ID: {target_card_id}")

        # Sync population records metrics box values
        pop_data = {
            "base_card_id": target_card_id,
            "psa_spec_id": spec_id,
            "pop_10": cert_details.get("PopTen", 0),
            "pop_9": cert_details.get("PopNine", 0),
            "pop_8": cert_details.get("PopEight", 0),
            "pop_total": cert_details.get("TotalPopulation", 0),
            "updated_at": "now()"
        }

        supabase.table("psa_pop_reports").upsert(pop_data, on_conflict="base_card_id").execute()
        print(f"📊 Population tables refreshed for Spec ID: {spec_id}")

if __name__ == "__main__":
    # Test items list parameters sequence array
    sample_certificates = ["84692014", "90184720", "75920184"]
    ingest_by_certificates(sample_certificates)
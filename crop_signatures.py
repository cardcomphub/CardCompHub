import os
import cv2
from ultralytics import YOLO
from supabase import create_client, Client

# 🎯 1. Setup Supabase & AI
SUPABASE_URL = "https://mjnzpmkzdtrdpwzpgvdo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1qbnpwbWt6ZHRyZHB3enBndmRvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTczMTk4MywiZXhwIjoyMDk1MzA3OTgzfQ.-ONKSC3gQBZOqKJc7_SGEj1CPb6HA0nlfHPo0zNwxJ8"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

model = YOLO("best.pt")

INPUT_DIR = r"C:\users\apena\desktop\autograph_dataset\all_raw_images"

print("🤖 Hunting signatures and uploading to Supabase...")

for filename in os.listdir(INPUT_DIR):
    if not filename.endswith(".jpg"):
        continue
        
    img_id = filename.replace(".jpg", "")
    img_path = os.path.join(INPUT_DIR, filename)
    img = cv2.imread(img_path)
    
    # 🎯 2. Find the signature
    results = model.predict(source=img, conf=0.5, verbose=False)
    boxes = results[0].boxes
    if len(boxes) == 0:
        continue
        
    box = boxes[0].xyxy[0].cpu().numpy()
    x1, y1, x2, y2 = map(int, box)
    cropped_sig = img[y1:y2, x1:x2]
    
    # 🎯 3. Lookup the player in Supabase using the image ID
    response = supabase.table("price_comps") \
        .select("card_variants!inner(base_cards!inner(player_name))") \
        .eq('id', img_id) \
        .execute()
        
    if not response.data:
        continue
        
    # Extract player name and format it (e.g., "Bobby Witt Jr" -> "bobby_witt_jr")
    raw_name = response.data[0]['card_variants']['base_cards']['player_name']
    clean_player_id = raw_name.lower().replace(" ", "_").replace(".", "")
    
    # 🎯 4. Convert cropped image to bytes and upload!
    # We use cv2.imencode to turn the OpenCV image matrix back into a standard JPG file format
    success, encoded_image = cv2.imencode('.jpg', cropped_sig)
    if success:
        file_bytes = encoded_image.tobytes()
        storage_path = f"{clean_player_id}.jpg"
        
        try:
            # Upload to the 'signatures' bucket. If it already exists, overwrite it.
            supabase.storage.from_("signatures").upload(
                file=file_bytes,
                path=storage_path,
                file_options={"content-type": "image/jpeg", "upsert": "true"}
            )
            print(f"✅ Uploaded signature for {raw_name}")
        except Exception as e:
            print(f"⚠️ Could not upload {raw_name}: {e}")

print("🎉 All signatures extracted and pushed to the cloud!")
from ultralytics import YOLO

print("🧠 Downloading base YOLOv8 model...")
# 1. Load the pre-trained YOLOv8 "nano" model (it is the fastest and most efficient)
model = YOLO("yolov8n.pt") 

print("🚀 Starting training process...")
# 2. Train the model on your custom data
# MAKE SURE THIS PATH POINTS TO YOUR EXTRACTED data.yaml FILE
yaml_path = r"C:\users\apena\desktop\autograph_dataset_yolo\data.yaml"

results = model.train(
    data=yaml_path,
    epochs=50,       # How many times it reads through your images (50 is a great start)
    imgsz=640,       # The image size the AI scales everything to
    batch=16,        # How many images it processes at once
    plots=True       # Generates cool graphs of its learning progress!
)

print("✅ Training complete! Your model is ready.")
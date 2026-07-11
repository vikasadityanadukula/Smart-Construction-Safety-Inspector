from ultralytics import YOLO

model = YOLO("models/models/best.pt")   # Use the correct path for your project

print("Model Classes:")
print(model.names)
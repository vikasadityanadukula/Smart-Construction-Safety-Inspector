"""
SafeSite AI - PPE Detection
Smart Construction Safety Inspector 
(High-Speed Frame Skipping, Multi-Distance 1280px Tracking & Safety Waist/Vest Support)
"""

import argparse
import os
import sys
import threading
import array
import json

import cv2
import numpy as np
import requests
from ultralytics import YOLO

# Suppress Pygame initial welcome banner in terminal output
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

# -----------------------------------
# CONFIGURATION (defaults; overridable via CLI)
# -----------------------------------
MODEL_PATH = "models/models/best7.pt"
API_URL = "http://127.0.0.1:8000/violations"
CONF_THRESHOLD = 0.20  
OUTPUT_DIR = "output"
OUTPUT_VIDEO_NAME = "detected_video.mp4"

# ANTI-CAP FILTERING CONFIG
HELMET_CONF_THRESHOLD = 0.45 

# DEFAULT DANGER ZONE: Coordinates format: (x, y)
DANGER_ZONE_POLYGON = [(200, 400), (800, 400), (1000, 700), (100, 700)]


# -----------------------------------
# STABLE AUDIO ALERT GENERATION
# -----------------------------------
WARNING_SOUND = None

def init_audio_engine():
    """Generates an explicit synthesizer sine wave audio token to guarantee cross-platform playback."""
    global WARNING_SOUND
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=1)
        
        # Synthesize a clear 1000Hz alert tone duration mapping (200ms)
        sample_rate = 22050
        frequency = 1000
        duration = 0.2
        
        num_samples = int(sample_rate * duration)
        buf = array.array('h', [0] * num_samples)
        for i in range(num_samples):
            t = float(i) / sample_rate
            # Generate sine coordinates scaled to 16-bit signed integer spaces
            buf[i] = int(32767.0 * np.sin(2.0 * np.pi * frequency * t))
            
        WARNING_SOUND = pygame.mixer.Sound(buffer=buf)
    except Exception as e:
        print(f"WARNING: Audio subsystem initialization failed: {e}. Script continuing in silent mode.")

def play_warning_beep():
    """Asynchronously streams the alarm wave avoiding loop iteration blocks."""
    global WARNING_SOUND
    if WARNING_SOUND is not None:
        if not pygame.mixer.get_busy():
            threading.Thread(target=WARNING_SOUND.play, daemon=True).start()


# -----------------------------------
# CLI ARGS
# -----------------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="SafeSite AI - PPE Detection")
    parser.add_argument("--video", type=str, default=None,
                        help="Path to video file, or '0' for webcam. If omitted, a file picker opens.")
    parser.add_argument("--model", type=str, default=MODEL_PATH,
                        help="Path to YOLO .pt model")
    parser.add_argument("--conf", type=float, default=CONF_THRESHOLD,
                        help="Confidence threshold for detections")
    parser.add_argument("--imgsz", type=int, default=1280,
                        help="Inference image resolution size. 1280 captures distant/small objects perfectly.")
    parser.add_argument("--skip-frames", type=int, default=3,
                        help="Process every N-th frame to dramatically increase playback speed (1 = process every frame).")
    parser.add_argument("--no-display", action="store_true",
                        help="Disable the live cv2 preview window")
    parser.add_argument("--api-url", type=str, default=API_URL,
                        help="Backend endpoint to POST results to")
    return parser.parse_args()


def select_video_via_dialog():
    try:
        from tkinter import Tk
        from tkinter.filedialog import askopenfilename
    except ImportError:
        print("tkinter not available in this environment. Pass --video <path> instead.")
        sys.exit(1)

    Tk().withdraw()
    path = askopenfilename(
        title="Select Construction Video",
        filetypes=[("Video Files", "*.mp4 *.avi *.mov")]
    )
    if not path:
        print("No video selected.")
        sys.exit(0)
    return path


def load_model(model_path):
    if not os.path.exists(model_path):
        print(f"ERROR: Model file not found at '{model_path}'.")
        sys.exit(1)
    model = YOLO(model_path)
    print("\n" + "="*50)
    print("Model Loaded Successfully")
    print("="*50 + "\n")
    return model


def open_video(video_arg):
    source = int(video_arg) if video_arg.isdigit() else video_arg
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"ERROR: Could not open video source '{video_arg}'.")
        sys.exit(1)
    return cap


def make_writer(output_path, fps, width, height):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps if fps > 0 else 25, (width, height))
    if not writer.isOpened():
        output_path = output_path.replace(".mp4", ".avi")
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(output_path, fourcc, fps if fps > 0 else 25, (width, height))
    return writer, output_path


def draw_overlay(annotated, frame_workers, frame_helmet, frame_vest, frame_danger, video_name, height):
    cv2.putText(annotated, f"Workers Counted: {frame_workers}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(annotated, f"Helmet Violations: {frame_helmet}", (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.putText(annotated, f"Vest/Waist Violations: {frame_vest}", (20, 110),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 140, 255), 2)
    cv2.putText(annotated, f"Danger Zone Breaches: {frame_danger}", (20, 145),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.putText(annotated, video_name, (20, height - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)


def send_to_backend(api_url, payload):
    print("\nSending data to Backend...")
    try:
        response = requests.post(api_url, json=payload, timeout=5)
        if response.status_code in [200, 201]:
            print("Backend Updated Successfully")
        else:
            print(f"Backend Error: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print("Backend Error:")
        print(e)

# -----------------------------------
# MAIN RUNTIME ENGINE
# -----------------------------------
def main():
    args = parse_args()

    print("=" * 50)
    print("SafeSite AI - PPE Detection Dashboard")
    print("=" * 50)

    init_audio_engine()
    model = load_model(args.model)
    
    # DEBUG LINE: Prints your model's target labels to verify setup names
    print("Your Model Classes are:", model.names)

    video_arg = args.video if args.video is not None else select_video_via_dialog()
    video_name = "Webcam" if str(video_arg) == "0" else os.path.basename(str(video_arg))
    print("Selected Video:", video_name)
    print("Inference Resolution Size:", args.imgsz)
    print("Processing Frame Interval:", args.skip_frames)

    cap = open_video(str(video_arg))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480

    output_path = os.path.join(OUTPUT_DIR, OUTPUT_VIDEO_NAME)
    out, output_path = make_writer(output_path, fps, width, height)

    zone_pts = np.array(DANGER_ZONE_POLYGON, dtype=np.int32).reshape((-1, 1, 2))

    peak_workers = 0                 
    peak_helmet_violations = 0       
    peak_vest_violations = 0         
    peak_danger_zone_entries = 0     
    frame_count = 0

    display_enabled = not args.no_display

    # Cache tracking dictionaries to carry over data across frame skipping gaps
    cached_boxes = []
    frame_workers = 0
    frame_helmet = 0
    frame_vest = 0
    frame_danger_entries = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_count += 1
            annotated = frame.copy()

            # Generate Danger Zone HUD Graphic
            overlay = annotated.copy()
            cv2.fillPoly(overlay, [zone_pts], (0, 0, 255))  
            cv2.polylines(annotated, [zone_pts], True, (0, 0, 255), 3)  
            cv2.addWeighted(overlay, 0.20, annotated, 0.80, 0, annotated)  

            # RUN MODEL INFERENCE ON SELECTED FRAME INTERVALS (Speed boost setup)
            if (frame_count - 1) % args.skip_frames == 0:
                results = model(frame, conf=args.conf, iou=0.4, max_det=100, imgsz=args.imgsz, verbose=False)
                boxes = results[0].boxes
                
                cached_boxes = []
                frame_workers = 0
                frame_helmet = 0
                frame_vest = 0
                frame_danger_entries = 0

                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    raw_label = model.names[cls]
                    label_lower = raw_label.lower().strip()

                    is_helmet_related = "hardhat" in label_lower or "helmet" in label_lower
                    
                    if is_helmet_related and conf < HELMET_CONF_THRESHOLD:
                        continue

                    is_worker = "person" in label_lower or "worker" in label_lower
                    is_helmet_violation = "no" in label_lower and is_helmet_related
                    
                    # FIXED MATCHING LOGIC: Catches "waist", "vest", or "jacket" datasets
                    is_vest_related = "vest" in label_lower or "waist" in label_lower or "jacket" in label_lower
                    is_vest_violation = "no" in label_lower and is_vest_related

                    if is_helmet_related or is_vest_related:
                        if "no" not in label_lower:
                            is_worker = True

                    if is_worker:
                        frame_workers += 1
                    if is_helmet_violation:
                        frame_helmet += 1
                    if is_vest_violation:
                        frame_vest += 1

                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    is_inside_zone = False

                    if is_worker:
                        feet_x = int((x1 + x2) / 2)
                        feet_y = y2
                        if cv2.pointPolygonTest(zone_pts, (feet_x, feet_y), False) >= 0:
                            is_inside_zone = True
                            frame_danger_entries += 1

                    # Save current detections into memory
                    cached_boxes.append({
                        "coords": (x1, y1, x2, y2),
                        "label": raw_label,
                        "is_violation": (is_helmet_violation or is_vest_violation),
                        "is_worker": is_worker,
                        "is_inside_zone": is_inside_zone
                    })

            # PERSISTENT BOUNDING BOX RENDER (Draws smoothly every frame without blinking)
            for target in cached_boxes:
                x1, y1, x2, y2 = target["coords"]
                
                if target["is_inside_zone"]:
                    feet_x = int((x1 + x2) / 2)
                    cv2.circle(annotated, (feet_x, y2), 8, (0, 0, 255), -1)

                if target["is_violation"]:
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    cv2.rectangle(annotated, (x1, max(y1 - 25, 0)), (x2, y1), (0, 0, 255), -1)
                    cv2.putText(annotated, f"ALERT: {target['label']}", (x1 + 5, max(y1 - 7, 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                else:
                    box_color = (255, 255, 0) if (target["is_worker"] and target["is_inside_zone"]) else (0, 255, 0)
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 2)
                    cv2.putText(annotated, target["label"], (x1, max(y1 - 7, 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 1)

            # --- AUDIO ALERT BLOCKS ---
            if frame_danger_entries > 0:
                play_warning_beep()

            peak_workers = max(peak_workers, frame_workers)
            peak_helmet_violations = max(peak_helmet_violations, frame_helmet)
            peak_vest_violations = max(peak_vest_violations, frame_vest)
            peak_danger_zone_entries = max(peak_danger_zone_entries, frame_danger_entries)

            draw_overlay(annotated, frame_workers, frame_helmet, frame_vest, frame_danger_entries, video_name, height)
            out.write(annotated)

            if display_enabled:
                try:
                    cv2.namedWindow("SafeSite AI", cv2.WINDOW_NORMAL)
                    cv2.imshow("SafeSite AI", annotated)
                    if cv2.waitKey(1) == ord("q"):
                        break
                except cv2.error:
                    display_enabled = False

    finally:
        cap.release()
        out.release()
        if display_enabled:
            cv2.destroyAllWindows()
        try:
            pygame.mixer.quit()
        except:
            pass

    # -----------------------------------
    # EXPORT SUMMARY DATA
    # -----------------------------------
    # -----------------------------------
    # EXPORT SUMMARY DATA
    # -----------------------------------
    print("\n" + "=" * 50)
    print("Detection Completed")
    print("=" * 50)
    print(f"Frames Processed           : {frame_count}")
    print(f"Peak Concurrent Workers    : {peak_workers}")
    print(f"Peak Helmet Violations     : {peak_helmet_violations}")
    print(f"Peak Vest Violations : {peak_vest_violations}")
    print(f"Peak Danger Zone Entries   : {peak_danger_zone_entries}")

    payload = {
        "video_name": video_name,
        "total_records": peak_workers,
        "helmet_violations": peak_helmet_violations,
        "vest_violations": peak_vest_violations,
        "danger_zone_entries": peak_danger_zone_entries,
        "violations": []  # Combined your two duplicate payload structures here
    }
    
    # send_to_backend(args.api_url, payload)
    
    with open("results.json", "w") as f:
        json.dump(payload, f, indent=4)

    print("Dashboard Updated Successfully")
    print(f"\nProcessed video successfully generated at: {output_path}")
    print("Results saved to results.json")


if __name__ == "__main__":
    main()

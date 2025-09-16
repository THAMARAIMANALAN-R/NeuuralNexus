import subprocess
import json
import sys
from pathlib import Path
import re
import os
from diffusers import StableDiffusionPipeline
import torch
from moviepy import ImageClip, concatenate_videoclips   # ✅ fixed import

# -----------------------------
# 1️⃣ Read manuscript
# -----------------------------
MANUSCRIPT_PATH = Path("manuscript.txt")

if not MANUSCRIPT_PATH.exists():
    print(f"Error: {MANUSCRIPT_PATH} not found.")
    sys.exit(1)

with open(MANUSCRIPT_PATH, "r", encoding="utf-8") as f:
    manuscript_text = f.read().strip()

if not manuscript_text:
    print("Error: manuscript.txt is empty.")
    sys.exit(1)

# -----------------------------
# 2️⃣ Generate scenes using Ollama
# -----------------------------
prompt = f"""
You are a professional script writer. Based on the following manuscript, generate a JSON array of scenes.
Each scene should be an object with a "text" field containing the scene description.
Do NOT include any extra text outside the JSON array.

Manuscript:
{manuscript_text}

Output ONLY valid JSON.
"""

try:
    result = subprocess.run(
        ["ollama", "run", "gemma3:4b"],  # adjust your model name if needed
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True
    )
except subprocess.CalledProcessError as e:
    print("Error calling Ollama:", e)
    print("Ollama stderr:", e.stderr)
    sys.exit(1)

raw_output = result.stdout.strip()
print("Raw Ollama output:", raw_output)

# Extract JSON array
try:
    match = re.search(r"\[.*\]", raw_output, re.DOTALL)
    if not match:
        raise ValueError("No JSON array found in Ollama output.")
    
    scenes = json.loads(match.group(0))
except (json.JSONDecodeError, ValueError) as e:
    print(f"Error parsing JSON: {e}")
    sys.exit(1)

# Assign scene numbers if missing
for i, scene in enumerate(scenes, start=1):
    if "scene_number" not in scene:
        scene["scene_number"] = i

# -----------------------------
# 3️⃣ Generate images using Stable Diffusion
# -----------------------------
os.makedirs("scene_images", exist_ok=True)
os.makedirs("video_output", exist_ok=True)

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16
).to("cuda")  # Use "cpu" if no GPU

image_paths = []
for scene in scenes:
    scene_number = scene["scene_number"]
    text = scene["text"]
    print(f"🎨 Generating image for Scene {scene_number}: {text}")
    
    image = pipe(text).images[0]
    img_path = f"scene_images/scene_{scene_number}.png"
    image.save(img_path)
    image_paths.append(img_path)

# -----------------------------
# 4️⃣ Create silent video from images
# -----------------------------
clips = []
for img_path in image_paths:
    clip = ImageClip(img_path).set_duration(3)  # 3 sec per scene
    clips.append(clip)

video = concatenate_videoclips(clips, method="compose")
video.write_videofile("video_output/final_video.mp4", fps=24)

print("✅ Video generated at video_output/final_video.mp4")

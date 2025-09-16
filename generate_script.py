import subprocess
import json
import sys
from pathlib import Path
import re

# Path to your manuscript
MANUSCRIPT_PATH = Path("manuscript.txt")

# Check if manuscript exists
if not MANUSCRIPT_PATH.exists():
    print(f"Error: {MANUSCRIPT_PATH} not found.")
    sys.exit(1)

# Read the manuscript
with open(MANUSCRIPT_PATH, "r", encoding="utf-8") as f:
    manuscript_text = f.read().strip()

if not manuscript_text:
    print("Error: manuscript.txt is empty.")
    sys.exit(1)

# Prompt for Ollama
prompt = f"""
You are a professional script writer. Based on the following manuscript, generate a JSON array of scenes.
Each scene should be an object with a "text" field containing the scene description.
Do NOT include any extra text outside the JSON array.

Manuscript:
{manuscript_text}

Output ONLY valid JSON.
"""

try:
    # Call Ollama CLI (pass prompt via stdin, no --prompt flag)
    result = subprocess.run(
        ["ollama", "run", "gemma3:4b"],
        input=prompt,
        capture_output=True,
        text=True,
        check=True
    )
except subprocess.CalledProcessError as e:
    print("Error calling Ollama:", e)
    print("Ollama stderr:", e.stderr)
    sys.exit(1)

# Ollama output
raw_output = result.stdout.strip()
print("Raw Ollama output:", raw_output)

# Extract JSON array in case of extra text
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

# Print the scenes
print("\nGenerated Scenes:")
for scene in scenes:
    print(f"Scene {scene['scene_number']}: {scene['text']}\n")
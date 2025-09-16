import os
import subprocess
import math
import json

# ---------------- CONFIG ----------------
base_dir = r"C:\Users\rtham\sih-sample"
images_dir = os.path.join(base_dir, "images")     # Images should be saved here
audio_dir = os.path.join(base_dir, "audio")       # Scene audio files
output_dir = os.path.join(base_dir, "outputs")    # Final videos
os.makedirs(output_dir, exist_ok=True)

scene_script_file = os.path.join(base_dir, "scene_script.json")  # Generated scripts

image_duration = 2  # Default seconds per image
final_videos = []

# ---------------- LOAD SCENE DESCRIPTIONS ----------------
with open(scene_script_file, "r", encoding="utf-8") as f:
    scene_scripts = json.load(f)

# ---------------- CREATE VIDEO FOR EACH SCENE ----------------
for scene in scene_scripts:
    scene_number = scene["scene_number"]
    description = scene["description"]
    output_file = f"scene{scene_number}_final.mp4"

    # Assume images are named scene1_1.png, scene1_2.png, etc.
    scene_images = sorted([img for img in os.listdir(images_dir) if f"scene{scene_number}_" in img.lower()])
    if not scene_images:
        print(f"WARNING: No images found for Scene {scene_number}, skipping...")
        continue

    total_duration = len(scene_images) * image_duration

    # Create FFmpeg image list
    img_list_file = os.path.join(output_dir, f"scene{scene_number}_images.txt")
    with open(img_list_file, "w") as f:
        for img in scene_images:
            img_path = os.path.join(images_dir, img).replace("\\", "/")
            f.write(f"file '{img_path}'\n")
            f.write(f"duration {image_duration}\n")
        # Repeat last image
        last_img_path = os.path.join(images_dir, scene_images[-1]).replace("\\", "/")
        f.write(f"file '{last_img_path}'\n")

    # Audio for this scene
    audio_file = os.path.join(audio_dir, f"s{scene_number}.mp3")
    if not os.path.exists(audio_file):
        print(f"WARNING: Audio for Scene {scene_number} not found, skipping...")
        continue

    # Get audio duration
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_file],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    try:
        audio_duration = float(result.stdout.strip())
    except ValueError:
        print(f"WARNING: Could not get audio duration for Scene {scene_number}, skipping...")
        continue

    loop_count = max(1, math.ceil(total_duration / audio_duration))

    final_scene_path = os.path.join(output_dir, output_file)
    final_videos.append(final_scene_path)

    # FFmpeg command: images + looped audio -> scene video
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", img_list_file,
        "-stream_loop", str(loop_count - 1),
        "-i", audio_file,
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,"
               "pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1",
        "-pix_fmt", "yuv420p",
        "-shortest",
        final_scene_path
    ]

    print(f"Processing Scene {scene_number} -> {output_file} ...")
    subprocess.run(cmd, check=True)

# ---------------- MERGE SCENES ----------------
if final_videos:
    merge_list_file = os.path.join(output_dir, "merge_list.txt")
    with open(merge_list_file, "w") as f:
        for vid in final_videos:
            f.write(f"file '{vid.replace('\\', '/')}'\n")

    final_output = os.path.join(output_dir, "final_video.mp4")
    cmd_merge = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", merge_list_file,
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        final_output
    ]

    print("Merging all scenes into final video with audio...")
    subprocess.run(cmd_merge, check=True)
    print(f"Done! Final video created at: {final_output}")
else:
    print("No scenes were processed. Final video not created.")

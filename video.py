import os
import subprocess
import math

# --- CONFIG ---
base_dir = r"C:\Users\rtham\sih-sample"
images_dir = os.path.join(base_dir, "images")
audio_dir = os.path.join(base_dir, "audio")
output_dir = os.path.join(base_dir, "outputs")
os.makedirs(output_dir, exist_ok=True)

# (scene text file, audio file, final scene output)
scenes = [
    ("scene1.txt", "s1.mp3", "scene1_final.mp4"),
    ("scene2.txt", "s2.mp3", "scene2_final.mp4"),
    ("scene3.txt", "s3.mp3", "scene3_final.mp4"),
]

image_duration = 2  # seconds per image
final_videos = []

for scene_txt, audio_file, output_file in scenes:
    # Read image filenames from scene text file
    scene_txt_path = os.path.join(base_dir, scene_txt)
    if not os.path.exists(scene_txt_path):
        print(f"WARNING: {scene_txt} not found, skipping...")
        continue

    with open(scene_txt_path, "r") as f:
        scene_images = [line.strip() for line in f.readlines() if line.strip()]

    if not scene_images:
        print(f"WARNING: {scene_txt} is empty, skipping...")
        continue

    # Total duration of the scene
    total_duration = len(scene_images) * image_duration

    # Create temporary FFmpeg list file for images
    img_list_file = os.path.join(output_dir, f"{scene_txt[:-4]}_images.txt")
    with open(img_list_file, "w") as f:
        for img in scene_images:
            img_path = os.path.join(images_dir, img).replace("\\", "/")
            f.write(f"file '{img_path}'\n")
            f.write(f"duration {image_duration}\n")
        # Repeat last image to hold it
        last_img_path = os.path.join(images_dir, scene_images[-1]).replace("\\", "/")
        f.write(f"file '{last_img_path}'\n")

    # Get audio duration
    audio_path = os.path.join(audio_dir, audio_file)
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    try:
        audio_duration = float(result.stdout.strip())
    except ValueError:
        print(f"WARNING: Could not get duration for {audio_file}, skipping...")
        continue

    # Loop audio if shorter than scene duration
    loop_count = max(1, math.ceil(total_duration / audio_duration))

    final_scene = os.path.join(output_dir, output_file)

    # FFmpeg command: images + looped audio -> scene video
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", img_list_file,
        "-stream_loop", str(loop_count - 1),
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,"
               "pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1",
        "-pix_fmt", "yuv420p",
        "-shortest",
        final_scene
    ]

    print(f"Processing {scene_txt} -> {output_file} ...")
    subprocess.run(cmd, check=True)
    final_videos.append(final_scene)

# --- Merge all scenes into one final video ---
if final_videos:
    merge_list_file = os.path.join(output_dir, "merge_list.txt")
    with open(merge_list_file, "w") as f:
        for video in final_videos:
            f.write(f"file '{video.replace('\\', '/')}'\n")

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

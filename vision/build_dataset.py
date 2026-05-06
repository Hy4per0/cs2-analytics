import os

from frame_extractor import extract_frames

CLIPS_FOLDER = "vision/clips"
OUTPUT_FOLDER = "vision/frames"


def build_dataset():

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    for file in os.listdir(CLIPS_FOLDER):
        if not file.endswith(".mp4"):
            continue

        video_path = os.path.join(CLIPS_FOLDER, file)

        name = os.path.splitext(file)[0]

        out_folder = os.path.join(OUTPUT_FOLDER, name)

        extract_frames(video_path, out_folder)


if __name__ == "__main__":
    build_dataset()

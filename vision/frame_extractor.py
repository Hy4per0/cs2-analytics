import cv2
import os


def extract_frames(video_path, output_folder, fps=5):

    os.makedirs(output_folder, exist_ok=True)

    cap = cv2.VideoCapture(video_path)

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(video_fps / fps)

    frame_count = 0
    saved_count = 0

    while True:

        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:

            filename = f"{saved_count:06d}.jpg"
            path = os.path.join(output_folder, filename)

            cv2.imwrite(path, frame)
            saved_count += 1

        frame_count += 1

    cap.release()

    print(f"Saved {saved_count} frames from {video_path}")
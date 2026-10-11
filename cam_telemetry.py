import cv2
import numpy as np
import json

def analyze_camera_behavior(video_source, output_json_path, sample_rate=1):
    """
    Analyzes a game video stream to extract camera angle rotation, visual stimulus 
    density, and behavioral style profiles (acceleration, smoothness, jerk).
    """
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        raise IOError(f"Error opening video source: {video_source}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    feature_params = dict(maxCorners=120, qualityLevel=0.2, minDistance=10, blockSize=7)
    lk_params = dict(
        winSize=(21, 21),
        maxLevel=3,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 15, 0.02)
    )

    ret, old_frame = cap.read()
    if not ret:
        return

    h, w, _ = old_frame.shape
    center_x, center_y = w / 2.0, h / 2.0
    old_gray = cv2.cvtColor(old_frame, cv2.COLOR_BGR2GRAY)
    p0 = cv2.goodFeaturesToTrack(old_gray, mask=None, **feature_params)

    telemetry_records = []
    prev_angular_velocity = 0.0
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        if frame_idx % sample_rate != 0:
            continue

        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 1. Calculate visual stimulus (frame difference / local motion density)
        frame_diff = cv2.absdiff(old_gray, frame_gray)
        visual_stimulus = float(np.mean(frame_diff))

        angular_velocity = 0.0
        magnitude = 0.0

        if p0 is not None and len(p0) > 0:
            p1, st, err = cv2.calcOpticalFlowPyrLK(old_gray, frame_gray, p0, None, **lk_params)
            if p1 is not None:
                good_new = p1[st == 1]
                good_old = p0[st == 1]

                if len(good_new) > 6:
                    # Calculate rotational angle change (proxy for camera angle/yaw/pitch shifts)
                    # Vector from center to points
                    vec_old = good_old - np.array([center_x, center_y])
                    vec_new = good_new - np.array([center_x, center_y])
                    
                    angles_old = np.arctan2(vec_old[:, 1], vec_old[:, 0])
                    angles_new = np.arctan2(vec_new[:, 1], vec_new[:, 0])
                    
                    angle_diffs = angles_new - angles_old
                    # Normalize angles between -pi and pi
                    angle_diffs = (angle_diffs + np.pi) % (2 * np.pi) - np.pi
                    
                    angular_velocity = float(np.mean(angle_diffs) * (180.0 / np.pi))
                    
                    displacements = good_new - good_old
                    magnitude = float(np.mean(np.linalg.norm(displacements, axis=1)))

                p0 = good_new.reshape(-1, 1, 2)
            else:
                p0 = cv2.goodFeaturesToTrack(frame_gray, mask=None, **feature_params)
        else:
            p0 = cv2.goodFeaturesToTrack(frame_gray, mask=None, **feature_params)

        # 2. Behavioral style metrics (Acceleration / Jerk / Smoothing tendency)
        acceleration = angular_velocity - prev_angular_velocity
        prev_angular_velocity = angular_velocity

        # Heuristic style classification proxy based on response profile
        if abs(angular_velocity) > 15.0:
            behavior_style = "Aggressive Snap"
        elif abs(angular_velocity) < 2.0 and visual_stimulus > 12.0:
            behavior_style = "Fixed Observation / Target Lock"
        else:
            behavior_style = "Smooth Cinematic Glide"

        telemetry_records.append({
            "frame": frame_idx,
            "timestamp_sec": round(frame_idx / fps, 3),
            "angular_velocity_deg_s": round(angular_velocity, 3),
            "motion_magnitude": round(magnitude, 3),
            "visual_stimulus_index": round(visual_stimulus, 3),
            "acceleration": round(acceleration, 3),
            "style_classification": behavior_style
        })

        old_gray = frame_gray.copy()

    cap.release()

    with open(output_json_path, 'w') as f:
        json.dump(telemetry_records, f, indent=4)

if __name__ == "__main__":
    pass

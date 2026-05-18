import cv2
import mediapipe as mp

class HandTracker:
    def __init__(self, max_hands = 1, complexity = 0, det_conf = 0.6, track_conf = 0.6):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            max_num_hands = max_hands,
            model_complexity = complexity,
            min_detection_confidence = det_conf,
            min_tracking_confidence = track_conf
        )

    def process(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return self.hands.process(rgb_frame)

    def draw(self, frame, hand_landmarks):
        self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
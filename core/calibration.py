import time
import cv2
import numpy as np

class CalibrationManager:
    def __init__(self):
        self.is_active = False
        self.step = 0
        self.start_time = 0
        self.prep_time = 2.0
        self.scan_time = 4.0
        self.open_data = []
        self.calib_data = []

        # 🚀 2D 픽셀 거리 기반 표준 임계값 (롤백)
        self.on_threshold = 0.15
        self.off_threshold = 0.25

    def start(self):
        print("🔧 [캘리브레이션] 2D 영점 조절 시작")
        self.is_active = True
        self.step = 1
        self.start_time = time.time() + self.prep_time
        self.open_data = []
        self.calib_data = []

    def update(self, frame, index_pinch_ratio):
        h, w, _ = frame.shape
        current_time = time.time()

        # 1. 준비 단계
        if current_time < self.start_time:
            msg = "Ready... OPEN Hand" if self.step == 1 else "Ready... PINCH Fingers"
            cv2.putText(frame, msg, (w//2 - 200, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
            return

        # 2. 데이터 수집
        elapsed = current_time - self.start_time
        self.calib_data.append(index_pinch_ratio)
        
        progress = min(1.0, elapsed / self.scan_time)
        cv2.rectangle(frame, (w//2-250, h//2+50), (w//2-250 + int(500*progress), h//2+70), (0, 255, 0), -1)

        # 3. 분석
        if elapsed > self.scan_time:
            data = np.array(self.calib_data)
            self.calib_data = []

            if self.step == 1:
                self.open_data = data
                self.step = 2
                self.start_time = time.time() + self.prep_time
            else:
                open_low = np.percentile(self.open_data, 10)
                pinch_high = np.percentile(data, 90)

                if open_low <= pinch_high:
                    print("❌ 오류: 동작 구분이 불명확합니다.")
                else:
                    gap = open_low - pinch_high
                    self.on_threshold = pinch_high + (gap * 0.2)
                    self.off_threshold = open_low - (gap * 0.2)
                    print(f"✅ 2D 영점 조절 완료! [ON: {self.on_threshold:.3f} / OFF: {self.off_threshold:.3f}]")
                
                self.is_active = False

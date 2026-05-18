import math
import numpy as np
import pyautogui
import time
from pynput.mouse import Controller, Button
import cv2

from core.filter import OneEuroFilter
from core.calibration import CalibrationManager

# ==========================================
# 🚀 메인 컨트롤러 (2D 안정화 버전 - 롤백)
# ==========================================
class MouseController:
    def __init__(self, drag_delay=0.25, double_click_threshold=0.3):
        self.mouse = Controller()
        self.screen_w, self.screen_h = pyautogui.size()
        
        self.drag_delay = drag_delay
        self.double_click_threshold = double_click_threshold
        self.frame_margin = 100

        self.prev_x, self.prev_y = 0, 0
        self.curr_x, self.curr_y = 0, 0
        
        self.is_pinching = False
        self.drag_mode = False
        self.pinch_start_time = 0
        self.locked_x, self.locked_y = 0, 0
        
        self.is_right_pinching = False
        self.last_click_time = 0

        # 모듈 인스턴스화
        self.calib_manager = CalibrationManager()
        # 1유로 필터 세팅
        self.filter_x = OneEuroFilter(mincutoff=0.5, beta=0.01)
        self.filter_y = OneEuroFilter(mincutoff=0.5, beta=0.01)

    def process_landmarks(self, frame, hand_landmarks, show_debug):
        h, w, _ = frame.shape
        
        # 1. 2D 랜드마크 추출 (픽셀 좌표)
        wrist = hand_landmarks.landmark[0]
        index_mcp = hand_landmarks.landmark[5]
        thumb_tip = hand_landmarks.landmark[4]
        index_tip = hand_landmarks.landmark[8]
        middle_tip = hand_landmarks.landmark[12]

        mcp_x, mcp_y = int(index_mcp.x * w), int(index_mcp.y * h)
        wrist_x, wrist_y = int(wrist.x * w), int(wrist.y * h)
        thumb_x, thumb_y = int(thumb_tip.x * w), int(thumb_tip.y * h)
        index_x, index_y = int(index_tip.x * w), int(index_tip.y * h)
        middle_x, middle_y = int(middle_tip.x * w), int(middle_tip.y * h)

        # 커서 기준점
        cursor_x, cursor_y = mcp_x, mcp_y

        # 2. 비율 연산 (2D 픽셀 거리 기준)
        base_dist = math.hypot(mcp_x - wrist_x, mcp_y - wrist_y)
        if base_dist == 0: base_dist = 1 

        index_pinch_dist = math.hypot(index_x - thumb_x, index_y - thumb_y)
        middle_pinch_dist = math.hypot(middle_x - thumb_x, middle_y - thumb_y)

        index_pinch_ratio = index_pinch_dist / base_dist
        middle_pinch_ratio = middle_pinch_dist / base_dist

        # 3. 캘리브레이션 중이면 매니저에게 제어권 위임
        if self.calib_manager.is_active:
            self.calib_manager.update(frame, index_pinch_ratio)
            return 

        # 4. 실시간 임계값 가져오기
        dynamic_on = self.calib_manager.on_threshold
        dynamic_off = self.calib_manager.off_threshold

        # 5. 지수형 가변 브레이크 (2D 최적화)
        if self.drag_mode:
            brake_factor = 0.0
        else:
            ratio_clamped = max(dynamic_on, min(dynamic_off, index_pinch_ratio))
            linear_factor = 1.0 - ((ratio_clamped - dynamic_on) / (dynamic_off - dynamic_on + 0.0001))
            brake_factor = math.pow(linear_factor, 2) 
        
        # 6. 커서 스무딩 및 이동
        current_time = time.time()
        raw_screen_x = np.interp(cursor_x, (self.frame_margin, w - self.frame_margin), (0, self.screen_w))
        raw_screen_y = np.interp(cursor_y, (self.frame_margin, h - self.frame_margin), (0, self.screen_h))

        self.filter_x.mincutoff = 1.5 - (brake_factor * 1.49)
        self.filter_y.mincutoff = 1.5 - (brake_factor * 1.49)
        
        smoothed_x = self.filter_x(current_time, raw_screen_x)
        smoothed_y = self.filter_y(current_time, raw_screen_y)

        # 동적 데드존
        dynamic_deadzone = 2.0 + (brake_factor * 8.0)
        if math.hypot(smoothed_x - self.prev_x, smoothed_y - self.prev_y) < dynamic_deadzone:
            smoothed_x, smoothed_y = self.prev_x, self.prev_y

        target_x, target_y = int(smoothed_x), int(smoothed_y)

        # 7. 마우스 이벤트 핸들링
        self._handle_left_click(index_pinch_ratio, dynamic_on, dynamic_off, target_x, target_y)
        self._handle_right_click(middle_pinch_ratio, dynamic_on)

        # 8. 최종 좌표 결정
        if self.is_pinching and not self.drag_mode:
            self.curr_x, self.curr_y = self.locked_x, self.locked_y
        else:
            self.curr_x, self.curr_y = target_x, target_y

        self.mouse.position = (self.curr_x, self.curr_y)
        self.prev_x, self.prev_y = self.curr_x, self.curr_y

        # 디버그 UI
        if show_debug:
            self._draw_debug_ui(frame, index_pinch_ratio, dynamic_on, dynamic_off, brake_factor)

    def _handle_left_click(self, ratio, on_th, off_th, tx, ty):
        if not self.is_pinching and ratio < on_th:
            self.is_pinching = True
            self.pinch_start_time = time.time()
            self.locked_x, self.locked_y = tx, ty

        elif self.is_pinching and ratio > off_th:
            if self.drag_mode:
                self.mouse.release(Button.left)
            else:
                self.mouse.position = (self.locked_x, self.locked_y)
                if (time.time() - self.last_click_time) < self.double_click_threshold:
                    self.mouse.click(Button.left, 2)
                    self.last_click_time = 0
                else:
                    self.mouse.click(Button.left, 1)
                    self.last_click_time = time.time()
            self.is_pinching = False
            self.drag_mode = False

        elif self.is_pinching:
            if not self.drag_mode and (time.time() - self.pinch_start_time) >= self.drag_delay:
                self.drag_mode = True
                self.mouse.position = (self.locked_x, self.locked_y)
                self.mouse.press(Button.left)

    def _handle_right_click(self, ratio, on_th):
        if ratio < on_th and not self.is_pinching:
            if not self.is_right_pinching:
                self.is_right_pinching = True
                self.mouse.click(Button.right, 1)
        else:
            self.is_right_pinching = False

    def _draw_debug_ui(self, frame, ratio, on_th, off_th, brake):
        color = (0, 255, 0) if self.is_pinching else (0, 0, 255)
        status = "DRAGGING" if self.drag_mode else ("PINCHED" if self.is_pinching else "RELEASED")
        cv2.putText(frame, f"STATUS: {status} ({ratio:.2f})", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(frame, f"Brake: {int(brake*100)}%", (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, f"ON: {on_th:.2f} / OFF: {off_th:.2f}", (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    def reset_state(self):
        if self.is_pinching and self.drag_mode:
            self.mouse.release(Button.left)
        self.is_pinching = False
        self.drag_mode = False
        self.is_right_pinching = False
        self.filter_x.reset()
        self.filter_y.reset()

    def adjust_thresholds(self, key):
        step = 0.02
        if key == ord('c'): self.calib_manager.start()
        elif key == ord('w'): self.calib_manager.on_threshold += step
        elif key == ord('s'): self.calib_manager.on_threshold -= step
        elif key == ord('e'): self.calib_manager.off_threshold += step
        elif key == ord('d'): self.calib_manager.off_threshold -= step

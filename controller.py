import math
import numpy as np
import pyautogui
import time
from pynput.mouse import Controller, Button
import cv2

class MouseController:
    def __init__(self, smoothing_factor=2, drag_delay=0.25, double_click_threshold=0.3):
        self.mouse = Controller()
        self.screen_w, self.screen_h = pyautogui.size()
        
        self.smoothing_factor = smoothing_factor
        self.drag_delay = drag_delay
        self.double_click_threshold = double_click_threshold
        self.frame_margin = 100

        self.prev_x, self.prev_y = 0, 0
        self.is_pinching = False
        self.drag_mode = False
        self.pinch_start_time = 0
        self.locked_x, self.locked_y = 0, 0
        
        self.is_right_pinching = False
        self.locked_right_x, self.locked_right_y = 0, 0
        self.last_click_time = 0

        # 초기 기본 임계값
        self.click_on_threshold = 0.15
        self.click_off_threshold = 0.25
        self.right_click_threshold = 0.15

        # 🚀 [자동 캘리브레이션용 상태 변수]
        self.is_calibrating = False
        self.calib_step = 0
        self.calib_start_time = 0
        self.calib_data = []
        self.relaxed_ratio_avg = 0
        self.pinch_ratio_avg = 0

    # 🚀 [추가됨] 자동 캘리브레이션 시작 함수
    def start_calibration(self):
        print("🔧 자동 캘리브레이션 프로세스 시작")
        self.is_calibrating = True
        self.calib_step = 1 # 1단계: 편안한 손 (Open)
        self.calib_start_time = time.time() + 1.5 # 1.5초 대기 후 측정 시작
        self.calib_data = []

    def process_landmarks(self, frame, hand_landmarks, show_debug):
        h, w, _ = frame.shape
        
        if show_debug:
            cv2.rectangle(frame, (self.frame_margin, self.frame_margin), 
                         (w - self.frame_margin, h - self.frame_margin), (255, 0, 255), 2)

        wrist = hand_landmarks.landmark[0]
        index_mcp = hand_landmarks.landmark[5]
        thumb_tip = hand_landmarks.landmark[4]
        index_tip = hand_landmarks.landmark[8]
        middle_tip = hand_landmarks.landmark[12]

        wrist_x, wrist_y = int(wrist.x * w), int(wrist.y * h)
        mcp_x, mcp_y = int(index_mcp.x * w), int(index_mcp.y * h)
        thumb_x, thumb_y = int(thumb_tip.x * w), int(thumb_tip.y * h)
        index_x, index_y = int(index_tip.x * w), int(index_tip.y * h)
        middle_x, middle_y = int(middle_tip.x * w), int(middle_tip.y * h)

        cursor_x = mcp_x
        cursor_y = mcp_y

        base_dist = math.hypot(mcp_x - wrist_x, mcp_y - wrist_y)
        if base_dist == 0: base_dist = 1 

        index_pinch_dist = math.hypot(index_x - thumb_x, index_y - thumb_y)
        middle_pinch_dist = math.hypot(middle_x - thumb_x, middle_y - thumb_y)

        index_pinch_ratio = index_pinch_dist / base_dist
        middle_pinch_ratio = middle_pinch_dist / base_dist

        # ==========================================
        # 🚀 [핵심] 캘리브레이션 모드일 때의 동작 가로채기
        # ==========================================
        if self.is_calibrating:
            current_time = time.time()
            # 1. 준비 시간 (1.5초 대기)
            if current_time < self.calib_start_time:
                msg = "Ready... Open Hand (Relax)" if self.calib_step == 1 else "Ready... Pinch Fingers (Click)"
                color = (0, 255, 255)
                cv2.putText(frame, msg, (w//2 - 200, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)
            # 2. 측정 시간 (1.5초간 데이터 수집)
            else:
                elapsed = current_time - self.calib_start_time
                self.calib_data.append(index_pinch_ratio)
                
                msg = f"Scanning {'OPEN' if self.calib_step==1 else 'PINCH'}: {1.5 - elapsed:.1f}s"
                cv2.putText(frame, msg, (w//2 - 150, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

                # 1.5초 측정이 끝나면 다음 단계로
                if elapsed > 1.5:
                    avg_ratio = sum(self.calib_data) / len(self.calib_data)
                    self.calib_data = []
                    
                    if self.calib_step == 1:
                        self.relaxed_ratio_avg = avg_ratio
                        print(f"👉 편안한 손 비율 측정 완료: {self.relaxed_ratio_avg:.3f}")
                        self.calib_step = 2
                        self.calib_start_time = time.time() + 1.5 # 다음 단계 준비 시간
                    else:
                        self.pinch_ratio_avg = avg_ratio
                        print(f"👉 클릭한 손 비율 측정 완료: {self.pinch_ratio_avg:.3f}")
                        
                        # 3. [최종 수학적 계산] 최적의 임계값 도출
                        diff = self.relaxed_ratio_avg - self.pinch_ratio_avg
                        if diff > 0.05: # 정상적으로 측정되었을 경우
                            # 누르는 기준: 꼬집은 상태에서 살짝만 풀려도 됨 (범위의 30%)
                            self.click_on_threshold = self.pinch_ratio_avg + (diff * 0.3)
                            # 떼는 기준: 꼬집은 상태에서 꽤 많이 풀어야 됨 (범위의 70%)
                            self.click_off_threshold = self.pinch_ratio_avg + (diff * 0.7)
                            self.right_click_threshold = self.click_on_threshold
                            print(f"✅ 설정 완료! ON: {self.click_on_threshold:.3f}, OFF: {self.click_off_threshold:.3f}")
                        else:
                            print("❌ 측정 오류: 손의 움직임이 너무 적습니다. 기존 값을 유지합니다.")
                            
                        self.is_calibrating = False

            # 캘리브레이션 중에는 마우스가 움직이지 않도록 여기서 함수를 종료합니다.
            return
        # ==========================================

        dynamic_on_threshold = self.click_on_threshold
        dynamic_off_threshold = self.click_off_threshold

        # OSD UI 출력
        if show_debug:
            state_color = (0, 255, 0) if self.is_pinching else (0, 0, 255)
            state_text = "CLICKED" if self.is_pinching else "RELEASED"
            
            cv2.putText(frame, f"State: {state_text} (Ratio: {index_pinch_ratio:.2f})", 
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, state_color, 2)
            cv2.putText(frame, f"ON Thresh : {dynamic_on_threshold:.2f}", 
                        (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame, f"OFF Thresh: {dynamic_off_threshold:.2f}", 
                        (20, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            # 🚀 [가이드 추가] C를 누르면 자동 측정 시작
            cv2.putText(frame, "[Press 'C' for Auto-Calibration]", 
                        (20, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        # 스무딩 및 목표 좌표 연산
        screen_x = np.interp(cursor_x, (self.frame_margin, w - self.frame_margin), (0, self.screen_w))
        screen_y = np.interp(cursor_y, (self.frame_margin, h - self.frame_margin), (0, self.screen_h))

        move_distance = math.hypot(screen_x - self.prev_x, screen_y - self.prev_y)

        deadzone_threshold = 5.0
        if move_distance < deadzone_threshold:
            screen_x, screen_y = self.prev_x, self.prev_y
            move_distance = 0

        dynamic_smooth = 7.0 if move_distance < 20 else 2.0

        target_x = self.prev_x + (screen_x - self.prev_x) / dynamic_smooth
        target_y = self.prev_y + (screen_y - self.prev_y) / dynamic_smooth

        self._handle_left_click(frame, cursor_x, cursor_y, index_pinch_ratio, 
                                dynamic_on_threshold, dynamic_off_threshold, 
                                target_x, target_y, show_debug)
        self._handle_right_click(frame, thumb_x, thumb_y, middle_x, middle_y, 
                                 middle_pinch_ratio, self.right_click_threshold, show_debug)

        self.mouse.position = (self.curr_x, self.curr_y)
        self.prev_x, self.prev_y = self.curr_x, self.curr_y

    def _handle_left_click(self, frame, center_x, center_y, index_pinch_ratio, on_threshold, off_threshold, target_x, target_y, show_debug):
        if show_debug:
            color = (0, 255, 0) if self.is_pinching else (0, 0, 255)
            cv2.circle(frame, (center_x, center_y), 10, color, cv2.FILLED)

        if not self.is_pinching and index_pinch_ratio < on_threshold:
            self.is_pinching = True
            self.pinch_start_time = time.time()
            self.locked_x, self.locked_y = self.prev_x, self.prev_y
            self.curr_x, self.curr_y = self.locked_x, self.locked_y 

        elif self.is_pinching and index_pinch_ratio > off_threshold:
            if self.drag_mode:
                self.mouse.release(Button.left)
            else:
                self.mouse.position = (self.locked_x, self.locked_y)
                current_time = time.time()
                if current_time - self.last_click_time < self.double_click_threshold:
                    self.mouse.click(Button.left, 2)
                    self.last_click_time = 0
                else:
                    self.mouse.click(Button.left, 1)
                    self.last_click_time = current_time
            
            self.is_pinching = False
            self.drag_mode = False
            self.curr_x, self.curr_y = target_x, target_y

        elif self.is_pinching:
            if not self.drag_mode and (time.time() - self.pinch_start_time) >= self.drag_delay:
                self.drag_mode = True
                self.mouse.position = (self.locked_x, self.locked_y)
                self.mouse.press(Button.left)
            
            self.curr_x, self.curr_y = (target_x, target_y) if self.drag_mode else (self.locked_x, self.locked_y)

        else:
            self.curr_x, self.curr_y = target_x, target_y

    def _handle_right_click(self, frame, thumb_x, thumb_y, middle_x, middle_y, middle_pinch_ratio, threshold, show_debug):
        if middle_pinch_ratio < threshold and not self.is_pinching:
            if not self.is_right_pinching:
                self.is_right_pinching = True
                self.locked_right_x, self.locked_right_y = self.prev_x, self.prev_y
                self.mouse.position = (self.locked_right_x, self.locked_right_y)
                self.mouse.click(Button.right, 1)
            self.curr_x, self.curr_y = self.locked_right_x, self.locked_right_y
        else:
            self.is_right_pinching = False

    def reset_state(self):
        if self.is_pinching and self.drag_mode:
            self.mouse.release(Button.left)
        self.is_pinching = False
        self.drag_mode = False
        self.is_right_pinching = False

    def adjust_thresholds(self, key):
        """수동 조절(W,S,E,D) 및 자동 조절(C) 호출"""
        step = 0.02
        if key == ord('c'): self.start_calibration() # 🚀 'C' 키 입력 시 자동 캘리브레이션 시작
        elif key == ord('w'): self.click_on_threshold = min(1.0, self.click_on_threshold + step)
        elif key == ord('s'): self.click_on_threshold = max(0.05, self.click_on_threshold - step)
        elif key == ord('e'): self.click_off_threshold = min(1.0, self.click_off_threshold + step)
        elif key == ord('d'): self.click_off_threshold = max(0.05, self.click_off_threshold - step)
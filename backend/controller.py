import math
import numpy as np
import pyautogui
import time
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
import cv2

from core.filter import OneEuroFilter
from core.calibration import CalibrationManager

# ==========================================================
# 🚀 메인 컨트롤러 v4.0 (Intelligent Context Hybrid Engine)
# ==========================================================
class MouseController:
    def __init__(self, drag_delay=0.25, double_click_threshold=0.3):
        # 🚀 [v8.0] Windows 고해상도 모니터 대응 DPI 스케일링 인식 설정
        import sys
        if sys.platform.startswith('win'):
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(2) # Per Monitor DPI Aware
            except Exception as e:
                pass
                
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self.gesture_cooldown = 0
        self.screen_w, self.screen_h = pyautogui.size()
        
        # 설정값
        self.drag_delay = drag_delay
        self.double_click_threshold = double_click_threshold
        self.frame_margin = 100

        # 상태 변수
        self.prev_x, self.prev_y = 0, 0
        self.prev_ratio = 0.5
        self.ratio_velocity = 0.0
        
        self.is_pinching = False
        self.drag_mode = False
        self.pinch_start_time = 0
        self.locked_x, self.locked_y = 0, 0
        self.last_click_time = 0
        self.is_right_pinching = False
        self.pinch_release_counter = 0

        # v4.0 신규 상태 변수
        self.is_scroll_mode = False
        self.scroll_start_y = 0
        self.prev_thumb_z = 0.0
        self.thumb_z_velocity = 0.0
        self.freeze_until = 0.0
        self.current_sensitivity = 1.0

        # [v6.0] Fluid Intelligence 상태 변수
        self.prev_raw_x, self.prev_raw_y = 0, 0
        self.vel_x, self.vel_y = 0.0, 0.0
        self.accel_x, self.vel_y = 0.0, 0.0 # 가속도 추적
        self.structural_integrity = 1.0     # 랜드마크 신뢰도 (1.0 = 완벽)
        self.base_bone_length = 0.0         # 기준 뼈 길이 (캘리브레이션 시 저장 가능하나 여기선 실시간 평균 대비)
        self.is_sticky_locked = False
        self.sticky_target_x, self.sticky_target_y = 0, 0

        self.calib_manager = CalibrationManager()
        self.filter_x = OneEuroFilter(mincutoff=0.5, beta=0.01)
        self.filter_y = OneEuroFilter(mincutoff=0.5, beta=0.01)

    # --- 3D 수학 유틸리티 ---
    def _calc_3d_dist(self, p1, p2):
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

    def _calc_angle_score(self, pip, tip, target):
        vx, vy, vz = tip.x - pip.x, tip.y - pip.y, tip.z - pip.z
        ux, uy, uz = target.x - pip.x, target.y - pip.y, target.z - pip.z
        dot = vx*ux + vy*uy + vz*uz
        mag_v = math.sqrt(vx**2 + vy**2 + vz**2)
        mag_u = math.sqrt(ux**2 + uy**2 + uz**2)
        if mag_v * mag_u == 0: return 0
        return dot / (mag_v * mag_u)

    def process_landmarks(self, frame, hand_landmarks, world_landmarks, show_debug):
        h, w, _ = frame.shape
        lm = hand_landmarks.landmark
        current_time = time.time()
        
        # 3D Metric 월드 랜드마크 추출 (Aspect Ratio 왜곡이 없는 실제 미터 단위 좌표)
        wlm = world_landmarks.landmark if world_landmarks is not None else hand_landmarks.landmark
        
        # 1. 기초 데이터 추출 (화면 좌표용)
        def to_px(l): return int(l.x * w), int(l.y * h)
        wx, wy = to_px(lm[0])
        tx, ty = to_px(lm[4])
        imx, imy = to_px(lm[5])
        ix, iy = to_px(lm[8])
        mx, my = to_px(lm[12])

        # [v8.0] 3D 회전 불변(3D Rotation-Invariant) 비율 계산 도입 (wlm 기반)
        d3_base = self._calc_3d_dist(wlm[5], wlm[0]) or 0.001
        index_ratio = self._calc_3d_dist(wlm[8], wlm[4]) / d3_base
        middle_ratio = self._calc_3d_dist(wlm[12], wlm[4]) / d3_base

        # 2. [v5.0] Intention Gate (조작 의도 판별 - wlm 기반)
        hand_dir_x = wlm[9].x - wlm[0].x
        hand_dir_y = wlm[9].y - wlm[0].y
        is_resting = (abs(hand_dir_x) > abs(hand_dir_y) * 1.5) or (hand_dir_y > 0)

        # 3. [v4.0] Z-Depth 분석 (엄지 돌진 속도 계산 - wlm 기반)
        dt = 0.033
        self.thumb_z_velocity = (wlm[4].z - self.prev_thumb_z) / dt
        self.prev_thumb_z = wlm[4].z

        # 3. [v3.0 하이브리드 코어] 트리플 체크 엔진 (wlm 기반)
        i_3d = min(self._calc_3d_dist(wlm[8], wlm[4]), self._calc_3d_dist(wlm[6], wlm[4])) / d3_base
        m_3d = self._calc_3d_dist(wlm[12], wlm[4]) / d3_base
        
        i_vec = self._calc_angle_score(wlm[6], wlm[8], wlm[4])
        m_vec = self._calc_angle_score(wlm[10], wlm[12], wlm[4])
        
        is_idx_extended = (self._calc_3d_dist(wlm[8], wlm[0]) / d3_base) > 1.7
        
        # 하이브리드 점수 산출
        i_score = i_3d + max(0, (0.8 - i_vec)) * 1.5
        m_score = m_3d + max(0, (0.8 - m_vec)) * 1.5
        
        if is_idx_extended:
            i_score += 3.0
            m_score -= 0.2
            
        # [v4.0] 가변 감도(DPI) 결정
        if not self.is_pinching:
            self.current_sensitivity = 1.2 if is_idx_extended else 0.5

        # 하이브리드 승자 판정
        is_idx_dom = i_score < (m_score - 0.1)
        is_mid_dom = m_score < (i_score - 0.1)
        
        # 🚀 [v8.3] 주먹 쥐기(Fist) 스크롤 모드 판정
        index_fold = self._calc_3d_dist(wlm[8], wlm[5]) / d3_base
        middle_fold = self._calc_3d_dist(wlm[12], wlm[9]) / d3_base
        ring_fold = self._calc_3d_dist(wlm[16], wlm[13]) / d3_base
        pinky_fold = self._calc_3d_dist(wlm[20], wlm[17]) / d3_base

        folded_count = 0
        if index_fold < 0.55: folded_count += 1
        if middle_fold < 0.55: folded_count += 1
        if ring_fold < 0.55: folded_count += 1
        if pinky_fold < 0.55: folded_count += 1

        is_fist = folded_count >= 3
        if self.is_pinching:
            is_fist = False

        # 🚀 [v8.4] 커스텀 제스처 (세 손가락 펴고 새끼접기 -> Mission Control)
        is_three_fingers = (index_fold > 0.6 and middle_fold > 0.6 and ring_fold > 0.6 and pinky_fold < 0.5)
        if is_three_fingers and current_time > self.gesture_cooldown:
            self.keyboard.press(Key.ctrl)
            self.keyboard.press(Key.up)
            self.keyboard.release(Key.up)
            self.keyboard.release(Key.ctrl)
            self.gesture_cooldown = current_time + 1.5 # 1.5초 쿨다운

        # 4. 캘리브레이션 및 인텐트 부스트
        if self.calib_manager.is_active:
            self.calib_manager.update(frame, index_ratio)
            return

        self.ratio_velocity = (index_ratio - self.prev_ratio) / dt
        self.prev_ratio = index_ratio

        # [v8.2] Release Boost (속도 기반 해제 가속) 및 드래그 탈출 마진 완화
        if self.is_pinching:
            # 드래그 중에는 1.4배의 마진을, 일반 핀치 유지 시에는 1.25배 마진을 적용하여 유지력을 보강합니다.
            drag_margin = 1.4 if self.drag_mode else 1.25
            
            # 손가락이 펴지는 속도가 빠를수록(ratio_velocity > 0.3) 해제 임계값을 일시적으로 낮춤 (Release Boost)
            # 노이즈로 튀어 조기 해제되는 오류를 방지하기 위해 가속 상한선(0.1)을 둡니다.
            release_boost = 0.0
            if self.ratio_velocity > 0.3:
                release_boost = min(0.1, self.ratio_velocity * 0.08)
                
            dynamic_on = self.calib_manager.on_threshold
            dynamic_off = (self.calib_manager.off_threshold * drag_margin) - release_boost
            
            # 해제 임계값 안전 가이드라인 (on_threshold보다는 크게 설정)
            dynamic_off = max(dynamic_off, self.calib_manager.on_threshold + 0.05)
        else:
            intent_boost = abs(self.ratio_velocity) * 0.05 if self.ratio_velocity < -0.5 else 0.0
            dynamic_on = self.calib_manager.on_threshold + intent_boost
            dynamic_off = self.calib_manager.off_threshold

        # 5. [v6.0] Fluid Coordination & Prediction
        # A. Structural Integrity Score (랜드마크 안정성 분석 - wlm 기반)
        current_bone = self._calc_3d_dist(wlm[0], wlm[5])
        if self.base_bone_length == 0: self.base_bone_length = current_bone
        self.structural_integrity = 1.0 - min(0.5, abs(current_bone - self.base_bone_length) / (self.base_bone_length + 1e-6))
        self.base_bone_length = self.base_bone_length * 0.95 + current_bone * 0.05

        # B. Predictive Kinematics (필터 지연 상쇄)
        raw_screen_x = np.interp(imx, (self.frame_margin, w-self.frame_margin), (0, self.screen_w))
        raw_screen_y = np.interp(imy, (self.frame_margin, h-self.frame_margin), (0, self.screen_h))
        
        inst_vel_x = (raw_screen_x - self.prev_raw_x) / dt
        inst_vel_y = (raw_screen_y - self.prev_raw_y) / dt
        self.prev_raw_x, self.prev_raw_y = raw_screen_x, raw_screen_y
        
        # 속도 및 가속도 기반 미래 위치 예측 (지연 보정)
        look_ahead = 0.045 # 약 45ms 앞을 내다봄 (필터 지연 시간과 유사하게 설정)
        pred_x = raw_screen_x + inst_vel_x * look_ahead
        pred_y = raw_screen_y + inst_vel_y * look_ahead
        
        # C. Sticky Targeting (정지 마찰력 강화) & Pinch Stabilization Lock (클릭 시 횡이동 튀는 현상 방지)
        # 속도가 낮을 때 마우스를 타겟에 살짝 '자석'처럼 붙게 함
        speed = math.hypot(inst_vel_x, inst_vel_y)
        viscosity = 1.0
        if speed < 150 and not self.drag_mode: # 느린 움직임 시
            viscosity = 0.3 # 70% 저항 발생 (타겟팅 보조)
            
        # 🚀 [v8.4 Sniper Mode] 핀치 직전(클릭 직전) 단계인 경우 커서를 거의 고정(viscosity = 0.03)하여 
        # 엄지와 검지가 닿는 과정에서 발생하는 우측 횡이동 피벗 드래프트를 원천 차단 (극강의 정밀도 보장)
        is_sniper_mode = False
        if index_ratio < (dynamic_on * 1.4) and not self.drag_mode:
            viscosity = 0.03
            is_sniper_mode = True
            
        # 가변 감도 및 예측 좌표 적용
        if self.prev_x != 0:
            diff_x = (pred_x - self.prev_x) * self.current_sensitivity * viscosity
            diff_y = (pred_y - self.prev_y) * self.current_sensitivity * viscosity
            raw_screen_x = self.prev_x + diff_x
            raw_screen_y = self.prev_y + diff_y

        # D. Adaptive Filtering (안정성에 따른 필터 강도 조절)
        # 랜드마크가 불안정할수록(integrity 낮음) 필터를 강하게 적용하여 점프 방지
        brake_factor = 0.0 if self.drag_mode else math.pow(max(0, min(1.0, 1.0 - (index_ratio - dynamic_on)/(dynamic_off - dynamic_on + 1e-6))), 2)
        integrity_damping = (1.0 - self.structural_integrity) * 2.0 # 최대 1.0 댐핑 추가
        
        self.filter_x.mincutoff = max(0.1, 1.5 - (brake_factor * 1.4) - integrity_damping)
        self.filter_y.mincutoff = max(0.1, 1.5 - (brake_factor * 1.4) - integrity_damping)
        
        tx_filtered, ty_filtered = int(self.filter_x(current_time, raw_screen_x)), int(self.filter_y(current_time, raw_screen_y))

        # [v5.0] Dynamic Deadzone (정지 시 흔들림 완전 제거)
        dist_moved = math.hypot(tx_filtered - self.prev_x, ty_filtered - self.prev_y)
        # 손가락을 모으고 있을수록(brake_factor 높음) 더 강한 데드존 적용
        if dist_moved < (1.5 + brake_factor * 8.0):
            tx_filtered, ty_filtered = self.prev_x, self.prev_y

        # 6. 상태 머신 호출
        # 스크롤 중에는 클릭이 발생하지 않도록 비율 강제 조정
        effective_ratio = 1.0 if self.is_scroll_mode else index_ratio
        self._handle_logic(effective_ratio, middle_ratio, dynamic_on, dynamic_off, tx_filtered, ty_filtered, is_idx_dom, is_mid_dom, is_fist, i_vec, i_score, m_score)

        # [v7.0] Neural Drift Update (실시간 학습)
        if not self.calib_manager.is_active:
            # 현재 상태(self.is_pinching)와 비율을 전달하여 배경에서 보정 수행
            self.calib_manager.drift_update(index_ratio, self.is_pinching)

        # 7. 최종 좌표 적용
        if is_resting:
            # 조작 의사가 없는 자세면 좌표 업데이트 건너뜀 (턱 괴기 방지 등)
            final_x, final_y = self.prev_x, self.prev_y
        elif current_time < self.freeze_until:
            final_x, final_y = self.prev_x, self.prev_y
        else:
            final_x, final_y = (self.locked_x, self.locked_y) if (self.is_pinching and not self.drag_mode) else (tx_filtered, ty_filtered)
        
        if not self.is_scroll_mode:
            self.mouse.position = (final_x, final_y)
            self.prev_x, self.prev_y = final_x, final_y
        else:
            # [v4.1] 스크롤 속도 대폭 상향 (분모 20 -> 5)
            diff_y = ty_filtered - self.scroll_start_y
            if abs(diff_y) > 3:  # 미세 떨림 방지 데드존
                scroll_amount = int(diff_y // 5)
                if scroll_amount != 0:
                    self.mouse.scroll(0, -scroll_amount)
                    self.scroll_start_y = ty_filtered
        # 8. v4.0 HUD 시각화
        if show_debug:
            self._draw_v4_hud(frame, index_ratio, m_score, dynamic_on, dynamic_off, is_idx_dom, is_mid_dom, is_both_pinched, i_vec, is_resting)

    def _handle_logic(self, ratio, m_ratio, on_th, off_th, tx, ty, is_idx_dom, is_mid_dom, is_both, i_vec, i_score, m_score):
        current_time = time.time()
        
        # A. 스크롤 모드 (양손가락 클릭 제스처)
        if is_both and not self.is_pinching:
            if not self.is_scroll_mode:
                self.is_scroll_mode = True
                self.scroll_start_y = ty
            return
        elif not is_both:
            self.is_scroll_mode = False

        # B. 좌클릭/드래그 (Z-Depth 및 정조준 보정 적용)
        # Z-Depth 조건: 엄지가 앞으로 돌진(z값 감소) 중일 때 더 쉽게 클릭 발동
        z_boost = 0.05 if self.thumb_z_velocity < -0.2 else 0.0
        effective_on = on_th + z_boost
        
        # 🚀 [v8.1] 좌클릭 조건 강화: 중지 손가락이 모이고 있지 않아야 함 (m_score > 0.65)
        # 이 조건이 없으면 양손가락 스크롤 제스처 진입 시 검지가 더 빠르게 움직이면 좌클릭이 오작동함
        if not self.is_pinching and ratio < effective_on and is_idx_dom and m_score > 0.65:
            self.is_pinching, self.pinch_start_time = True, current_time
            self.locked_x, self.locked_y = tx, ty
            self.pinch_release_counter = 0
        elif self.is_pinching and ratio > off_th:
            # 디바운스: 3프레임 연속으로 해제 조건을 만족할 때에만 실제로 클릭을 뗍니다.
            self.pinch_release_counter += 1
            if self.pinch_release_counter >= 3:
                if self.drag_mode: self.mouse.release(Button.left)
                else:
                    self.mouse.position = (self.locked_x, self.locked_y)
                    if (current_time - self.last_click_time) < self.double_click_threshold:
                        self.mouse.click(Button.left, 2)
                        self.last_click_time = 0
                    else:
                        self.mouse.click(Button.left, 1)
                        self.last_click_time = current_time
                self.is_pinching, self.drag_mode = False, False
                self.pinch_release_counter = 0
        else:
            # 핀치가 정상 유지 중이면 디바운스 카운터 리셋
            if self.is_pinching:
                self.pinch_release_counter = 0
                
            if self.is_pinching and not self.drag_mode and (current_time - self.pinch_start_time) >= self.drag_delay:
                self.drag_mode = True
                self.mouse.position = (self.locked_x, self.locked_y)
                self.mouse.press(Button.left)

        # C. 우클릭
        # 🚀 [v8.1] 우클릭 조건 강화: 검지 손가락이 모이고 있지 않아야 함 (i_score > 0.65)
        # 양손가락 스크롤 제스처 진입 시 중지가 더 빠르게 움직이면 우클릭이 오작동하는 경쟁 상태 차단
        if not self.is_pinching and m_ratio < (on_th * 1.2) and is_mid_dom and i_score > 0.65:
            if not self.is_right_pinching:
                self.is_right_pinching = True
                self.mouse.click(Button.right, 1)
        else:
            self.is_right_pinching = False

    def _draw_v4_hud(self, frame, ratio, m_score, on_th, off_th, is_idx_dom, is_mid_dom, is_both, i_vec, is_resting):
        h, w, _ = frame.shape
        # 상단 상태바
        status = "RESTING" if is_resting else "SCROLL" if self.is_scroll_mode else "DRAG" if self.drag_mode else "L-PINCH" if self.is_pinching else "R-PINCH" if self.is_right_pinching else "IDLE"
        color = (0, 0, 255) if is_resting else (255, 0, 255) if self.is_scroll_mode else (0, 255, 0) if (self.is_pinching or is_idx_dom) else (0, 255, 255) if (self.is_right_pinching or is_mid_dom) else (200, 200, 200)
        
        cv2.putText(frame, f"v6.0 {status}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        # [v6.0] Integrity 게이지
        int_color = (0, 255, 0) if self.structural_integrity > 0.8 else (0, 255, 255) if self.structural_integrity > 0.6 else (0, 0, 255)
        cv2.rectangle(frame, (w-220, 20), (w-220 + int(self.structural_integrity * 200), 35), int_color, -1)
        cv2.putText(frame, "TRACKING QUALITY", (w-215, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        # 정조준 게이지 (Vector Score)
        v_color = (0, 255, 0) if i_vec > 0.9 else (0, 200, 255) if i_vec > 0.8 else (0, 0, 255)
        cv2.rectangle(frame, (20, 60), (20 + int(i_vec * 200), 75), v_color, -1)
        cv2.putText(frame, f"AIM: {i_vec:.2f}", (230, 73), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # DPI 배율 표시
        dpi_label = "HIGH-DPI" if self.current_sensitivity > 1.0 else "PRECISION"
        cv2.putText(frame, dpi_label, (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # [v6.0] Prediction 보너스 표시
        if abs(self.vel_x) > 500:
            cv2.putText(frame, "PREDICTIVE ON", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        # 미니 맵 상의 포인트
        cv2.circle(frame, (self.prev_x * w // self.screen_w, self.prev_y * h // self.screen_h), 5, color, -1)

    def reset_state(self):
        if self.is_pinching and self.drag_mode: self.mouse.release(Button.left)
        self.is_pinching, self.drag_mode, self.is_right_pinching = False, False, False
        self.is_scroll_mode = False
        self.filter_x.reset(); self.filter_y.reset()

    def adjust_thresholds(self, key):
        step = 0.02
        changed = False
        if key == ord('c'): self.calib_manager.start()
        elif key == ord('w'): self.calib_manager.on_threshold += step; changed = True
        elif key == ord('s'): self.calib_manager.on_threshold -= step; changed = True
        elif key == ord('e'): self.calib_manager.off_threshold += step; changed = True
        elif key == ord('d'): self.calib_manager.off_threshold -= step; changed = True
        if changed: self.calib_manager.save_config()

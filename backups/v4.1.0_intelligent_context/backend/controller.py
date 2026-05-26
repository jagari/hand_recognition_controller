import math
import numpy as np
import pyautogui
import time
from pynput.mouse import Controller, Button
import cv2

from core.filter import OneEuroFilter
from core.calibration import CalibrationManager

# ==========================================================
# 🚀 메인 컨트롤러 v4.0 (Intelligent Context Hybrid Engine)
# ==========================================================
class MouseController:
    def __init__(self, drag_delay=0.25, double_click_threshold=0.3):
        self.mouse = Controller()
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

        # v4.0 신규 상태 변수
        self.is_scroll_mode = False
        self.scroll_start_y = 0
        self.prev_thumb_z = 0.0
        self.thumb_z_velocity = 0.0
        self.freeze_until = 0.0
        self.current_sensitivity = 1.0

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

    def process_landmarks(self, frame, hand_landmarks, show_debug):
        h, w, _ = frame.shape
        lm = hand_landmarks.landmark
        current_time = time.time()
        
        # 1. 기초 데이터 추출
        def to_px(l): return int(l.x * w), int(l.y * h)
        wx, wy = to_px(lm[0])
        tx, ty = to_px(lm[4])
        imx, imy = to_px(lm[5])
        ix, iy = to_px(lm[8])
        mx, my = to_px(lm[12])

        base_dist_2d = math.hypot(imx - wx, imy - wy) or 1
        index_ratio = math.hypot(ix-tx, iy-ty) / base_dist_2d
        middle_ratio = math.hypot(mx-tx, my-ty) / base_dist_2d

        # 2. [v4.0] Z-Depth 분석 (엄지 돌진 속도 계산)
        dt = 0.033
        self.thumb_z_velocity = (lm[4].z - self.prev_thumb_z) / dt
        self.prev_thumb_z = lm[4].z

        # 3. [v3.0 하이브리드 코어] 트리플 체크 엔진
        d3_base = self._calc_3d_dist(lm[5], lm[0]) or 0.001
        i_3d = min(self._calc_3d_dist(lm[8], lm[4]), self._calc_3d_dist(lm[6], lm[4])) / d3_base
        m_3d = self._calc_3d_dist(lm[12], lm[4]) / d3_base
        
        i_vec = self._calc_angle_score(lm[6], lm[8], lm[4])
        m_vec = self._calc_angle_score(lm[10], lm[12], lm[4])
        
        is_idx_extended = (self._calc_3d_dist(lm[8], lm[0]) / d3_base) > 1.7
        
        # 하이브리드 점수 산출
        i_score = i_3d + max(0, (0.8 - i_vec)) * 1.5
        m_score = m_3d + max(0, (0.8 - m_vec)) * 1.5
        
        if is_idx_extended:
            i_score += 3.0
            m_score -= 0.2
            
        # [v4.0] 가변 감도(DPI) 결정 - 검지를 펴면 고감도(빠른 이동), 접으면 저감도(정밀)
        self.current_sensitivity = 1.2 if is_idx_extended else 0.5

        # 하이브리드 승자 판정
        is_idx_dom = i_score < (m_score - 0.1)
        is_mid_dom = m_score < (i_score - 0.1)
        # [v4.1] 스크롤 모드 판정: 인식률 향상을 위해 임계값 완화 (0.4 -> 0.55)
        is_both_pinched = i_score < 0.55 and m_score < 0.55 and abs(i_score - m_score) < 0.2

        # 4. 캘리브레이션 및 인텐트 부스트
        if self.calib_manager.is_active:
            self.calib_manager.update(frame, index_ratio)
            return

        self.ratio_velocity = (index_ratio - self.prev_ratio) / dt
        self.prev_ratio = index_ratio

        intent_boost = abs(self.ratio_velocity) * 0.05 if self.ratio_velocity < -0.5 else 0.0
        dynamic_on = self.calib_manager.on_threshold + intent_boost
        dynamic_off = self.calib_manager.off_threshold

        # 5. [v4.0] 좌표 계산 및 정밀도 필터링
        # 정조준 시 커서 프리즈 (클릭 미끄럼 방지)
        if i_vec > 0.96 and not self.is_pinching:
            self.freeze_until = current_time + 0.15 

        raw_screen_x = np.interp(imx, (self.frame_margin, w-self.frame_margin), (0, self.screen_w))
        raw_screen_y = np.interp(imy, (self.frame_margin, h-self.frame_margin), (0, self.screen_h))
        
        # 가변 감도 적용 (상대 이동량 조절)
        if self.prev_x != 0:
            diff_x = (raw_screen_x - self.prev_x) * self.current_sensitivity
            diff_y = (raw_screen_y - self.prev_y) * self.current_sensitivity
            raw_screen_x = self.prev_x + diff_x
            raw_screen_y = self.prev_y + diff_y

        brake_factor = 0.0 if self.drag_mode else math.pow(max(0, min(1.0, 1.0 - (index_ratio - dynamic_on)/(dynamic_off - dynamic_on + 1e-6))), 2)
        self.filter_x.mincutoff = 1.5 - (brake_factor * 1.49)
        self.filter_y.mincutoff = 1.5 - (brake_factor * 1.49)
        
        tx_filtered, ty_filtered = int(self.filter_x(current_time, raw_screen_x)), int(self.filter_y(current_time, raw_screen_y))

        # 6. 상태 머신 호출
        self._handle_logic(index_ratio, middle_ratio, dynamic_on, dynamic_off, tx_filtered, ty_filtered, is_idx_dom, is_mid_dom, is_both_pinched, i_vec)

        # 7. 최종 좌표 적용
        if current_time < self.freeze_until:
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
            self._draw_v4_hud(frame, index_ratio, m_score, dynamic_on, dynamic_off, is_idx_dom, is_mid_dom, is_both_pinched, i_vec)

    def _handle_logic(self, ratio, m_ratio, on_th, off_th, tx, ty, is_idx_dom, is_mid_dom, is_both, i_vec):
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
        
        if not self.is_pinching and ratio < effective_on and is_idx_dom:
            # 클릭 확정 전 최종 정조준 체크
            if i_vec > 0.85: 
                self.is_pinching, self.pinch_start_time = True, current_time
                self.locked_x, self.locked_y = tx, ty
        elif self.is_pinching and ratio > off_th:
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
        elif self.is_pinching and not self.drag_mode and (current_time - self.pinch_start_time) >= self.drag_delay:
            self.drag_mode = True
            self.mouse.position = (self.locked_x, self.locked_y)
            self.mouse.press(Button.left)

        # C. 우클릭
        if not self.is_pinching and m_ratio < (on_th * 1.2) and is_mid_dom:
            if not self.is_right_pinching:
                self.is_right_pinching = True
                self.mouse.click(Button.right, 1)
        else:
            self.is_right_pinching = False

    def _draw_v4_hud(self, frame, ratio, m_score, on_th, off_th, is_idx_dom, is_mid_dom, is_both, i_vec):
        h, w, _ = frame.shape
        # 상단 상태바
        status = "SCROLL" if self.is_scroll_mode else "DRAG" if self.drag_mode else "L-PINCH" if self.is_pinching else "R-PINCH" if self.is_right_pinching else "IDLE"
        color = (255, 0, 255) if self.is_scroll_mode else (0, 255, 0) if (self.is_pinching or is_idx_dom) else (0, 255, 255) if (self.is_right_pinching or is_mid_dom) else (200, 200, 200)
        
        cv2.putText(frame, f"v4.0 {status}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        # 정조준 게이지 (Vector Score)
        v_color = (0, 255, 0) if i_vec > 0.9 else (0, 200, 255) if i_vec > 0.8 else (0, 0, 255)
        cv2.rectangle(frame, (20, 60), (20 + int(i_vec * 200), 75), v_color, -1)
        cv2.putText(frame, f"AIM: {i_vec:.2f}", (230, 73), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # DPI 배율 표시
        dpi_label = "HIGH-DPI" if self.current_sensitivity > 1.0 else "PRECISION"
        cv2.putText(frame, dpi_label, (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

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

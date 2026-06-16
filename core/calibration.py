import time
import cv2
import numpy as np
import logging
import json
import os

logger = logging.getLogger(__name__)

class CalibrationManager:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.is_active = False
        self.step = 0
        self.start_time = 0
        self.prep_time = 2.0
        self.scan_time = 4.0
        self.open_data = []
        self.pinch_data = []

        # 🚀 황금 경계선 초기값
        self.on_threshold = 0.25
        self.off_threshold = 0.38
        
        # 분석 결과 리포트
        self.open_stats = {"mean": 0.4, "std": 0.05}
        self.pinch_stats = {"mean": 0.1, "std": 0.03}

        # 저장된 설정 불러오기
        self.load_config()

    def start(self):
        logger.info("🔧 [v3.0 캘리브레이션] 지능형 군집 분석 시작")
        self.is_active = True
        self.step = 1
        self.start_time = time.time() + self.prep_time
        self.open_data = []
        self.pinch_data = []

    def update(self, frame, index_ratio):
        h, w, _ = frame.shape
        current_time = time.time()

        # UI 스타일링 (Modern HUD)
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 120), (30, 30, 30), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # 1. 준비 단계
        if current_time < self.start_time:
            msg = "PREPARING STEP 1: OPEN HAND" if self.step == 1 else "PREPARING STEP 2: PINCH TIGHT"
            cv2.putText(frame, msg, (w//2-250, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            cv2.putText(frame, f"Starts in {int(self.start_time - current_time) + 1}s...", (w//2-80, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
            return

        # 2. 데이터 수집 단계
        elapsed = current_time - self.start_time
        if self.step == 1:
            self.open_data.append(index_ratio)
            msg = "ACTION: ROTATE OPEN HAND"
            color = (0, 255, 0)
        else:
            self.pinch_data.append(index_ratio)
            msg = "ACTION: HOLD TIGHT PINCH"
            color = (0, 255, 255)

        progress = min(1.0, elapsed / self.scan_time)
        cv2.rectangle(frame, (w//2-250, 80), (w//2+250, 100), (50, 50, 50), -1)
        cv2.rectangle(frame, (w//2-250, 80), (w//2-250 + int(500*progress), 100), color, -1)
        cv2.putText(frame, msg, (w//2-180, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        # 3. 분석 및 군집화
        if elapsed > self.scan_time:
            if self.step == 1:
                self.step = 2
                self.start_time = time.time() + self.prep_time
                logger.info("👉 STEP 1 완료, STEP 2 준비")
            else:
                self._analyze_clusters()
                self.is_active = False

    def _analyze_clusters(self):
        # 가우시안 군집 분석 스타일의 통계 처리
        open_arr = np.array(self.open_data)
        pinch_arr = np.array(self.pinch_data)

        # 이상치 제거 (IQR 방식)
        def get_clean_stats(data):
            if len(data) == 0: return 0.5, 0.1
            q1, q3 = np.percentile(data, [25, 75])
            iqr = q3 - q1
            filtered = data[(data >= q1 - 1.5*iqr) & (data <= q3 + 1.5*iqr)]
            if len(filtered) == 0: filtered = data
            return np.mean(filtered), np.std(filtered)

        o_mean, o_std = get_clean_stats(open_arr)
        p_mean, p_std = get_clean_stats(pinch_arr)

        self.open_stats = {"mean": float(o_mean), "std": float(o_std)}
        self.pinch_stats = {"mean": float(p_mean), "std": float(p_std)}

        # 황금 경계선 도출 (gap ratio 기반)
        gap = o_mean - p_mean
        self.on_threshold = p_mean + (gap * 0.25)
        self.off_threshold = p_mean + (gap * 0.45)

        # 안전 장치: 간격이 너무 좁으면 보정
        if self.off_threshold - self.on_threshold < 0.08:
            self.on_threshold = p_mean + (gap * 0.25)
            self.off_threshold = o_mean - (gap * 0.25)

        logger.info(f"✅ 분석 완료 - OPEN(μ={o_mean:.3f}, σ={o_std:.3f}) / PINCH(μ={p_mean:.3f}, σ={p_std:.3f})")
        logger.info(f"🚀 적용된 임계값 - ON: {self.on_threshold:.3f} / OFF: {self.off_threshold:.3f}")
        self.save_config()

    def drift_update(self, ratio, is_pinched):
        """실시간 사용 데이터를 기반으로 군집 중심을 미세하게 조정 (Evolutionary Intelligence)"""
        learning_rate = 0.0005 # 매우 보수적인 학습률
        
        # 1. 중심점 이동
        if is_pinched:
            # 클릭 중일 때: 현재 비율이 평균보다 더 작으면(더 꽉 쥐면) 평균을 아래로 이동
            if ratio < self.pinch_stats["mean"]:
                self.pinch_stats["mean"] = (self.pinch_stats["mean"] * (1 - learning_rate)) + (ratio * learning_rate)
        else:
            # 손을 펴고 있을 때: 현재 비율이 평균보다 더 크면(더 크게 펴면) 평균을 위로 이동
            if ratio > self.open_stats["mean"]:
                self.open_stats["mean"] = (self.open_stats["mean"] * (1 - learning_rate)) + (ratio * learning_rate)

        # 2. 임계값 재계산 (부드러운 적응 - gap ratio 기반)
        current_gap = self.open_stats["mean"] - self.pinch_stats["mean"]
        new_on = self.pinch_stats["mean"] + (current_gap * 0.25)
        new_off = self.pinch_stats["mean"] + (current_gap * 0.45)
        
        # 급격한 변화 방지 (Smoothing)
        self.on_threshold = (self.on_threshold * 0.99) + (new_on * 0.01)
        self.off_threshold = (self.off_threshold * 0.99) + (new_off * 0.01)

        # 안전 장치 유지
        if self.off_threshold - self.on_threshold < 0.08:
            self.on_threshold = self.pinch_stats["mean"] + (current_gap * 0.25)
            self.off_threshold = self.open_stats["mean"] - (current_gap * 0.25)

    def save_config(self):
        config = {
            "on_threshold": float(self.on_threshold),
            "off_threshold": float(self.off_threshold),
            "open_stats": self.open_stats,
            "pinch_stats": self.pinch_stats,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "is_metric": True  # 🚀 3D Metric Core flag
        }
        try:
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=4)
            logger.info(f"💾 설정 저장 완료: {self.config_path}")
        except Exception as e:
            logger.error(f"❌ 설정 저장 실패: {e}")

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                
                # 구버전 비메트릭 설정 파일 무효화 및 리셋
                if not config.get("is_metric", False):
                    logger.info("⚠️ 구버전 비메트릭 설정 파일 감지: 3D Metric 기반 설정으로 초기화합니다.")
                    self.on_threshold = 0.18
                    self.off_threshold = 0.28
                    self.open_stats = {"mean": 0.4, "std": 0.05}
                    self.pinch_stats = {"mean": 0.1, "std": 0.03}
                    self.save_config()
                    return
                
                self.on_threshold = config.get("on_threshold", self.on_threshold)
                self.off_threshold = config.get("off_threshold", self.off_threshold)
                self.open_stats = config.get("open_stats", self.open_stats)
                self.pinch_stats = config.get("pinch_stats", self.pinch_stats)
                logger.info(f"📂 설정 로드 완료 (v3.0) - ON: {self.on_threshold:.3f}, OFF: {self.off_threshold:.3f}")
            except Exception as e:
                logger.error(f"❌ 설정 로드 오류: {e}")
        else:
            logger.info("ℹ️ 기존 설정 파일 없음, 기본값 사용")

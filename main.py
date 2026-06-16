import cv2
import logging
import math
from backend.camera import CameraManager
from backend.tracker import HandTracker
from backend.controller import MouseController

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 시스템 가동 (v7.0 Evolutionary Intelligence Engine)")
    SHOW_DEBUG_WINDOW = True

    try:
        cam = CameraManager()
        tracker = HandTracker()
        controller = MouseController()
    except Exception as e:
        logger.error(f"초기화 실패: {e}")
        return

    cam.start()

    try:
        while True:
            try:
                frame = cam.get_frame()
                if frame is not None:
                    frame = cv2.flip(frame, 1)
                    results = tracker.process(frame)

                    if results.multi_hand_landmarks and results.multi_handedness:
                        # 🚀 [v8.0] 주도적 손 바인딩 (Hand Dominance Binding) 개선
                        target_hand = None
                        target_world_hand = None
                        
                        # 화면 미러링(cv2.flip) 상태에서는 물리적 오른손이 "Left"로 검출됨.
                        # 따라서 물리적 오른손을 추적하기 위해 "Left"를 우선 검색하되,
                        # 검출된 손이 1개뿐이라면 라벨과 무관하게 추적 대상으로 지정하여 인식률 제고.
                        if len(results.multi_hand_landmarks) == 1:
                            target_hand = results.multi_hand_landmarks[0]
                            if results.multi_hand_world_landmarks:
                                target_world_hand = results.multi_hand_world_landmarks[0]
                        else:
                            # 여러 손이 감지된 경우 미러링된 오른손("Left") 우선 락온
                            target_label = "Left" 
                            for idx, (hand_landmarks, handedness) in enumerate(zip(results.multi_hand_landmarks, results.multi_handedness)):
                                label = handedness.classification[0].label
                                if label == target_label:
                                    target_hand = hand_landmarks
                                    if results.multi_hand_world_landmarks and idx < len(results.multi_hand_world_landmarks):
                                        target_world_hand = results.multi_hand_world_landmarks[idx]
                                    break
                            
                            # 만약 선호하는 라벨이 없는 경우 첫 번째 손 매핑
                            if target_hand is None:
                                target_hand = results.multi_hand_landmarks[0]
                                if results.multi_hand_world_landmarks:
                                    target_world_hand = results.multi_hand_world_landmarks[0]
                        
                        if target_hand is not None:
                            # 🚀 [v8.1] 원거리 오인식 방지 필터 (Distance/Size Filter)
                            # 얼굴이나 배경 노이즈가 오인식된 경우 손목(0)과 검지 시작점(5) 간의 3D 거리가 매우 작음
                            lm = target_hand.landmark
                            d3_base = math.sqrt((lm[5].x - lm[0].x)**2 + (lm[5].y - lm[0].y)**2 + (lm[5].z - lm[0].z)**2)
                            if d3_base > 0.065:
                                if SHOW_DEBUG_WINDOW:
                                    tracker.draw(frame, target_hand)
                                # v8.2 하이브리드 엔진 프로세싱 (world_landmarks 주입)
                                controller.process_landmarks(frame, target_hand, target_world_hand, SHOW_DEBUG_WINDOW)
                            else:
                                controller.reset_state()
                        else:
                            controller.reset_state()
                    else:
                        controller.reset_state()

                    if SHOW_DEBUG_WINDOW:
                        cv2.imshow('AI Mouse Architecture', frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    logger.info("종료 요청 수신 (q)")
                    break
                else:
                    controller.adjust_thresholds(key)
            except cv2.error as e:
                logger.error(f"OpenCV 오류: {e}")
                break
            except Exception as e:
                logger.error(f"루프 내 예외 발생: {e}")
                
    except KeyboardInterrupt:
        logger.info("사용자에 의한 강제 종료 (Ctrl+C)")
    finally:
        logger.info("시스템 종료 절차 시작")
        controller.reset_state()
        cam.stop()
        cv2.destroyAllWindows()
        logger.info("시스템 완전히 종료됨")

if __name__ == '__main__':
    main()

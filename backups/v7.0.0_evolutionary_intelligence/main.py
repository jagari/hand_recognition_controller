import cv2
import logging
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

                    if results.multi_hand_landmarks:
                        for hand_landmarks in results.multi_hand_landmarks:
                            if SHOW_DEBUG_WINDOW:
                                tracker.draw(frame, hand_landmarks)
                            
                            # v3.0 하이브리드 엔진 (2D/3D 결합) 프로세싱
                            controller.process_landmarks(frame, hand_landmarks, SHOW_DEBUG_WINDOW)
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

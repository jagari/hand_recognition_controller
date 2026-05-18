import cv2
from camera import CameraManager
from tracker import HandTracker
from controller import MouseController

def main():
    print("시스템 가동 (모듈화 아키텍처 및 캘리브레이션 적용)")
    SHOW_DEBUG_WINDOW = True

    # 모듈 초기화
    cam = CameraManager()
    tracker = HandTracker()
    controller = MouseController()

    cam.start()

    try:
        while True:
            frame = cam.get_frame()
            if frame is not None:
                frame = cv2.flip(frame, 1)
                results = tracker.process(frame)

                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        if SHOW_DEBUG_WINDOW:
                            tracker.draw(frame, hand_landmarks)
                        
                        # 제어 로직 호출
                        controller.process_landmarks(frame, hand_landmarks, SHOW_DEBUG_WINDOW)
                else:
                    controller.reset_state()

                if SHOW_DEBUG_WINDOW:
                    cv2.imshow('AI Mouse Architecture', frame)
            
            # 키보드 입력 처리 및 캘리브레이션 제어
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            else:
                # 'q' 이외의 키 입력 발생 시 캘리브레이션 메서드로 전달
                controller.adjust_thresholds(key)
                
    finally:
        # 시스템 종료 시 리소스 안전 해제
        controller.reset_state()
        cam.stop()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
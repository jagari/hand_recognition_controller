import cv2
import mediapipe as mp
import multiprocessing as mp_lib
import math
import numpy as np
import pyautogui
from pynput.mouse import Controller, Button
import time

# --- [1. 이미지 캡처 전담 프로세스 (독립 실행)] ---
def image_capture_process(image_queue):
    cap = cv2.VideoCapture(0)
    # 해상도 및 FPS 설정
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 60)

    while True:
        success, frame = cap.read()
        if success:
            # 큐가 꽉 찼다면 가장 오래된 프레임을 버리고 최신 프레임을 넣음 (입력 지연 방지)
            if image_queue.full():
                try:
                    image_queue.get_nowait()
                except:
                    pass
            image_queue.put(frame)
        else:
            time.sleep(0.01)

# --- [2. 메인 AI 추론 및 마우스 제어 프로세스] ---
def main():
    # 프로세스 간 통신을 위한 큐 (항상 최신 프레임 1개만 유지)
    image_queue = mp_lib.Queue(maxsize=1)
    
    # 카메라 캡처 프로세스 시작
    capture_proc = mp_lib.Process(target=image_capture_process, args=(image_queue,), daemon=True)
    capture_proc.start()

    mouse = Controller()
    screen_w, screen_h = pyautogui.size()

    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    
    # model_complexity=0 으로 설정하여 연산 속도 극대화
    hands = mp_hands.Hands(
        max_num_hands=1,
        model_complexity=0, 
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    )

    FRAME_MARGIN = 100
    SMOOTHING_FACTOR = 2  # 멀티프로세싱으로 반응이 빨라졌으므로 2로 낮춰 반응성 향상

    # --- [상태 제어 변수] ---
    prev_x, prev_y = 0, 0
    curr_x, curr_y = 0, 0
    
    is_pinching = False
    drag_mode = False
    pinch_start_time = 0
    locked_x, locked_y = 0, 0
    
    DRAG_DELAY = 0.25

    is_right_pinching = False
    locked_right_x, locked_right_y = 0, 0

    last_click_time = 0
    double_click_threshold = 0.3

    SHOW_DEBUG_WINDOW = True 

    print(f"✅ 시스템 가동 (멀티프로세싱 모드). 0.25초 이상 길게 꼬집으면 드래그가 시작됩니다.")

    while True:
        # 큐에 캡처된 이미지가 있을 때만 처리
        if not image_queue.empty():
            frame = image_queue.get()

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)
            h, w, c = frame.shape

            if SHOW_DEBUG_WINDOW:
                cv2.rectangle(frame, (FRAME_MARGIN, FRAME_MARGIN), 
                             (w - FRAME_MARGIN, h - FRAME_MARGIN), (255, 0, 255), 2)

            # 1. 화면에 손이 인식되었을 때
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    if SHOW_DEBUG_WINDOW:
                        mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                    # 랜드마크 추출
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

                    center_x = (thumb_x + index_x) // 2
                    center_y = (thumb_y + index_y) // 2

                    hand_size = math.hypot(mcp_x - wrist_x, mcp_y - wrist_y)
                    dynamic_click_threshold = hand_size * 0.25
                    index_pinch_dist = math.hypot(index_x - thumb_x, index_y - thumb_y)
                    middle_pinch_dist = math.hypot(middle_x - thumb_x, middle_y - thumb_y)

                    # 마우스 이동 목표 좌표 계산
                    screen_x = np.interp(center_x, (FRAME_MARGIN, w - FRAME_MARGIN), (0, screen_w))
                    screen_y = np.interp(center_y, (FRAME_MARGIN, h - FRAME_MARGIN), (0, screen_h))
                    target_x = prev_x + (screen_x - prev_x) / SMOOTHING_FACTOR
                    target_y = prev_y + (screen_y - prev_y) / SMOOTHING_FACTOR

                    # --- 2. 시간 기반 좌클릭 & 드래그 상태 머신 ---
                    if index_pinch_dist < dynamic_click_threshold:
                        if SHOW_DEBUG_WINDOW: cv2.circle(frame, (center_x, center_y), 15, (0, 255, 0), cv2.FILLED)
                        
                        if not is_pinching:
                            is_pinching = True
                            pinch_start_time = time.time()
                            locked_x, locked_y = prev_x, prev_y 
                        else:
                            if not drag_mode and (time.time() - pinch_start_time) >= DRAG_DELAY:
                                drag_mode = True
                                mouse.position = (locked_x, locked_y)
                                mouse.press(Button.left)
                                print("드래그 모드 활성화")

                        if not drag_mode:
                            curr_x, curr_y = locked_x, locked_y
                        else:
                            curr_x, curr_y = target_x, target_y 
                    else:
                        if SHOW_DEBUG_WINDOW: cv2.circle(frame, (center_x, center_y), 10, (0, 0, 255), cv2.FILLED)
                        
                        if is_pinching:
                            if drag_mode:
                                mouse.release(Button.left)
                                print("드래그 해제")
                            else:
                                mouse.position = (locked_x, locked_y)
                                
                                # 더블 클릭 검사
                                current_time = time.time()
                                if current_time - last_click_time < double_click_threshold:
                                    mouse.click(Button.left, 2)
                                    print("더블 클릭")
                                    last_click_time = 0 
                                else:
                                    mouse.click(Button.left, 1)
                                    print("단발성 좌클릭")
                                    last_click_time = current_time 
                            
                            is_pinching = False
                            drag_mode = False

                        curr_x, curr_y = target_x, target_y

                    # --- 3. 우클릭 제어 ---
                    if middle_pinch_dist < dynamic_click_threshold and not is_pinching:
                        if SHOW_DEBUG_WINDOW: 
                            cv2.line(frame, (thumb_x, thumb_y), (middle_x, middle_y), (255, 0, 0), 3)
                            cv2.circle(frame, (middle_x, middle_y), 15, (255, 0, 0), cv2.FILLED)
                        
                        if not is_right_pinching:
                            is_right_pinching = True
                            locked_right_x, locked_right_y = prev_x, prev_y
                            mouse.position = (locked_right_x, locked_right_y)
                            mouse.click(Button.right, 1)
                            print("단발성 우클릭")
                        
                        curr_x, curr_y = locked_right_x, locked_right_y
                    else:
                        is_right_pinching = False

                    # --- 최종 좌표 적용 ---
                    mouse.position = (curr_x, curr_y)
                    prev_x, prev_y = curr_x, curr_y

            # 손이 화면 밖으로 나갔을 때의 안전 장치
            else:
                if is_pinching and drag_mode:
                    mouse.release(Button.left)
                    print("화면 이탈: 드래그 강제 해제")
                is_pinching = False
                drag_mode = False
                is_right_pinching = False

            if SHOW_DEBUG_WINDOW:
                cv2.imshow('AI Mouse Controller (Multi-Processing)', frame)
                
        # 큐에 데이터가 없더라도 종료 키 입력은 계속 대기
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 시스템 종료 시 
    if is_pinching and drag_mode:
        mouse.release(Button.left)
        
    capture_proc.terminate() # 캡처 프로세스 안전하게 강제 종료
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
    
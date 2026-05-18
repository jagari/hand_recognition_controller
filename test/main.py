import cv2 # opencv (웹캠 제어, 화면에 그림)
import mediapipe as mp # AI 모델, 손을 찾아 점 찍음
import math
import numpy as np
import pyautogui # 모니터 해상됴 알기 위해 한 번만 사용
from pynput.mouse import Controller, Button # 실제로 마우스를 움직이고 클릭하는 역할 (최적화)
import time  # 시간 측정을 위한 모듈 추가

def main():
    mouse = Controller()
    screen_w, screen_h = pyautogui.size() 

    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    
    hands = mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    )

    cap = cv2.VideoCapture(0)

    # 해상도를 낮춰 연산량 감소
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # 60프로엠으로 강제로 할당해 반응속도 극대화
    cap.set(cv2.CAP_PROP_FPS, 60) 

    FRAME_MARGIN = 100
    SMOOTHING_FACTOR = 3 

    # --- [상태 제어 변수] ---
    prev_x, prev_y = 0, 0
    curr_x, curr_y = 0, 0
    
    is_pinching = False           # 물리적으로 손가락이 모여있는지 여부
    drag_mode = False             # 드래그 모드 활성화 여부
    pinch_start_time = 0          # 손가락을 모은 시점의 시간
    locked_x, locked_y = 0, 0     # 클릭 시 고정할 좌표
    
    DRAG_DELAY = 0.25             # [튜닝 포인트] 0.25초 이상 모으고 있으면 드래그로 판정

    is_right_pinching = False
    locked_right_x, locked_right_y = 0, 0

    SHOW_DEBUG_WINDOW = True 

    print(f"시스템 가동 (안정화 모드). 0.25초 이상 길게 꼬집으면 드래그가 시작됩니다.")

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

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
                index_tip = hand_landmarks.landmark[8] # 8번 랜드마크 설정   
                middle_tip = hand_landmarks.landmark[12]    

                wrist_x, wrist_y = int(wrist.x * w), int(wrist.y * h)
                mcp_x, mcp_y = int(index_mcp.x * w), int(index_mcp.y * h)
                thumb_x, thumb_y = int(thumb_tip.x * w), int(thumb_tip.y * h) 
                index_x, index_y = int(index_tip.x * w), int(index_tip.y * h) # 8번 랜드마크(검지 끝)의 비율 값을 실제 픽셀 좌표(x, y)로 변환
                middle_x, middle_y = int(middle_tip.x * w), int(middle_tip.y * h)

                center_x = (thumb_x + index_x) // 2
                center_y = (thumb_y + index_y) // 2

                hand_size = math.hypot(mcp_x - wrist_x, mcp_y - wrist_y)
                dynamic_click_threshold = hand_size * 0.25
                index_pinch_dist = math.hypot(index_x - thumb_x, index_y - thumb_y)
                middle_pinch_dist = math.hypot(middle_x - thumb_x, middle_y - thumb_y)

                # 마우스 이동 목표 좌표 계산 (스무딩 적용 전)
                screen_x = np.interp(center_x, (FRAME_MARGIN, w - FRAME_MARGIN), (0, screen_w))
                screen_y = np.interp(center_y, (FRAME_MARGIN, h - FRAME_MARGIN), (0, screen_h))
                target_x = prev_x + (screen_x - prev_x) / SMOOTHING_FACTOR
                target_y = prev_y + (screen_y - prev_y) / SMOOTHING_FACTOR

                # --- 2. 시간 기반 좌클릭 & 드래그 상태 머신 ---
                if index_pinch_dist < dynamic_click_threshold:
                    if SHOW_DEBUG_WINDOW: cv2.circle(frame, (center_x, center_y), 15, (0, 255, 0), cv2.FILLED)
                    
                    if not is_pinching:
                        # [초기 진입] 핀치 시작: 시간 기록 및 현재 좌표 강제 고정 (떨림 방지)
                        is_pinching = True
                        pinch_start_time = time.time()
                        locked_x, locked_y = prev_x, prev_y 
                    else:
                        # [유지 중] 설정된 시간(DRAG_DELAY)이 지나면 드래그 모드로 전환
                        if not drag_mode and (time.time() - pinch_start_time) >= DRAG_DELAY:
                            drag_mode = True
                            mouse.position = (locked_x, locked_y)
                            mouse.press(Button.left)
                            print("드래그 모드 활성화")

                    # 좌표 적용: 드래그 모드가 아니면(일반 클릭 대기중) 좌표를 묶어둠
                    if not drag_mode:
                        curr_x, curr_y = locked_x, locked_y
                    else:
                        curr_x, curr_y = target_x, target_y # 드래그 중에는 마우스 이동 허용
                else:
                    if SHOW_DEBUG_WINDOW: cv2.circle(frame, (center_x, center_y), 10, (0, 0, 255), cv2.FILLED)
                    
                    if is_pinching:
                        # [핀치 해제] 손가락을 뗐을 때의 판단
                        if drag_mode:
                            mouse.release(Button.left)
                            print("드래그 해제")
                        else:
                            # 0.25초 전에 손을 뗐다면 깔끔한 '단발성 클릭' 실행
                            mouse.position = (locked_x, locked_y)
                            mouse.click(Button.left, 1)
                            print("단발성 좌클릭")
                        
                        is_pinching = False
                        drag_mode = False

                    # 평상시 마우스 이동
                    curr_x, curr_y = target_x, target_y

                # --- 3. 우클릭 제어 (좌클릭과 간섭 방지) ---
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
                    
                    # 우클릭하는 동안에도 커서 흔들림 방지
                    curr_x, curr_y = locked_right_x, locked_right_y
                else:
                    is_right_pinching = False

                # --- 최종 좌표 적용 ---
                mouse.position = (curr_x, curr_y)
                prev_x, prev_y = curr_x, curr_y

        # 손이 화면 밖으로 나갔을 때의 안전 장치 (눌림 풀림)
        else:
            if is_pinching and drag_mode:
                mouse.release(Button.left)
                print("화면 이탈: 드래그 강제 해제")
            is_pinching = False
            drag_mode = False
            is_right_pinching = False

        if SHOW_DEBUG_WINDOW:
            cv2.imshow('AI Mouse Controller (Stable)', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    # 시스템 종료 시 
    if is_pinching and drag_mode:
        mouse.release(Button.left)
        
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
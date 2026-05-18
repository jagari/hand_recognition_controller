import cv2
import time
import multiprocessing as mp_lib
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def _image_capture_process(image_queue, stop_event):
    logger.info("카메라 캡처 프로세스 시작")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        logger.error("카메라를 열 수 없습니다.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 60)

    try:
        while not stop_event.is_set():
            success, frame = cap.read()
            if success:
                if image_queue.full():
                    try:
                        image_queue.get_nowait()
                    except mp_lib.queues.Empty:
                        pass
                image_queue.put(frame)
            else:
                logger.warning("프레임 읽기 실패. 재시도 중...")
                time.sleep(0.1)
    except Exception as e:
        logger.error(f"캡처 프로세스 오류: {e}")
    finally:
        cap.release()
        logger.info("카메라 리소스 해제 및 프로세스 종료")

class CameraManager:
    def __init__(self):
        self.queue = mp_lib.Queue(maxsize=1)
        self.stop_event = mp_lib.Event()
        self.process = None

    def start(self):
        if self.process is None or not self.process.is_alive():
            self.stop_event.clear()
            self.process = mp_lib.Process(
                target=_image_capture_process, 
                args=(self.queue, self.stop_event), 
                daemon=True
            )
            self.process.start()
            logger.info("CameraManager 가동")

    def get_frame(self):
        try:
            if not self.queue.empty():
                return self.queue.get_nowait()
        except mp_lib.queues.Empty:
            pass
        return None

    def stop(self):
        if self.process and self.process.is_alive():
            self.stop_event.set()
            self.process.join(timeout=2.0)
            if self.process.is_alive():
                logger.warning("프로세스가 정상 종료되지 않아 강제 종료합니다.")
                self.process.terminate()
            logger.info("CameraManager 정지")

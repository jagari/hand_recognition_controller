import cv2
import time
import multiprocessing as mp_lib

def _image_capture_process(image_queue):
    """독립 프로세스에서 동작하는 카메라 캡처 루프"""

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 60)

    while True:
        success, frame = cap.read()
        if success:
            if image_queue.full():
                try:
                    image_queue.get_nowait()
                except:
                    pass
            image_queue.put(frame)
        else:
            time.sleep(0.01)

class CameraManager:
    def __init__(self):
        self.queue = mp_lib.Queue(maxsize = 1)
        self.process = mp_lib.Process(target = _image_capture_process, args = (self.queue,), daemon = True)

    def start(self):
        self.process.start()
    
    def get_frame(self):
        if not self.queue.empty():
            return self.queue.get()
        return None
    
    def stop(self):
        self.process.terminate()
from PySide6.QtCore import QThread, Signal
import cv2
import time
import numpy as np

class VideoDecoder(QThread):
    frame_ready = Signal(np.ndarray)

    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.running = True

    def run(self):
        cap = cv2.VideoCapture(self.path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        delay = 1.0 / fps if fps > 1e-2 else 1 / 30  # fallback
        while self.running:
            if not cap.isOpened():
                break
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # rewind to first frame
                continue
            self.frame_ready.emit(frame)
            time.sleep(delay)
        cap.release()

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

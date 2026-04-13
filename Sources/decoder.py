from PySide6.QtCore import QThread, Signal
import cv2
import time
import numpy as np
from threading import Lock

class VideoDecoder(QThread):
    frame_ready = Signal(np.ndarray)
    frame_info_updated = Signal(int, int)

    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.running = True
        self.paused = False
        self.seek_frame = None
        self.lock = Lock()

    def run(self):
        cap = cv2.VideoCapture(self.path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        delay = 1.0 / fps if fps > 1e-2 else 1 / 30  # fallback
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        while self.running:
            if not cap.isOpened():
                break

            with self.lock:
                paused = self.paused
                seek_frame = self.seek_frame
                self.seek_frame = None

            if seek_frame is not None:
                cap.set(cv2.CAP_PROP_POS_FRAMES, seek_frame)
                ret, frame = cap.read()
                if ret:
                    current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                    self.frame_ready.emit(frame)
                    self.frame_info_updated.emit(current_frame, total_frames)
                time.sleep(delay)
                continue

            if paused:
                time.sleep(0.05)
                continue

            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # rewind to first frame
                continue
            current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            self.frame_ready.emit(frame)
            self.frame_info_updated.emit(current_frame, total_frames)
            time.sleep(delay)
        cap.release()

    def play(self):
        with self.lock:
            self.paused = False

    def pause(self):
        with self.lock:
            self.paused = True

    def seek(self, frame):
        with self.lock:
            self.seek_frame = max(0, int(frame))

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

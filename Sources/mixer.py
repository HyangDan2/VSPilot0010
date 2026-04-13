from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
import cv2
import numpy as np
from queue import Empty
import time

class MixingThread(QThread):
    mixed_frame_ready = Signal(QImage)
    metadata_updated = Signal(tuple)

    def __init__(self, queue1, queue2):
        super().__init__()
        self.q1 = queue1
        self.q2 = queue2
        self.running = True
        self.mode = "columns"
        self.checker_size = 16

    def run(self):
        last1 = None
        last2 = None
        while self.running:
            updated = False
            try:
                last1 = self.q1.get(timeout=0.03 if last1 is None else 0.001)
                updated = True
            except Empty:
                pass
            try:
                last2 = self.q2.get(timeout=0.03 if last2 is None else 0.001)
                updated = True
            except Empty:
                pass

            if last1 is None or last2 is None:
                continue
            if not updated:
                time.sleep(0.005)
                continue

            f1 = last1
            f2 = last2

            # 해상도 맞추기
            if f1.shape != f2.shape:
                f2 = cv2.resize(f2, (f1.shape[1], f1.shape[0]))

            mixed = self.mix_frames(f1, f2)
            h, w, ch = mixed.shape
            rgb = cv2.cvtColor(mixed, cv2.COLOR_BGR2RGB)
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
            w1 = f1.shape[1]
            w2 = f2.shape[1]
            h1 = f1.shape[0]
            h2 = f2.shape[0]
            self.metadata_updated.emit((w1, h1, w2, h2))
            self.mixed_frame_ready.emit(qimg)

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

    def set_mode(self, mode):
        self.mode = mode

    def set_checker_size(self, size):
        self.checker_size = max(1, int(size))

    def mix_frames(self, f1, f2):
        if self.mode == "zigzag":
            return self.mix_zigzag(f1, f2)
        if self.mode == "checker":
            return self.mix_checkerboard(f1, f2)
        return self.mix_columns(f1, f2)

    def mix_columns(self, f1, f2):
        result = f1.copy()
        result[:, ::2] = f2[:, ::2]
        return result

    def mix_checkerboard(self, f1, f2):
        block = max(1, self.checker_size)
        h, w = f1.shape[:2]
        yy = np.arange(h)[:, None] // block
        xx = np.arange(w)[None, :] // block
        mask = ((yy + xx) % 2) == 0
        result = f1.copy()
        result[mask] = f2[mask]
        return result

    def mix_zigzag(self, f1, f2):
        h, w = f1.shape[:2]
        yy = np.arange(h)[:, None]
        xx = np.arange(w)[None, :]
        mask = ((yy + xx) % 2) == 0

        result = f1.copy()
        result[~mask, 0] = f2[~mask, 0]
        result[mask, 1] = f2[mask, 1]
        result[~mask, 2] = f2[~mask, 2]
        return result

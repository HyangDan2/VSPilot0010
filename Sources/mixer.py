from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
import cv2
import numpy as np
from queue import Empty

class MixingThread(QThread):
    mixed_frame_ready = Signal(QImage)
    metadata_updated = Signal(tuple)

    def __init__(self, queue1, queue2):
        super().__init__()
        self.q1 = queue1
        self.q2 = queue2
        self.running = True

    def run(self):
        while self.running:
            try:
                f1 = self.q1.get(timeout=1)
                f2 = self.q2.get(timeout=1)

                # 해상도 맞추기
                if f1.shape != f2.shape:
                    f2 = cv2.resize(f2, (f1.shape[1], f1.shape[0]))

                mixed = self.mix_columns(f1, f2)
                h, w, ch = mixed.shape
                rgb = cv2.cvtColor(mixed, cv2.COLOR_BGR2RGB)
                qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
                w1 = f1.shape[1]
                w2 = f2.shape[1]
                h1 = f1.shape[0]
                h2 = f2.shape[0]
                self.metadata_updated.emit((w1, h1, w2, h2))
                self.mixed_frame_ready.emit(qimg)

            except Empty:
                continue

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

    def mix_columns(self, f1, f2):
        result = f1.copy()
        result[:, ::2] = f2[:, ::2]
        return result

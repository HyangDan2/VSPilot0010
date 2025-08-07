import time
import numpy as np
from queue import Queue
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QFileDialog, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QImage, QAction

from Sources.decoder import VideoDecoder
from Sources.mixer import MixingThread
from Sources.utils import ImageLoader


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Column Video Mixer: Odd/Even Columns")
        self.resize(1280, 720)

        self.q1 = Queue()
        self.q2 = Queue()

        self.label = QLabel("🔲 Mixed Output")
        self.label.setStyleSheet("background-color: black; color: white;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.setCentralWidget(self.label)

        self.path1 = ""
        self.path2 = ""
        self.decoder1 = None
        self.decoder2 = None
        self.mixer = None
        
        self.init_menu()

    def init_menu(self):
        menubar = self.menuBar()

        # File 메뉴
        file_menu = menubar.addMenu("File")
        load1_action = QAction("Load 1", self)
        load2_action = QAction("Load 2", self)
        load1_action.triggered.connect(self.load_source1)
        load2_action.triggered.connect(self.load_source2)
        file_menu.addAction(load1_action)
        file_menu.addAction(load2_action)

        # Play 메뉴
        play_menu = menubar.addMenu("Play")
        start_action = QAction("▶ Start", self)
        stop_action = QAction("⏹ Stop", self)
        start_action.triggered.connect(self.start_mixing)
        stop_action.triggered.connect(self.stop_all)
        play_menu.addAction(start_action)
        play_menu.addAction(stop_action)

    def load_source1(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Video/Image 1")
        if path:
            self.path1 = path

    def load_source2(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Video/Image 2")
        if path:
            self.path2 = path

    def start_mixing(self):
        if not self.path1 or not self.path2:
            return

        self.stop_all()  # 기존 스레드 정지
        self.clear_queue(self.q1)
        self.clear_queue(self.q2)

        # decoder1 생성
        if self.path1.lower().endswith((".mp4", ".avi", ".mov")):
            self.decoder1 = VideoDecoder(self.path1)
        else:
            self.decoder1 = ImageFeeder(self.path1)
        self.decoder1.frame_ready.connect(lambda f: self.q1.put(f))
        self.decoder1.start()

        # decoder2 생성
        if self.path2.lower().endswith((".mp4", ".avi", ".mov")):
            self.decoder2 = VideoDecoder(self.path2)
        else:
            self.decoder2 = ImageFeeder(self.path2)
        self.decoder2.frame_ready.connect(lambda f: self.q2.put(f))
        self.decoder2.start()

        # mixer 시작
        self.mixer = MixingThread(self.q1, self.q2)
        self.mixer.mixed_frame_ready.connect(self.update_display)
        self.mixer.start()


    def stop_all(self):
        if self.decoder1:
            self.decoder1.stop()
            self.decoder1 = None
        if self.decoder2:
            self.decoder2.stop()
            self.decoder2 = None
        if self.mixer:
            self.mixer.stop()
            self.mixer = None

    def update_display(self, qimg: QImage):
        pix = QPixmap.fromImage(qimg).scaled(
            self.label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.label.setPixmap(pix)

    def closeEvent(self, event):
        self.stop_all()
        event.accept()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_1:
            self.load_source1()
        elif key == Qt.Key.Key_2:
            self.load_source2()
        elif key == Qt.Key.Key_3:
            self.start_mixing()
        elif key == Qt.Key.Key_4:
            self.stop_all()
        elif key == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
                
    @staticmethod
    def clear_queue(q):
        while not q.empty():
            try:
                q.get_nowait()
            except:
                break
                
    # 새로운 클래스: 이미지 반복 공급자
class ImageFeeder(QThread):
    frame_ready = Signal(np.ndarray)

    def __init__(self, path, fps=30):
        super().__init__()
        self.path = path
        self.running = True
        self.fps = fps

    def run(self):
        img = ImageLoader.load_image(self.path)
        delay = 1.0 / self.fps
        while self.running:
            self.frame_ready.emit(img.copy())
            time.sleep(delay)

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


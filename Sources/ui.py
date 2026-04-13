import time
import numpy as np
from queue import Queue, Full
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QFileDialog,
    QSizePolicy, QFrame, QSlider, QComboBox, QSpinBox
)
from PySide6.QtCore import Qt, QThread, Signal, QEvent
from PySide6.QtGui import QPixmap, QImage, QAction, QResizeEvent, QPainter

from Sources.decoder import VideoDecoder
from Sources.mixer import MixingThread
from Sources.utils import ImageLoader
from Sources.VideoLabel import VideoLabel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Column Video Mixer: Odd/Even Columns")
        self.resize(1280, 720)

        self.q1 = Queue(maxsize=10)
        self.q2 = Queue(maxsize=10)

        self.container = QWidget()
        self.container.setMouseTracking(True)

        self.label = VideoLabel("🔲 Mixed Output")
        self.label.setStyleSheet("background-color: black; color: white;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.label.setMouseTracking(True)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)

        self.current_metadata = {
            "left": {"width": None, "height": None},
            "right": {"width" : None, "height" : None},
            "tooltip_enabled" : False
            }        
        self.setCentralWidget(self.container)

        self.path1 = ""
        self.path2 = ""
        self.decoder1 = None
        self.decoder2 = None
        self.mixer = None
        self.frame_counts = {1: 0, 2: 0}
        self.current_frames = {1: 0, 2: 0}
        self.slider_dragging = {1: False, 2: False}
        self.mixing_mode = "columns"
        self.checker_size = 16
        
        self.init_menu()
        self.init_control_overlay()
        self.container.installEventFilter(self)
        self.label.installEventFilter(self)

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

    def init_control_overlay(self):
        self.overlay = QFrame(self.container)
        self.overlay.setObjectName("videoControlOverlay")
        self.overlay.setMouseTracking(True)
        self.overlay.setStyleSheet("""
            QFrame#videoControlOverlay {
                background-color: rgba(18, 18, 18, 220);
                border: 1px solid rgba(255, 255, 255, 120);
                border-radius: 8px;
            }
            QLabel {
                color: white;
                font-weight: 600;
            }
            QPushButton {
                min-width: 56px;
                padding: 6px 10px;
                color: white;
                background-color: rgba(70, 70, 70, 230);
                border: 1px solid rgba(255, 255, 255, 140);
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(95, 95, 95, 235);
            }
            QComboBox, QSpinBox {
                color: white;
                background-color: rgba(40, 40, 40, 235);
                border: 1px solid rgba(255, 255, 255, 140);
                border-radius: 6px;
                padding: 4px 8px;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: rgba(255, 255, 255, 70);
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                margin: -5px 0;
                background: white;
                border-radius: 8px;
            }
        """)
        overlay_layout = QVBoxLayout(self.overlay)
        overlay_layout.setContentsMargins(14, 12, 14, 12)
        overlay_layout.setSpacing(8)

        self.progress_sliders = {}
        self.progress_labels = {}
        for index in (1, 2):
            row = QHBoxLayout()
            row.setSpacing(10)
            title = QLabel(f"Video {index}")
            title.setFixedWidth(64)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 0)
            slider.sliderPressed.connect(lambda i=index: self.set_slider_dragging(i, True))
            slider.sliderReleased.connect(lambda i=index: self.seek_video(i))
            frame_label = QLabel("0 / 0")
            frame_label.setFixedWidth(110)
            play_button = QPushButton("Play")
            stop_button = QPushButton("Stop")
            play_button.clicked.connect(lambda _, i=index: self.set_video_paused(i, False))
            stop_button.clicked.connect(lambda _, i=index: self.set_video_paused(i, True))

            self.progress_sliders[index] = slider
            self.progress_labels[index] = frame_label
            row.addWidget(title)
            row.addWidget(slider, 1)
            row.addWidget(frame_label)
            row.addWidget(play_button)
            row.addWidget(stop_button)
            overlay_layout.addLayout(row)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        mode_row.addWidget(QLabel("Mix"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Odd/Even Columns", "columns")
        self.mode_combo.addItem("Checker-board", "checker")
        self.mode_combo.currentIndexChanged.connect(self.change_mixing_mode)
        mode_row.addWidget(self.mode_combo)
        mode_row.addWidget(QLabel("Checker pixels"))
        self.checker_spin = QSpinBox()
        self.checker_spin.setRange(1, 512)
        self.checker_spin.setValue(self.checker_size)
        self.checker_spin.valueChanged.connect(self.change_checker_size)
        mode_row.addWidget(self.checker_spin)
        mode_row.addStretch(1)
        overlay_layout.addLayout(mode_row)

        self.overlay.hide()
        self.overlay.installEventFilter(self)

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
        self.decoder1.frame_ready.connect(lambda f: self.put_safe(self.q1, f))
        self.decoder1.frame_info_updated.connect(lambda current, total: self.update_frame_info(1, current, total))
        self.decoder1.start()

        # decoder2 생성
        if self.path2.lower().endswith((".mp4", ".avi", ".mov")):
            self.decoder2 = VideoDecoder(self.path2)
        else:
            self.decoder2 = ImageFeeder(self.path2)
        self.decoder2.frame_ready.connect(lambda f: self.put_safe(self.q2, f))
        self.decoder2.frame_info_updated.connect(lambda current, total: self.update_frame_info(2, current, total))
        self.decoder2.start()

        # mixer 시작
        self.mixer = MixingThread(self.q1, self.q2)
        self.mixer.set_mode(self.mixing_mode)
        self.mixer.set_checker_size(self.checker_size)
        self.mixer.mixed_frame_ready.connect(self.update_display)
        self.mixer.metadata_updated.connect(self.update_metadata)
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

    def set_video_paused(self, index, paused):
        decoder = self.decoder1 if index == 1 else self.decoder2
        if not decoder:
            return
        if paused:
            decoder.pause()
        else:
            decoder.play()

    def set_slider_dragging(self, index, dragging):
        self.slider_dragging[index] = dragging

    def seek_video(self, index):
        self.slider_dragging[index] = False
        decoder = self.decoder1 if index == 1 else self.decoder2
        if not decoder:
            return
        decoder.seek(self.progress_sliders[index].value())

    def update_frame_info(self, index, current, total):
        self.current_frames[index] = current
        self.frame_counts[index] = total
        slider = self.progress_sliders[index]
        if total > 0:
            slider.setEnabled(True)
            slider.setRange(0, max(0, total - 1))
            if not self.slider_dragging[index]:
                slider.setValue(max(0, current - 1))
        else:
            slider.setEnabled(False)
            slider.setRange(0, 0)
        self.progress_labels[index].setText(f"{current} / {total}")

    def change_mixing_mode(self):
        self.mixing_mode = self.mode_combo.currentData()
        if self.mixer:
            self.mixer.set_mode(self.mixing_mode)

    def change_checker_size(self, value):
        self.checker_size = value
        if self.mixer:
            self.mixer.set_checker_size(value)

    def update_display(self, qimg: QImage):
        pix = QPixmap.fromImage(qimg).scaled(
            self.label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.label.setPixmap(pix)

    def update_metadata(self, sizes):
        w1, h1, w2, h2 = sizes
        self.current_metadata['left']['width'] = w1
        self.current_metadata['left']['height'] = h1
        self.current_metadata['right']['width'] = w2
        self.current_metadata['right']['height'] = h2
        
        left = f"{self.current_metadata['left']['width']}x{self.current_metadata['left']['height']}"
        right = f"{self.current_metadata['right']['width']}x{self.current_metadata['right']['height']}"
        self.label.set_metadata(f"Left:{left}|Right:{right}")
        self.label.show_metadata = self.current_metadata["tooltip_enabled"]
        self.update()

    def resizeEvent(self, event):
        self.position_overlay()
        if self.label.pixmap():
            self.update_display(self.label.pixmap().toImage())
        return super().resizeEvent(event)

    def moveEvent(self, event):
        if self.label.pixmap():
            self.update_display(self.label.pixmap().toImage())
        return super().moveEvent(event)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseMove:
            point = event.position().toPoint()
            if obj is self.label:
                point = self.label.mapTo(self.container, point)
            elif obj is self.overlay:
                point = self.overlay.mapTo(self.container, point)
            if point.y() >= int(self.container.height() * 0.8):
                self.position_overlay()
                self.overlay.show()
                self.overlay.raise_()
            elif not self.overlay.geometry().contains(point):
                self.overlay.hide()
        elif event.type() == QEvent.Type.Leave and obj is self.container:
            self.overlay.hide()
        return super().eventFilter(obj, event)

    def position_overlay(self):
        if not hasattr(self, "overlay"):
            return
        margin = 18
        height = 150
        self.overlay.setGeometry(
            margin,
            max(margin, self.container.height() - height - margin),
            max(100, self.container.width() - margin * 2),
            height
        )

    def closeEvent(self, event):
        self.stop_all()
        event.accept()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_1:
            self.load_source1()
        elif key == Qt.Key.Key_2:
            self.load_source2()
        elif key == Qt.Key.Key_Space:
            self.start_mixing()
        elif key == Qt.Key.Key_P:
            self.stop_all()
        elif key == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
                self.menuBar().show()
            else:
                self.showFullScreen()
                self.menuBar().hide()
        elif key == Qt.Key.Key_Tab:
            self.current_metadata["tooltip_enabled"] = not self.current_metadata["tooltip_enabled"]
            self.label.show_metadata = self.current_metadata["tooltip_enabled"]
            self.label.update()
        elif key == Qt.Key.Key_S:
            temp_path1 = self.path1
            temp_path2 = self.path2
            self.path1 = temp_path2
            self.path2 = temp_path1
            self.start_mixing()
                
    def put_safe(self, q, f):
        try:
            q.put_nowait(f)
        except Full:
            pass
                
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
    frame_info_updated = Signal(int, int)

    def __init__(self, path, fps=30):
        super().__init__()
        self.path = path
        self.running = True
        self.paused = False
        self.fps = fps

    def run(self):
        img = ImageLoader.load_image(self.path)
        delay = 1.0 / self.fps
        while self.running:
            if not self.paused:
                self.frame_ready.emit(img.copy())
                self.frame_info_updated.emit(1, 1)
            time.sleep(delay)

    def play(self):
        self.paused = False

    def pause(self):
        self.paused = True

    def seek(self, frame):
        self.frame_info_updated.emit(1, 1)

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

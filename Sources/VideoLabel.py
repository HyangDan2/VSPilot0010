from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtWidgets import QLabel

class VideoLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metadata_text = ""
        self.show_metadata = True 

    def set_metadata(self, text):
        self.metadata_text = text
        self.update()

    def paintEvent(self,event):
        super().paintEvent(event)

        if self.show_metadata and self.metadata_text:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(QColor(255,255,255))
            painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            painter.drawText(10, 25, self.metadata_text)
            painter.end()

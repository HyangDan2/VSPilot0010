import cv2
import numpy as np

class ImageLoader:
    @staticmethod
    def load_image(path: str) -> np.ndarray:
        img = cv2.imread(path)
        if img is None:
            raise FileNotFoundError(f"Image at path '{path}' could not be loaded.")
        return img

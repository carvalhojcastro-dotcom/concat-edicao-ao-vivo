"""Detecção (YuNet) + boca (FaceLandmarker no recorte do rosto)."""
import os, cv2, numpy as np, mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision
YUNET = "/Users/joaopedro/.claude/plugins/cache/edit-labs-ai/edit-labs-ai/1.0.0/skills/corte-viral/models/face_detection_yunet_2023mar.onnx"
LMK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "modelos", "face_landmarker.task")
class Rostos:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.det = cv2.FaceDetectorYN.create(YUNET, "", (w, h), score_threshold=0.6, nms_threshold=0.3, top_k=10)
        self.lmk = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=LMK), num_faces=1,
            min_face_detection_confidence=0.2, min_face_presence_confidence=0.2, output_face_blendshapes=True))
    def __call__(self, rgb):
        """-> [(cx, cy, fh, boca)] normalizados no quadro."""
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        _, faces = self.det.detect(bgr)
        out = []
        if faces is None:
            return out
        for f in faces:
            x, y, w, h = f[:4]
            if w < 0.04 * self.w:
                continue
            cx, cy = x + w / 2, y + h / 2
            m = 0.9 * max(w, h)
            x0, y0 = int(max(cx - m, 0)), int(max(cy - m, 0))
            x1, y1 = int(min(cx + m, self.w)), int(min(cy + m, self.h))
            crop = cv2.resize(rgb[y0:y1, x0:x1], (256, 256))
            boca = 0.0
            r = self.lmk.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(crop)))
            if r.face_landmarks:
                p = np.array([[q.x, q.y] for q in r.face_landmarks[0]])
                fh = abs(p[152, 1] - p[10, 1]) or 1e-3
                jaw = next((c.score for c in r.face_blendshapes[0] if c.category_name == "jawOpen"), 0)
                boca = abs(p[14, 1] - p[13, 1]) / fh + 0.3 * jaw
            out.append((cx / self.w, cy / self.h, h / self.h, float(boca)))
        return out

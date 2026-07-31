import io
import re

import numpy as np


class OCRResult:
    def __init__(self, txts):
        self.txts = txts

    def __bool__(self):
        return bool(self.txts)


class RapidOCR:
    def __init__(self, *args, **kwargs):
        from rapidocr_onnxruntime import RapidOCR as _RapidOCR
        self._ocr = _RapidOCR(*args, **kwargs)

    @staticmethod
    def _prepare(img):
        """Load and enhance the input image for better recognition accuracy."""
        try:
            from PIL import Image
            import cv2

            if isinstance(img, (str, bytes)):
                data = img if isinstance(img, bytes) else open(img, "rb").read()
                img = Image.open(io.BytesIO(data)).convert("RGB")
            elif hasattr(img, "convert"):
                img = img.convert("RGB")

            arr = np.array(img)

            if arr.shape[0] < 300 or arr.shape[1] < 300:
                scale = max(1.0, 1400.0 / min(arr.shape[:2]))
                arr = cv2.resize(
                    arr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
                )

            gray = (
                arr
                if len(arr.shape) == 2
                else cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            )

            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            return enhanced
        except Exception:
            return img

    @staticmethod
    def _merge_lines(result):
        """Reconstruct logical lines from OCR boxes using positions."""
        if not result:
            return []
        boxes = []
        for item in result:
            if len(item) < 2:
                continue
            box = item[0]
            text = item[1]
            try:
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
            except (TypeError, IndexError):
                continue
            boxes.append(
                {
                    "text": str(text),
                    "x0": min(xs),
                    "x1": max(xs),
                    "yc": sum(ys) / len(ys),
                    "h": max(ys) - min(ys),
                }
            )
        if not boxes:
            return []

        boxes.sort(key=lambda b: (b["yc"], b["x0"]))

        lines = []
        current = [boxes[0]]
        for b in boxes[1:]:
            cur_y0 = min(x["yc"] - x["h"] / 2 for x in current)
            cur_y1 = max(x["yc"] + x["h"] / 2 for x in current)
            b_y0 = b["yc"] - b["h"] / 2
            b_y1 = b["yc"] + b["h"] / 2
            overlap = min(cur_y1, b_y1) - max(cur_y0, b_y0)
            if overlap >= max(min(b["h"], max(x["h"] for x in current)) * 0.3, 2):
                current.append(b)
            else:
                lines.append(current)
                current = [b]
        lines.append(current)

        merged = []
        for line in lines:
            line.sort(key=lambda b: b["x0"])
            parts = []
            prev_x1 = None
            for b in line:
                if prev_x1 is not None:
                    gap = b["x0"] - prev_x1
                    if gap > max(b["h"] * 0.6, 8):
                        parts.append(" ")
                parts.append(b["text"])
                prev_x1 = b["x1"]
            merged.append(RapidOCR._clean_text("".join(parts)))

        return merged

    @staticmethod
    def _clean_text(text):
        """Fix common OCR artifacts on numbers and units."""
        text = re.sub(r"(?<=\d)\.\s+(?=\d)", ".", text)
        text = re.sub(r"(?<=\d)\s+\.(?=\d)", ".", text)
        text = re.sub(r"(?<=\d)\s*×\s*(?=\d)", "×", text)
        text = re.sub(r"(?<=\d)\s*[/]\s*(?=\d)", "/", text)
        text = re.sub(
            r"(?<=\d)\s*(?:kW|KW|kv|KV|MW|W|V|A|Ah|ah)\b",
            lambda m: m.group(0).replace(" ", ""),
            text,
        )
        return text

    def __call__(self, img_content, **kwargs):
        try:
            img = self._prepare(img_content)
            result, elapse = self._ocr(img, **kwargs)
        except Exception as e:
            raise RuntimeError(f"OCR failed: {type(e).__name__}: {e}") from e

        if result is None:
            return OCRResult([])
        return OCRResult(self._merge_lines(result))

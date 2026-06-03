import pytesseract
from PIL import Image
import io
from config import OCR_SPARSE_THRESHOLD
pytesseract.pytesseract.tesseract_cmd = r'D:\apps\tesseract\tesseract.exe'

def extract(image_bytes: bytes) -> tuple[str, bool]:
    """
    Returns (text, is_sparse).
    is_sparse=True means Vision fallback should be used.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img).strip()
        word_count = len(text.split())
        is_sparse = word_count < OCR_SPARSE_THRESHOLD
        return text, is_sparse
    except Exception:
        return "", True

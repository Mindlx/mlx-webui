import io
import logging
import os
import sys
from typing import List

from langchain_core.documents import Document

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)

IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp']


class LocalOCRLoader:
    """Loader that uses local RapidOCR (rapidocr_onnxruntime, CPU/ONNX) to extract text."""

    def __init__(self, file_path: str):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'File not found at {file_path}')
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)

    @staticmethod
    def _pages_to_images(pdf_bytes: bytes, dpi: int = 200):
        """Render PDF pages to PNG bytes. pypdfium2 (bundled with pypdf) is used."""
        import pypdfium2 as pdfium
        from PIL import Image

        doc = pdfium.PdfDocument(pdf_bytes, password=None)
        try:
            for page in doc:
                bitmap = page.render(scale=dpi / 72.0)
                pil = bitmap.to_pil()
                out = io.BytesIO()
                pil.save(out, format='PNG')
                yield out.getvalue()
        finally:
            doc.close()

    def load(self) -> List[Document]:
        log.info(f'Processing with local OCR: {self.file_path}')

        try:
            from open_webui.retrieval.loaders.rapidocr import RapidOCR

            ocr = RapidOCR()
        except Exception as e:
            log.error(f'Failed to initialize local OCR: {e}')
            return [
                Document(
                    page_content=f'Error during OCR processing: {e}',
                    metadata={
                        'error': 'processing_failed',
                        'file_name': self.file_name,
                        'processing_engine': 'local-ocr',
                    },
                )
            ]

        ext = self.file_path.lower().split('.')[-1]
        is_image = ext in IMAGE_EXTENSIONS

        documents = []
        try:
            if is_image:
                with open(self.file_path, 'rb') as f:
                    result = ocr(f.read())
                text = '\n'.join(result.txts) if result else ''
                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            'file_name': self.file_name,
                            'processing_engine': 'local-ocr',
                        },
                    )
                )
            else:
                with open(self.file_path, 'rb') as f:
                    pdf_bytes = f.read()
                for i, img_bytes in enumerate(self._pages_to_images(pdf_bytes)):
                    result = ocr(img_bytes)
                    text = '\n'.join(result.txts) if result else ''
                    documents.append(
                        Document(
                            page_content=text,
                            metadata={
                                'page': i,
                                'page_label': i + 1,
                                'total_pages': None,
                                'file_name': self.file_name,
                                'processing_engine': 'local-ocr',
                            },
                        )
                    )
        except Exception as e:
            log.error(f'Error during local OCR processing: {e}')
            return [
                Document(
                    page_content=f'Error during OCR processing: {e}',
                    metadata={
                        'error': 'processing_failed',
                        'file_name': self.file_name,
                        'processing_engine': 'local-ocr',
                    },
                )
            ]

        return documents

import sys
import types
from unittest.mock import MagicMock, patch

langchain_core = types.ModuleType('langchain_core')
langchain_documents = types.ModuleType('langchain_core.documents')


class _Document:
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}


langchain_documents.Document = _Document
langchain_core.documents = langchain_documents
sys.modules['langchain_core'] = langchain_core
sys.modules['langchain_core.documents'] = langchain_documents

sys.path.insert(0, 'backend')
from open_webui.retrieval.loaders.local_ocr import LocalOCRLoader


def test_load_pdf_pages(tmp_path):
    pdf_file = tmp_path / 'fake.pdf'
    pdf_file.write_bytes(b'fake-pdf-bytes')

    fake_rapidocr = MagicMock()
    fake_result = MagicMock()
    fake_result.txts = ['line1', 'line2']
    fake_result.__bool__.return_value = True
    fake_result.side_effect = lambda *a, **k: fake_result
    fake_rapidocr.return_value = fake_result

    fake_mod = types.ModuleType('open_webui.retrieval.loaders.rapidocr')
    fake_mod.RapidOCR = fake_rapidocr

    with patch.object(
        LocalOCRLoader, '_pages_to_images', return_value=[b'png1', b'png2']
    ), patch.dict(sys.modules, {
        'open_webui.retrieval.loaders.rapidocr': fake_mod
    }):
        loader = LocalOCRLoader(str(pdf_file))
        docs = loader.load()

    assert len(docs) == 2
    assert docs[0].page_content == 'line1\nline2'
    assert docs[0].metadata['processing_engine'] == 'local-ocr'
    assert docs[0].metadata['page_label'] == 1


def test_load_image(tmp_path):
    img_file = tmp_path / 'fake.png'
    img_file.write_bytes(b'fake-png-bytes')

    fake_rapidocr = MagicMock()
    fake_result = MagicMock()
    fake_result.txts = ['img text']
    fake_result.__bool__.return_value = True
    fake_result.side_effect = lambda *a, **k: fake_result
    fake_rapidocr.return_value = fake_result

    fake_mod = types.ModuleType('open_webui.retrieval.loaders.rapidocr')
    fake_mod.RapidOCR = fake_rapidocr

    with patch.dict(sys.modules, {
        'open_webui.retrieval.loaders.rapidocr': fake_mod
    }):
        loader = LocalOCRLoader(str(img_file))
        docs = loader.load()

    assert len(docs) == 1
    assert docs[0].page_content == 'img text'
    assert docs[0].metadata['file_name'] == 'fake.png'


def test_load_ocr_error_returns_error_document(tmp_path):
    img_file = tmp_path / 'fake.png'
    img_file.write_bytes(b'fake-png-bytes')

    fake_rapidocr = MagicMock()
    fake_rapidocr.side_effect = RuntimeError('boom')

    fake_mod = types.ModuleType('open_webui.retrieval.loaders.rapidocr')
    fake_mod.RapidOCR = fake_rapidocr

    with patch.dict(sys.modules, {
        'open_webui.retrieval.loaders.rapidocr': fake_mod
    }):
        loader = LocalOCRLoader(str(img_file))
        docs = loader.load()

    assert len(docs) == 1
    assert docs[0].metadata.get('error') == 'processing_failed'


def test_load_missing_file_raises():
    try:
        LocalOCRLoader('/tmp/does-not-exist-xyz.pdf')
    except FileNotFoundError:
        assert True
    else:
        raise AssertionError('expected FileNotFoundError')

import sys
import types

import numpy

rapidocr_onnxruntime_stub = types.ModuleType('rapidocr_onnxruntime')

class _StubRapidOCR:
    def __init__(self, *args, **kwargs):
        pass

rapidocr_onnxruntime_stub.RapidOCR = _StubRapidOCR
sys.modules['rapidocr_onnxruntime'] = rapidocr_onnxruntime_stub

sys.path.insert(0, 'backend')
from open_webui.retrieval.loaders.rapidocr import OCRResult, RapidOCR


def test_clean_text_decimal_spaces():
    assert RapidOCR._clean_text('SCB14-1600/10/0. 4') == 'SCB14-1600/10/0.4'
    assert RapidOCR._clean_text('8. 7') == '8.7'


def test_clean_text_multiplication_unit():
    assert RapidOCR._clean_text('100 × 10') == '100×10'
    assert RapidOCR._clean_text('1400 kW') == '1400kW'
    assert RapidOCR._clean_text('3200kv') == '3200kv'


def test_merge_lines_reconstructs_rows():
    result = [
        ([[0, 0], [100, 0], [100, 20], [0, 20]], '设备名称'),
        ([[120, 0], [220, 0], [220, 20], [120, 20]], 'SCB14-1600'),
        ([[0, 30], [200, 30], [200, 50], [0, 50]], '合计'),
    ]
    merged = RapidOCR._merge_lines(result)
    assert merged[0] == '设备名称 SCB14-1600'
    assert merged[1] == '合计'


def test_merge_lines_empty():
    assert RapidOCR._merge_lines([]) == []
    assert RapidOCR._merge_lines(None) == []


def test_ocr_result_bool():
    assert bool(OCRResult(['a']))
    assert not bool(OCRResult([]))

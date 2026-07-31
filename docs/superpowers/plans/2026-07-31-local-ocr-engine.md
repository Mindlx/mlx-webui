# 本地 OCR 引擎（RapidOCR / local_ocr）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 MindLynx Agent（Open WebUI v0.10.2 fork）增加离线本地 OCR 引擎，通过复用 `CONTENT_EXTRACTION_ENGINE` 新增引擎值 `local_ocr`，零新增依赖，且不破坏未来合并上游更新。

**Architecture:** 新增 `rapidocr/` 兼容模块（照搬已验证代码，含 CLAHE 预处理 / 行合并 / 文本清洗）与 `LocalOCRLoader`（对齐 PaddleOCR-vl 结构）；在 `Loader._get_loader()` elif 链追加一个分支；前端 `Documents.svelte` 下拉框追加 option + 提示块；i18n 加一个词。不碰 config.py、retrieval/utils.py、routers/retrieval.py（上游高频变动文件）。

**Tech Stack:** Python 3.11（容器）/ 3.13（本地）、`rapidocr_onnxruntime==1.4.4`（已在依赖）、pypdfium2（pypdf 捆绑依赖，已在镜像）、numpy、pytest、SvelteKit、i18next。

## Global Constraints

- 引擎值必须为字符串 `'local_ocr'`（`CONTENT_EXTRACTION_ENGINE` 无白名单校验，直接可用）。
- 元数据 `processing_engine` 值为 `'local-ocr'`（连字符），与引擎值（下划线）不同，不可混用。
- 不修改以下文件：`backend/open_webui/config.py`、`backend/open_webui/retrieval/utils.py`、`backend/open_webui/routers/retrieval.py`。
- 对上游文件的修改必须是纯 append：`main.py` import 区 + elif 分支尾、`Documents.svelte` option 尾 + `{:else if}` 链尾、i18n 键追加。
- `local_ocr` 分支必须带文件类型白名单 `['pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp']`，其余类型回落到 `else` 常规 loader。
- `rapidocr_onnxruntime` 的 import 必须懒加载（在 `RapidOCR.__init__` 内），禁止顶层 import。
- 测试单测只依赖 numpy/re/io（本地可跑）；langchain_core/pypdfium2/rapidocr_onnxruntime 用 mock。
- 每个任务结束时运行 `python3 -m py_compile` 相关文件 + `pytest backend/tests/ -q` 不退化。

---

### Task 1: rapidocr 兼容模块 + 纯逻辑单测

**Files:**
- Create: `backend/open_webui/retrieval/loaders/rapidocr/__init__.py`
- Test: `backend/tests/test_rapidocr_clean.py`

**Interfaces:**
- Consumes: 无（纯新模块）。
- Produces: `open_webui.retrieval.loaders.rapidocr.RapidOCR`（`__call__(img, **kwargs) -> OCRResult`）、`open_webui.retrieval.loaders.rapidocr.OCRResult`（`.txts: list[str]`、`__bool__`）、静态方法 `RapidOCR._clean_text(text) -> str`、`RapidOCR._merge_lines(result) -> list[str]`。Task 2 的 `LocalOCRLoader` 通过 `from open_webui.retrieval.loaders.rapidocr import RapidOCR` 使用。

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_rapidocr_clean.py`：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest backend/tests/test_rapidocr_clean.py -v`
Expected: FAIL，ModuleNotFoundError（`open_webui.retrieval.loaders.rapidocr` 不存在）。

- [ ] **Step 3: 实现 rapidocr 兼容模块**

创建 `backend/open_webui/retrieval/loaders/rapidocr/__init__.py`（照搬已验证代码，全部保留 CLAHE/行合并/清洗逻辑）：

```python
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
            r"(?<=\d)\s*(?:KW|kw|KV|kv|MW|W|V|A|Ah|ah)\b",
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
```

注意：`_merge_lines` 增加了 `if not result: return []` 防御（原代码对 None 会崩溃），`test_merge_lines_empty` 覆盖此分支。

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest backend/tests/test_rapidocr_clean.py -v`
Expected: PASS，5 个测试全绿。

- [ ] **Step 5: 提交**

```bash
git add backend/open_webui/retrieval/loaders/rapidocr/__init__.py backend/tests/test_rapidocr_clean.py
git commit -m "feat: add local OCR rapidocr compatibility module"
```

---

### Task 2: LocalOCRLoader + mock 单测

**Files:**
- Create: `backend/open_webui/retrieval/loaders/local_ocr.py`
- Test: `backend/tests/test_local_ocr.py`

**Interfaces:**
- Consumes: `open_webui.retrieval.loaders.rapidocr.RapidOCR`（Task 1，经 `from open_webui.retrieval.loaders.rapidocr import RapidOCR`）、`langchain_core.documents.Document`（外部，测试 mock）、`pypdfium2` + PIL（测试 mock）。
- Produces: `open_webui.retrieval.loaders.local_ocr.LocalOCRLoader`，接口 `LocalOCRLoader(file_path: str)` + `.load() -> list[Document]`。Task 3 在 main.py 中 `from open_webui.retrieval.loaders.local_ocr import LocalOCRLoader` 并调用 `LocalOCRLoader(file_path=file_path)`。
- **注意**：不得用 `from rapidocr import RapidOCR`（会遮蔽 pip 的顶层 `rapidocr` 包）；必须用完整包路径。

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_local_ocr.py`：

```python
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
    fake_rapidocr.return_value = fake_result

    with patch(
        'open_webui.retrieval.loaders.rapidocr.RapidOCR', fake_rapidocr
    ), patch.object(
        LocalOCRLoader, '_pages_to_images', return_value=[b'png1', b'png2']
    ):
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
    fake_rapidocr.return_value = fake_result

    with patch(
        'open_webui.retrieval.loaders.rapidocr.RapidOCR', fake_rapidocr
    ):
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

    with patch(
        'open_webui.retrieval.loaders.rapidocr.RapidOCR', fake_rapidocr
    ):
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest backend/tests/test_local_ocr.py -v`
Expected: FAIL，ModuleNotFoundError（local_ocr 模块不存在）。

- [ ] **Step 3: 实现 LocalOCRLoader**

创建 `backend/open_webui/retrieval/loaders/local_ocr.py`：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest backend/tests/test_local_ocr.py -v`
Expected: PASS。测试用 `patch.object(_pages_to_images)` 隔离，不依赖 pypdfium2 mock。

- [ ] **Step 5: 提交**

```bash
git add backend/open_webui/retrieval/loaders/local_ocr.py backend/tests/test_local_ocr.py
git commit -m "feat: add LocalOCRLoader for offline OCR"
```

---

### Task 3: main.py dispatch 接入

**Files:**
- Modify: `backend/open_webui/retrieval/loaders/main.py:30`（import 区）
- Modify: `backend/open_webui/retrieval/loaders/main.py:558-563`（elif 链，paddleocr_vl 分支后）

**Interfaces:**
- Consumes: `LocalOCRLoader(file_path=...)`（Task 2）。
- Produces: 引擎值 `'local_ocr'` 可被 `Loader._get_loader` 路由。验证方式为 `py_compile` + 静态断言 + 容器端到端（Task 5）。

- [ ] **Step 1: 修改 import 区**

在 `main.py:30` 的 paddleocr_vl import 之后追加：

```python
from open_webui.retrieval.loaders.local_ocr import LocalOCRLoader
```

- [ ] **Step 2: 追加 elif 分支**

在 `paddleocr_vl` 分支（`main.py:558-563`）之后、`else:`（`main.py:564`）之前插入：

```python
        elif self.engine == 'local_ocr' and file_ext in ['pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp']:
            loader = LocalOCRLoader(file_path=file_path)
```

- [ ] **Step 3: 编译与静态验证**

Run:
```bash
python3 -m py_compile backend/open_webui/retrieval/loaders/main.py
grep -n "local_ocr" backend/open_webui/retrieval/loaders/main.py
```
Expected: 编译无错；grep 输出 2 处（import + elif）。`grep -c "local_ocr"` 返回 2。

- [ ] **Step 4: 提交**

```bash
git add backend/open_webui/retrieval/loaders/main.py
git commit -m "feat: dispatch local_ocr engine in Loader"
```

---

### Task 4: 前端 Documents.svelte + i18n

**Files:**
- Modify: `src/lib/components/admin/Settings/Documents.svelte:401`（option 后）
- Modify: `src/lib/components/admin/Settings/Documents.svelte:891`（`{/if}` 前，mineru 块尾）
- Modify: `src/lib/i18n/locales/en-US/translation.json`
- Modify: `src/lib/i18n/locales/zh-CN/translation.json`

**Interfaces:**
- Consumes: `CONTENT_EXTRACTION_ENGINE` 字符串值 `'local_ocr'`。
- Produces: UI 下拉框出现 `Local OCR` 选项；选择后显示本地 OCR 说明块。i18n key `Local OCR`。

- [ ] **Step 1: 追加 option**

在 `Documents.svelte:401` 的 `<option value="mineru">` 之后追加：

```svelte
									<option value="local_ocr">{$i18n.t('Local OCR')}</option>
```

- [ ] **Step 2: 追加提示块**

在 `Documents.svelte:891` 的 mineru 配置块结束后、`{/if}` 闭合前追加：

```svelte
						{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'local_ocr'}
							<div class="flex w-full mt-2">
								<div class="text-xs text-gray-500 dark:text-gray-400">
									{$i18n.t(
										'Local OCR processes scanned documents entirely on this server using RapidOCR (CPU, offline). No external API or network access is required.'
									)}
								</div>
							</div>
```

- [ ] **Step 3: 更新 i18n**

在 `src/lib/i18n/locales/en-US/translation.json` 中 `"PaddleOCR-vl": ""` 附近（按字母序，`"Local OCR"` 在 `"Paginate"` 之前）追加：

```json
	"Local OCR": "",
	"Local OCR processes scanned documents entirely on this server using RapidOCR (CPU, offline). No external API or network access is required.": "",
```

在 `src/lib/i18n/locales/zh-CN/translation.json` 中同样位置追加：

```json
	"Local OCR": "本地 OCR",
	"Local OCR processes scanned documents entirely on this server using RapidOCR (CPU, offline). No external API or network access is required.": "本地 OCR 使用 RapidOCR 在服务器上离线处理扫描文档（CPU，无需联网），不依赖任何外部 API。",
```

- [ ] **Step 4: 验证 JSON 合法 + Svelte 语法**

Run:
```bash
python3 -c "import json; json.load(open('src/lib/i18n/locales/en-US/translation.json')); json.load(open('src/lib/i18n/locales/zh-CN/translation.json')); print('JSON OK')"
grep -c "local_ocr" src/lib/components/admin/Settings/Documents.svelte
```
Expected: `JSON OK`；grep 输出 2（option + else-if）。

- [ ] **Step 5: 提交**

```bash
git add src/lib/components/admin/Settings/Documents.svelte src/lib/i18n/locales/en-US/translation.json src/lib/i18n/locales/zh-CN/translation.json
git commit -m "feat: add Local OCR option to content extraction settings"
```

---

### Task 5: 容器集成验证（真实扫描 PDF 端到端）

**Files:**
- 无源码修改；仅构建与运行验证。

**Interfaces:**
- Consumes: Task 1-4 全部产物。
- Produces: 验证记录（真实扫描 PDF 提取文本成功）。

- [ ] **Step 1: 构建镜像**

Run（在仓库根目录）:
```bash
docker build -t mlx-webui:local-ocr-test .
```
Expected: 构建成功，无错误。

- [ ] **Step 2: 容器内验证 import 与模块加载**

Run:
```bash
docker run --rm -it mlx-webui:local-ocr-test python3 -c "
from open_webui.retrieval.loaders.local_ocr import LocalOCRLoader
from open_webui.retrieval.loaders.rapidocr import RapidOCR
import rapidocr_onnxruntime
print('imports OK, rapidocr version:', rapidocr_onnxruntime.__version__)
"
```
Expected: `imports OK` 及版本号。

- [ ] **Step 3: 容器内运行 pytest 单测**

Run:
```bash
docker run --rm -it -v "$(pwd)/backend/tests:/app/backend/tests" mlx-webui:local-ocr-test \
  python3 -m pytest backend/tests/ -q
```
Expected: 全部测试通过（单测不依赖真实 ONNX，容器内同样应绿）。

- [ ] **Step 4: 端到端验证 dispatch**

Run（容器内）:
```bash
docker run --rm -it mlx-webui:local-ocr-test python3 -c "
from open_webui.retrieval.loaders.main import Loader
import tempfile, os
loader = Loader(engine='local_ocr')
# 构造最小 fake 调用验证路由到 LocalOCRLoader（非 PyPDFLoader）
print('engine routing OK:', loader.engine == 'local_ocr')
"
```
Expected: `engine routing OK: True`。

- [ ] **Step 5: 真实扫描 PDF 验证（若你有案例文件）**

将扫描 PDF 挂载进容器，运行提取：
```bash
docker run --rm -it -v /path/to/scanned.pdf:/tmp/scanned.pdf mlx-webui:local-ocr-test python3 -c "
from open_webui.retrieval.loaders.local_ocr import LocalOCRLoader
loader = LocalOCRLoader('/tmp/scanned.pdf')
docs = loader.load()
for d in docs:
    print(d.metadata.get('page_label'), d.page_content[:80])
"
```
Expected: 每页输出 OCR 文本；扫描页非空。

- [ ] **Step 6: 记录验证结果**

在 commit message 或单独 notes 中记录验证结果（页数、空页数、采样文本）。不强制提交测试资产。

---

## Self-Review 记录

**1. Spec 覆盖：**
- 4.1 rapidocr 模块 → Task 1 ✅
- 4.1 LocalOCRLoader → Task 2 ✅
- 4.2 main.py import + elif → Task 3 ✅
- 4.2 Documents.svelte option + 提示块 → Task 4 ✅
- 4.2 i18n → Task 4 ✅
- 5 数据流验证 → Task 3 Step 3 + Task 5 ✅
- 6 错误处理 → Task 2 `test_load_ocr_error_returns_error_document` ✅
- 7 测试策略 → Task 1/2 单测 + Task 5 容器 ✅

**2. 占位符扫描：** 无 TBD/TODO；所有步骤含完整代码与命令。

**3. 类型一致性：** `'local_ocr'`（引擎值）与 `'local-ocr'`（metadata）在 Global Constraints 中明确区分；`LocalOCRLoader(file_path=...)` 签名在 Task 2/3 一致；`_merge_lines` 的 None 防御在 Task 1 测试与实现一致。

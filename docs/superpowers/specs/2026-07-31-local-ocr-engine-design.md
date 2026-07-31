# 本地 OCR 引擎接入设计（RapidOCR / local_ocr）

**日期**: 2026-07-31
**状态**: 已批准
**范围**: MindLynx Agent fork（基于 Open WebUI v0.10.2）本地定制

---

## 1. 背景与目标

Open WebUI 的文档提取管线依赖远程/云 OCR（Mistral OCR、PaddleOCR-vl、MinerU、Datalab Marker），扫描 PDF / 图片在私有化、内网、中国区部署中遇到三类问题：

1. **隐私** — 敏感文档（合同、标书、董事会材料）被发送到第三方 API。
2. **可用性** — 远程服务不可达、限流或离线。
3. **成本** — 每页扫描件按次计费。

目标：增加一个 **100% 离线、CPU 运行、零新增依赖** 的本地 OCR 引擎。

**关键事实（已核实）**：`rapidocr-onnxruntime==1.4.4` 已锁定在依赖中（`backend/requirements.txt:91`、`pyproject.toml:99`），官方镜像自带。无需任何新依赖。

## 2. 架构约束（最高优先级）

**不破坏未来合并上游更新的能力。** 该 fork 的合并策略是"合并官方更新，保留所有个性化定制"，因此任何对上游文件的修改都必须最小化、可 append、3-way merge 友好。

### 2.1 上游加引擎的标准路径（PaddleOCR-vl PR #23945 范本）

上游新增一个引擎通常触碰 6 类文件：config.py PersistentConfig、loaders/main.py 分支、retrieval/utils.py 配置键、routers/retrieval.py ConfigForm、Documents.svelte、i18n。

### 2.2 本地 OCR 的特殊性 → 改动面剪裁

本地 OCR 是**零配置参数**引擎（无 API key / URL）。因此：

| 文件 | 上游标准路径 | 本设计 | 原因 |
|:-----|:------------|:-------|:-----|
| `config.py` PersistentConfig | 需要 | **不碰** | 无参数；engine 值无白名单校验，`'local_ocr'` 字符串直接可用 |
| `retrieval/utils.py` LOADER_CONFIG_KEYS | 需要 | **不碰** | `CONTENT_EXTRACTION_ENGINE` 键已存在（utils.py:74），loader 不需要额外 kwargs |
| `routers/retrieval.py` ConfigForm | 需要 | **不碰** | 无配置项需要前后端传递 |
| `retrieval/loaders/main.py` 分支 | 需要 | **改（append）** | dispatch 核心，必须接入 |
| `Documents.svelte` option | 需要 | **改（append）** | 否则 UI 无法选择引擎 |
| i18n translations | 需要 | **改（append）** | 一个显示词 |

**冲突收敛**：上游高频变动的 3 个文件（config.py、utils.py、routers/retrieval.py）零改动；仅 2 个文件做纯 append 式修改，3-way merge 大概率自动合并。

## 3. 引擎接入方式决策

**决策：复用 `CONTENT_EXTRACTION_ENGINE`，新增引擎值 `local_ocr`。**

论证（c1skill 8 阶段）：

- **Stage 0 原架构**：`CONTENT_EXTRACTION_ENGINE`（config.py:854）是刻意设计的闭合枚举 + 策略模式，无枚举校验。PaddleOCR-vl PR 是标准范本。
- **Stage 4 反方**：
  - *独立 `RAG_OCR_ENGINE` 变量* → 否决：破坏上游架构一致性，PR 会被拒；前端需独立配置 UI，扩大冲突面。
  - *auto 回退语义（远程未配置→本地）* → Phase 1 否决：改变现有默认行为（`''` 当前走 PyPDFLoader），行为变更 + 语义复杂化，merge 风险最高。可作后续 Phase。
- **Stage 7 自我批判**：方案对齐上游路径 = 增强而非违背。

## 4. 文件清单

### 4.1 新增（零冲突，上游不会同名）

**`backend/open_webui/retrieval/loaders/rapidocr/__init__.py`** — 兼容模块（照搬已验证代码）

- `OCRResult` 类：`txts` 属性 + `__bool__`
- `RapidOCR` 类：
  - `__init__` 懒加载 `from rapidocr_onnxruntime import RapidOCR`
  - `_prepare` 静态方法：图片加载（str/bytes/PIL）、小图放大（<300px → 1400px 目标）、灰度化、CLAHE 增强
  - `_merge_lines` 静态方法：按检测框坐标重构逻辑行（垂直重叠 + 水平间隙判定）
  - `_clean_text` 静态方法：修复数字/单位伪影（`0. 4`→`0.4`、`8. 7`→`8.7`、`100 × 10`→`100×10`、单位去空格）
  - `__call__`：OCR + 返回 `OCRResult(_merge_lines(...))`

**`backend/open_webui/retrieval/loaders/local_ocr.py`** — `LocalOCRLoader`

对齐 PaddleOCR-vl loader 结构：
- `__init__(file_path)`：存在性校验
- `load()` → `list[Document]`
  - 支持 PDF + 图片（png/jpg/jpeg/bmp/tiff/webp）
  - PDF：`fitz`（PyMuPDF）按页渲染 dpi=200 → 每页独立 Document
  - 图片：直接 OCR → 单个 Document
  - metadata：`processing_engine: 'local-ocr'`、`page`/`page_label`、`file_name`
  - 错误处理对齐 PaddleOCR-vl：异常返回 `Document(page_content=f'Error during OCR processing: {e}', metadata={'error': 'processing_failed', ...})`

### 4.2 修改（append 式）

**`backend/open_webui/retrieval/loaders/main.py`**：

1. import 区追加：`from open_webui.retrieval.loaders.local_ocr import LocalOCRLoader`
2. `_get_loader` elif 链，在 `paddleocr_vl` 分支之后、`else` 之前插入：

```python
elif self.engine == 'local_ocr' and file_ext in ['pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp']:
    loader = LocalOCRLoader(file_path=file_path)
```

文件类型限制使非 PDF/图片文件回落到 `else` 常规 loader，对齐 `mistral_ocr` 的 `and file_ext in ['pdf']` 惯例。

**`src/lib/components/admin/Settings/Documents.svelte`**：

1. option 列表 `<option value="mineru">` 之后追加：

```svelte
<option value="local_ocr">{$i18n.t('Local OCR')}</option>
```

2. `{:else if}` 链尾部追加无需配置的提示块（说明本地 CPU OCR、无外部依赖）。

**i18n**：

- `src/lib/i18n/locales/en-US/translation.json`：`"Local OCR": ""`（对齐惯例，UI key 用英文原词）
- `src/lib/i18n/locales/zh-CN/translation.json`：`"Local OCR": "本地 OCR"`

## 5. 数据流（自查验证）

```
UI 下拉框 → RAGConfig.CONTENT_EXTRACTION_ENGINE
→ POST /api/v1/retrieval/config
→ routers/retrieval.py:857 ConfigForm 接收, :965 写入 config.CONTENT_EXTRACTION_ENGINE
→ utils.py:112 get_loader_config() 从 DB 读 rag.content_extraction_engine ('local_ocr')
→ utils.py:138 Loader(engine='local_ocr', ...)
→ main.py _get_loader elif 链命中 'local_ocr'
→ LocalOCRLoader.load() → list[Document]
```

链路验证点：
- `LOADER_CONFIG_KEYS:74` 已含 `CONTENT_EXTRACTION_ENGINE` → 无需改 utils.py
- engine 值无白名单校验 → 无需改 config.py
- `'local_ocr'` 值不存在时 UI 下拉框回落到 Default（`''`），行为不变

## 6. 错误处理

对齐 PaddleOCR-vl 惯例：`load()` 内 try/except，异常返回带 `error` metadata 的 Document，避免上传任务崩溃。OCR 调用异常包装为 `RuntimeError`。

## 7. 测试策略

本地无 `rapidocr-onnxruntime`，采用分层验证：

| 层 | 方法 | 验证内容 |
|:---|:-----|:---------|
| 单元 | mock `rapidocr_onnxruntime` | `_clean_text` 确定性逻辑（`0. 4`→`0.4` 等）、`_merge_lines` 行合并 |
| 单元 | mock `LocalOCRLoader` | `_get_loader` 对 `'local_ocr'` 正确路由 |
| 集成 | 容器构建后真实扫描 PDF | 13 页扫描 PDF 案例（5 页纯扫描）端到端提取 |

## 8. 不在此设计范围

- auto 回退语义（远程未配置→本地）— 后续 Phase
- deskew、表格结构检测、大 PDF 批处理 — 后续 Phase
- 前端独立配置区 — 无参数引擎不需要
- 上游 PR 提交 — 本地实现验证通过后再决定

## 9. 风险与缓解

| 风险 | 缓解 |
|:-----|:-----|
| merge 上游时 main.py / Documents.svelte 冲突 | 纯 append 修改；3-way merge 大概率自动合并 |
| 首次 OCR 加载慢（ONNX 模型初始化） | 懒加载（`__init__` 延迟 import），不影响服务启动 |
| 扫描件质量差导致识别错误 | CLAHE + 行重建 + 文本清洗（已验证），红线印章重叠为所有 OCR 引擎共性限制 |

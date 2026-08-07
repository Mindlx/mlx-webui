# mlx-webui 发布 SOP — 合并上游 · 制作镜像 · 上传镜像

> **适用仓库**: `~/mlx-webui`（MindLynx Agent，Open WebUI fork）
> **GitHub**: `https://github.com/Mindlx/mlx-webui.git` (origin) / `https://github.com/open-webui/open-webui.git` (upstream)
> **镜像仓库**: 腾讯云 TCR `ccr.ccs.tencentyun.com/mindlx/mlx-webui` + GitHub Container Registry `ghcr.io/mindlx/mlx-webui`
> **上次执行**: 2026-07-07（合并到 v0.10.2，commit `0d7f93b15`）；本 SOP 整合于 2026-07-31

本 SOP 是**一份完整可执行流程**：合并上游更新（保留本地定制）→ 构建多架构镜像 → 推送双仓库 → 验证部署。命令均已实测（2026-07-07 合并 + 2026-07-31 OCR 功能镜像验证）。

---

## 〇、前置概念与约定

### 0.1 仓库结构

| Remote | URL | 用途 |
|:-------|:----|:-----|
| `origin` | `https://github.com/Mindlx/mlx-webui.git` | 本地 fork（推送目标） |
| `upstream` | `https://github.com/open-webui/open-webui.git` | 官方上游（只拉取） |

### 0.2 本地定制三分类（合并策略的核心）

> **⚠️ 重要**：禁止对全部冲突文件无脑 `git checkout --ours`。
> 2026-08-07 实测：上游自 v0.10.2 已推进 618 commits，本地定制文件几乎全被上游持续修改
> （env.py 12次、Documents.svelte 12次、loaders/main.py 6次、翻译 25 commits）。
> `--ours` 全选本地会**永久丢失这些上游的修复/性能/新功能**。

本地定制按保护策略分三类：

| 类别 | 定义 | 文件 | 合并策略 |
|:-----|:-----|:-----|:---------|
| **A. 品牌/文案**（真个性化） | 仅品牌名/文案/favicon | `backend/open_webui/env.py`（仅 WEBUI_NAME 部分）, `src/lib/components/workspace/Tools.svelte`, `src/lib/components/chat/Settings/About.svelte`, `src/lib/components/admin/Settings/General.svelte`, `static/favicon*.png/ico/svg`, `backend/open_webui/static/favicon*.png/ico/svg`, `src/app.html` | **保留本地**，冲突时用 `--ours`（见 1.3） |
| **B. 本地功能**（OCR） | 本地新增的实质功能 | `backend/open_webui/retrieval/loaders/local_ocr.py`, `backend/open_webui/retrieval/loaders/rapidocr/`, `backend/tests/test_local_ocr.py`, `backend/tests/test_rapidocr_clean.py` | **本地新增文件天然保留**；与上游重叠的 `main.py`、`Documents.svelte` 需**先合入上游再增量重放** OCR 代码块（见 1.4） |
| **C. 翻译漂移**（假定制，勿保留） | 上次 `--ours` 造成的外语翻译被英文回退污染 | `src/lib/i18n/locales/*/translation.json`（th-TH/ca-ES/de-DE 等约 40 个） | **采纳上游**（`--theirs`），上游有 25 commits 翻译更新 |

> **为何翻译要采纳上游**：实测 th-TH 等文件的"本地改动"是把泰语/西语/德语翻译清空成英文（英文回退），
> 这是上次 `--ours` 覆盖造成的**数据漂移**，不是有意定制。保留它会锁死上游翻译更新。
> 中文 `zh-CN` 若有主动翻译调整，单独保留（见 1.3）。

> 完整清单查询命令：
> `git diff ecd48e2f718220a6400ecf49eafd4867a38feb10..HEAD --name-only`
> （`ecd48e2f7` 为当前 fork 基线 v0.10.2）

### 0.3 镜像构建参数（Dockerfile）

默认构建（`main` variant，无 CUDA/Ollama）即可，`rapidocr-onnxruntime==1.4.4` 与 `onnxruntime` 已在 `backend/requirements.txt`，**本地 OCR 零额外依赖**。

---

## 一、合并上游更新（保留本地定制）

### 1.1 前置：添加 upstream remote（首次执行）

```bash
cd ~/mlx-webui
git remote add upstream https://github.com/open-webui/open-webui.git   # 如已存在可跳过
git fetch upstream
```

### 1.2 日常合并

```bash
git fetch upstream
git merge upstream/main
```

### 1.3 处理冲突 — 三分类策略

**注意**: 合并时上游在 `MERGE_HEAD`，本地在 `HEAD`。`--ours` 取本地版本，`--theirs` 取上游版本。

```bash
git merge upstream/main

# 查看全部冲突文件
git status | grep "both modified"
```

**按 0.2 分类逐个裁决**：

```bash
# ── A类: 品牌/文案 → 保留本地 (--ours) ──
git checkout --ours backend/open_webui/env.py
git checkout --ours src/lib/components/workspace/Tools.svelte
git checkout --ours src/lib/components/chat/Settings/About.svelte
# favicon 等静态资源若冲突
git checkout --ours static/favicon.png backend/open_webui/static/favicon.png

# ── B类: 本地新增文件 → 天然保留, 无需处理 ──
# local_ocr.py / rapidocr/ / tests 为本地新增, 上游无此文件, merge 自动保留

# ── C类: 翻译 → 采纳上游 (--theirs), 仅保留 zh-CN 本地调整 ──
git checkout --theirs src/lib/i18n/locales/th-TH/translation.json
# ... 对每个漂移翻译文件执行, 或通配(需谨慎):
# git checkout --theirs src/lib/i18n/locales/ca-ES/translation.json
git checkout --ours src/lib/i18n/locales/zh-CN/translation.json   # 中文定制保留

# ── 本地文档(上游可能删除) → --theirs 取回 ──
git checkout --theirs docs/apache.md docs/CONTRIBUTING.md
git add docs/apache.md docs/CONTRIBUTING.md

# ── 中间档: main.py / Documents.svelte → 先取上游, 再重放 OCR (见 1.4) ──
git checkout --theirs backend/open_webui/retrieval/loaders/main.py
git checkout --theirs src/lib/components/admin/Settings/Documents.svelte

# 标记全部冲突已解决
git add .
```

**裁决规则**：
- **A类品牌/文案** → `--ours` 保留本地
- **C类翻译** → `--theirs` 采纳上游（本地是污染），`zh-CN` 例外
- **B类本地新增文件** → 无冲突自动保留
- **中间档（本地功能与上游重叠）** → `--theirs` 取上游后**增量重放**本地代码块
- **无法简单裁决**（本地与上游改动重叠较深）→ 参考 `fork_merge_methodology.md` FE² 框架人工评估

### 1.4 OCR 本地功能增量重放

合并后 `main.py` 和 `Documents.svelte` 已被上游版本覆盖，需重放本地 OCR 代码块：

```bash
# 查看本地 OCR 分支应加在哪（上游新版 main.py 的 elif 链）
grep -n "paddleocr_vl\|elif self.engine" backend/open_webui/retrieval/loaders/main.py

# 1) main.py: 加 import + elif 分支（对齐上游新结构, 可能已改行号）
#    import:  from open_webui.retrieval.loaders.local_ocr import LocalOCRLoader
#    elif:    self.engine == 'local_ocr' and file_ext in ['pdf','png','jpg','jpeg','bmp','tiff','webp']

# 2) Documents.svelte: 加 <option value="local_ocr"> + {:else if} 提示块

# 3) 回归验证
python3 -m pytest backend/tests/ -q
```

> 参考实现：`git show 0699cdd77 -- backend/open_webui/retrieval/loaders/main.py` 和
> `git show 0f65ec49f -- src/lib/components/admin/Settings/Documents.svelte`（本地 OCR 接入提交）。

### 1.5 同步官方版本号（可选，不同步其他代码）

```bash
git show upstream/main:package.json | grep '"version"'
git checkout upstream/main -- package.json package-lock.json pyproject.toml
git add .
git commit -m "同步官方版本号到 x.x.x"
```

> 若不想覆盖整个文件，可只手动编辑三处 `"version"` 字段数字。

### 1.6 合并后验证

```bash
git status   # 应显示 "nothing to commit, working tree clean"
git log --oneline -5
python3 -m pytest backend/tests/ -q   # 本地 OCR 单测回归
```

---

## 二、制作镜像（Buildx 多架构构建）

### 2.1 环境准备（首次执行）

```bash
# 1. 安装 QEMU（跨架构模拟）
sudo apt install -y qemu-user-static
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

# 2. 创建 buildx 构建器（支持 linux/arm64）
docker buildx rm mybuilder-tencent 2>/dev/null
docker buildx create --use --name=mybuilder-tencent --driver docker-container
docker buildx inspect --bootstrap   # 应包含 linux/arm64
```

### 2.2 登录镜像仓库

```bash
# 腾讯云 TCR
docker login ccr.ccs.tencentyun.com --username=100021303469
# GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u Mindlx --password-stdin
```

> `GITHUB_TOKEN` 存在 `~/.secrets`（grep GITHUB_TOKEN ~/.secrets）。腾讯云 TCR 密码为控制台生成的访问凭据（docker login 交互式输入）。

### 2.3 执行构建并推送（推荐 screen 防 SSH 断开）

```bash
# 用 screen 保持会话
sudo apt install screen -y
screen -S buildx

cd ~/mlx-webui
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --cache-from mlx-webui:latest \
  --build-arg HF_TOKEN=$HF_TOKEN \
  -t ccr.ccs.tencentyun.com/mindlx/mlx-webui:latest \
  -t ghcr.io/mindlx/mlx-webui:latest \
  --push \
  .

# 脱离会话（Ctrl+A 然后 D），可安全退出 SSH
# 重连：screen -r buildx
```

**构建参数说明**：
- `--platform linux/amd64,linux/arm64` — 双架构推送
- `--cache-from mlx-webui:latest` — 复用本地缓存，加速 ARM64
- `-t` 两个标签 — 同时推送腾讯云 + GitHub
- `--build-arg HF_TOKEN=$HF_TOKEN` — 构建期需下载 HuggingFace 模型时使用（`export HF_TOKEN="hf_..."` 或写入 `~/.bashrc`）

**强制刷新缓存重建**（代码改动后想绕过旧缓存）：

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --build-arg CACHE_BUST=$(date +%s) \
  -t ccr.ccs.tencentyun.com/mindlx/mlx-webui:latest \
  -t ghcr.io/mindlx/mlx-webui:latest \
  --push \
  .
```

### 2.4 构建器清理

```bash
docker buildx stop mybuilder-tencent
docker buildx rm mybuilder-tencent
docker builder prune -a
```

---

## 三、验证与部署

### 3.1 检查远端镜像

```bash
docker manifest inspect ccr.ccs.tencentyun.com/mindlx/mlx-webui:latest
docker manifest inspect ghcr.io/mindlx/mlx-webui:latest
# 构建日志（如异常）：
docker logs -f buildx_buildkit_mybuilder-tencent0
```

### 3.2 本地运行验证

```bash
# 拉取新镜像
docker pull ccr.ccs.tencentyun.com/mindlx/mlx-webui:latest

# 停止并替换旧容器（保留数据卷）
docker stop mindlx && docker rm mindlx
docker run -d \
  --add-host=host.docker.internal:host-gateway \
  --name mindlx \
  --restart always \
  -p 3001:8080 \
  -v "${HOME}/mindlx/data:/app/backend/data" \
  -v "${HOME}/mindlx/static:/app/backend/open_webui/static" \
  -e HF_ENDPOINT=https://hf-mirror.com \
  ccr.ccs.tencentyun.com/mindlx/mlx-webui:latest

# 访问 http://localhost:3001 验证
```

> 数据卷说明：`${HOME}/mindlx/data` 持久化后端数据（`analyses/backtest/LLM` 等），`${HOME}/mindlx/static` 为静态资源覆盖目录。首次启动如需拷贝镜像初始内容，参考 `/opt/ai-workspace/docs/mindlx+docker.md`。

### 3.3 验证本地 OCR 功能（新功能冒烟）

在 WebUI 设置 → 文档中，将内容提取引擎选为 **Local OCR**，上传一张含文字的图片/PDF，确认文本被正确提取（无外部 API 调用，纯本地 CPU 处理）。

---

## 四、故障排查

| 问题 | 原因 | 处理 |
|:-----|:-----|:-----|
| `docker login` 失败 | 腾讯云访问凭据过期/未生成 | 腾讯云控制台 → TCR → 访问凭据 → 重新生成 |
| 推送 403 | 未登录对应仓库 | 重新执行 2.2 登录 |
| ARM64 构建很慢 | QEMU 模拟 | 确认已安装 qemu-user-static + 注册 binfmt |
| buildx builder 报错 | 构建器损坏 | `docker buildx rm mybuilder-tencent` 后重建 |
| 镜像缺 OCR 依赖 | 构建时 requirements 未包含 | 检查 `backend/requirements.txt` 含 `rapidocr-onnxruntime` |
| 合并后 OCR 功能丢失 | main.py/Documents.svelte 取上游后未重放 | 按 1.4 增量重放本地 OCR 代码块 |

---

## 五、参考

- 合并方法论（通用，含 FE² 评估框架）: `/opt/notes/fork_merge_methodology.md`
- 自动审计工具: `~/.agents/skills/fork-merge-audit/fork_merge_audit.py`（或 `/opt/notes/fork_merge_audit.py`）
- 历史命令笔记: `/opt/ai-workspace/docs/mindlx-docker-buildx.md`, `/opt/ai-workspace/docs/mindlx+docker.md`
- 上游状态: 当前 fork 点 `ecd48e2f7`（v0.10.2），上游已推进 618 commits（2026-08-07 审计）

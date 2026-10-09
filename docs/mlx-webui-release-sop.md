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
| **A. 品牌/文案**（真个性化） | 仅品牌名/文案/favicon | `backend/open_webui/env.py`（仅 WEBUI_NAME 部分）, `src/lib/constants.ts`（仅 APP_NAME 部分）, `static/favicon*.png/ico/svg`, `backend/open_webui/static/favicon*.png/ico/svg`, `site.webmanifest`, `static/opensearch.xml`, README | **采纳上游 + 重放品牌**（⚠️ v0.11.4 起上游 i18n 化，不可无脑 `--ours`，见 **1.7**） |
| **B. 本地功能**（OCR） | 本地新增的实质功能 | `backend/open_webui/retrieval/loaders/local_ocr.py`, `backend/open_webui/retrieval/loaders/rapidocr/`, `backend/open_webui/utils/model_seed.py`, `backend/tests/test_local_ocr.py`, `backend/tests/test_rapidocr_clean.py`, `test/test_model_seed.py` | **本地新增文件天然保留**；与上游重叠的 `main.py`、`Documents.svelte` 需**先合入上游再增量重放** OCR 代码块（见 1.4） |
| **C. 翻译漂移**（假定制，勿保留） | 上次 `--ours` 造成的外语翻译被英文回退污染 | `src/lib/i18n/locales/*/translation.json` | **采纳上游**（`--theirs`）+ 重放本地新增 i18n key（如 `Local OCR`，见 1.4/1.7） |

> **为何翻译要采纳上游**：实测 th-TH 等文件的"本地改动"是把泰语/西语/德语翻译清空成英文（英文回退），
> 这是上次 `--ours` 覆盖造成的**数据漂移**，不是有意定制。保留它会锁死上游翻译更新。

> 完整清单查询命令（基线随版本更新）：
> `git diff <上次合并的上游 commit>..HEAD --name-only`
> （2026-10-09 已合并至 v0.11.4，上游 `8bd8b4fac`）

### 0.3 镜像构建参数（Dockerfile）

默认构建（`main` variant，无 CUDA/Ollama）即可，`rapidocr-onnxruntime==1.4.4` 与 `onnxruntime` 已在 `backend/requirements.txt`，**本地 OCR 零额外依赖**。

本地 Dockerfile 定制（相对上游）:
- `ARG USE_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5`（中文默认嵌入模型）
- `ENV RAG_EMBEDDING_MODEL_AUTO_UPDATE=false` + `HF_HUB_DISABLE_XET=1`
- `ENV NODE_OPTIONS="--max-old-space-size=8192"`（**必需**：v0.11.4 前端变大，默认 node 堆内存 OOM；上游注释掉了此项）
- staging 拷贝行：`cp -a "$SENTENCE_TRANSFORMERS_HOME"/. /opt/open-webui/embedding_models/`（配合启动播种，见 1.7）

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
# ── A类: 品牌 → 采纳上游 + 重放品牌 (⚠️ 勿无脑 --ours，见 1.7) ──
git checkout --theirs backend/open_webui/env.py                # 然后改 WEBUI_NAME='MindLynx Agent'
git checkout --theirs src/lib/constants.ts                     # 然后改 APP_NAME='MindLynx Agent'
# 其余品牌 svelte / favicon 静态资源：直接取上游（品牌由 APP_NAME 驱动）或用 --ours 保留图标
git checkout --ours static/favicon.png backend/open_webui/static/favicon.png

# ── B类: 本地新增文件 → 天然保留, 无需处理 ──
# local_ocr.py / rapidocr/ / model_seed.py / tests 为本地新增, 上游无此文件, merge 自动保留

# ── C类: 翻译 → 采纳上游 (--theirs)，再重放本地新增 i18n key ──
git checkout --theirs src/lib/i18n/locales/*/translation.json
# 重放本地 OCR 的 i18n key(见 1.4): 'Local OCR' 等, 写入 en-US + zh-CN

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

### 1.7 品牌文件处理教训（v0.11.4 起，重要）

上游从 v0.11.4 起**大规模 i18n 化 + 结构调整**，对品牌文件的合并策略必须修正：

- **不要对品牌文件无脑 `--ours`**：本地品牌版本基于旧上游，会丢失上游本次新增的 **export / import / 组件结构**。
  实证：`src/lib/constants.ts` 用 `--ours` 丢了上游新增的 `COMMUNITY_ORIGINS` export，导致 `+layout.svelte` import 失败、前端构建整体崩溃。
- **正确做法 = 采纳上游 + 重放品牌**：
  - `backend/open_webui/env.py` → 取上游，仅改 `WEBUI_NAME = os.getenv('WEBUI_NAME', 'MindLynx Agent')`
  - `src/lib/constants.ts` → 取上游，仅改 `export const APP_NAME = 'MindLynx Agent';`
  - 其余品牌 svelte（About/General/Audio/…）→ **取上游版本**（上游已 i18n 化，品牌由 `APP_NAME` 统一驱动）
- **品牌真正承重的位置**（改这几处即可）：`constants.ts::APP_NAME`、`env.py::WEBUI_NAME`、
  `backend/open_webui/static/site.webmanifest`、favicon/logo 静态资源、`static/opensearch.xml`、README。
- **本地新增文件**（`local_ocr.py`、`rapidocr/`、`model_seed.py`、`Documents.svelte` 的 OCR 块）→ 天然保留或增量重放。

**合并后必做前端预验证**（比全量 Docker 构建快）:
```bash
npm ci --force                                  # 同步上游新依赖（否则本机 build 报缺包）
NODE_OPTIONS="--max-old-space-size=8192" npm run build   # 应 exit 0；失败先修再进 Docker 构建
git checkout HEAD~1 -- static/pyodide/pyodide-lock.json  # 丢弃 build 副作用（black 版本漂移）
```

### 1.8 本地启动播种机制（bind-mount 修复）

镜像在 `/opt/open-webui/embedding_models`（挂载区外）保留一份模型 staging，启动时
`seed_bundled_embeddings()`（`backend/open_webui/utils/model_seed.py`，lifespan 调用）把缺失的
`models--*` 快照拷入 `SENTENCE_TRANSFORMERS_HOME`，解决 bind mount（`-v HOST:/app/backend/data`）
掩盖内置模型的问题。合并时确保 `main.py` 的 import + 调用、`Dockerfile` 的 staging 拷贝行都在。

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
| 前端构建 `npm run build` 失败 `Aborted`/`SIGABRT` | node 堆内存不足（版本越大越明显） | Dockerfile 启用 `ENV NODE_OPTIONS="--max-old-space-size=8192"`（见 0.3） |
| 前端构建 `"X" is not exported by "constants.ts"` | 对品牌文件用 `--ours` 丢失了上游新增的 export | 改为**采纳上游 + 重放品牌**（如 constants.ts 需含上游 `COMMUNITY_ORIGINS`），见 1.7 |
| svelte 组件 import 与上游不匹配 | 部分 `--ours` 保留旧结构，与上游其他文件不兼容 | 该文件采纳上游版本（品牌由 APP_NAME/WEBUI_NAME 统一保证），见 1.7 |
| 构建残留 `static/pyodide/pyodide-lock.json` 改动 | 本机 `npm run build` 的 pyodide:fetch 副作用（black 版本漂移） | `git checkout HEAD~1 -- static/pyodide/pyodide-lock.json` 后 amend |

---

## 五、参考

- 合并方法论（通用，含 FE² 评估框架）: `/opt/notes/fork_merge_methodology.md`
- 自动审计工具: `~/.agents/skills/fork-merge-audit/fork_merge_audit.py`（或 `/opt/notes/fork_merge_audit.py`）
- 历史命令笔记: `/opt/ai-workspace/docs/mindlx-docker-buildx.md`, `/opt/ai-workspace/docs/mindlx+docker.md`
- 上游状态（2026-10-09 更新）: 已合并至 **v0.11.4**（上游 `8bd8b4fac`，自 v0.11.0 推进 898 commits）。merge commit `d2438de10`，构建修复 `fb7be4c77`，镜像 `:0.11.4` manifest `adafbad8`。

---

## 六、上游贡献（Issue/PR）留痕记录

> 本节记录向上游 open-webui 提交 issue / PR 的历史与结论，避免重复论证、确认格式。

### 6.1 提交格式核对（2026-08-25 验证）

向上游 open-webui 提 **PR** 的硬性要求（不满足会被 bot 自动关闭）:

| 要求 | 正确格式 |
|:-----|:---------|
| Target 分支 | 必须指向 `dev`（指向 `main` 会被 `owui-terminator[bot]` 立即关闭） |
| 关联 issue/discussion | PR body 必须含 `Relates to #xxx` 链接 |
| CLA 确认文本 | PR body 必须含 CLA checkbox 确认句（删除会被 CLA-Bot 作废） |
| 标题前缀 | `fix:` / `feat:` / `chore:` 等 |

**GitHub API 创建 PR 的 head 格式**：`head: "Mindlx:fix/<branch>"`（owner:branch，fork 名可为任意名，只要 owner 是 fork 属主）。

### 6.2 提交历史

| 日期 | 类型 | 内容 | 状态 |
|:-----|:-----|:-----|:-----|
| 2026-08-17 | PR #28682 | Ollama/OpenAI 嵌入空 Bearer 修复（target main） | 被 bot 关闭（应 target dev） |
| 2026-08-17 | Issue #28683 | 同 bug 的 issue 报告 | open |
| 2026-08-17 | PR #28684 | 同上修复（target dev + 关联 issue + CLA） | 被维护者 tjbck 关闭："Addressed in dev"（上游已自行采纳） |
| 2026-08-25 | Issue #29014 | bind-mount 掩盖内置嵌入模型 | open |
| 2026-08-25 | PR（seed-bundled-embeddings） | 播种内置模型修复 | **创建被拒**（见 6.3） |

### 6.3 上游 PR 管控发现（2026-08-25）

- 现象：创建 PR 到 open-webui 时，REST 返回 `404 Not Found`，`gh pr create` 返回
  `GraphQL: Mindlx does not have the correct permissions to execute CreatePullRequest`。
- 排查排除的因素：token 有效（能读 API、能创建 issue）、fork 关系正确
  （parent=open-webui/open-webui）、head 格式正确（`Mindlx:fix/<branch>` 与上次成功的
  #28684 完全一致）、分支已推送且 fork API 可见。
- 根因：**上游维护者 tjbck 正在关闭所有外部 fork PR**（实测 2026-08-24 后创建的
  #29005-29010 全部被 tjbck 静默关闭，无评论）。非提交格式问题，是上游当前的
  PR 接收策略（可能处于发布 freeze / 集中处理窗口）。
- 结论：**暂缓向 open-webui 提 PR**，等上游恢复正常接收 PR 再提交。本地功能
  （嵌入认证修复、播种模型修复、中文默认模型）已全部在 fork 的 main 分支实现，
  不影响使用。修复代码保留在本地分支：
  `fix/seed-bundled-embeddings`（基于 upstream/dev）。
- 应对：若上游长期不接收，可在 issue 评论区推进，或等上游下一版发布后核对
  "Addressed in dev" 是否已覆盖我们的修复（防止重复实现）。

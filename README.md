# MindLynx Agent 🚀

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/Mindlx/mlx-webui?style=social&label=⭐ Star)
![GitHub forks](https://img.shields.io/github/forks/Mindlx/mlx-webui?style=social&label=🍴 Fork)
![GitHub watchers](https://img.shields.io/github/watchers/Mindlx/mlx-webui?style=social&label=👁 Watch)
![GitHub repo size](https://img.shields.io/github/repo-size/Mindlx/mlx-webui?style=flat&color=blue)
![GitHub language count](https://img.shields.io/github/languages/count/Mindlx/mlx-webui?style=flat)
![GitHub top language](https://img.shields.io/github/languages/top/Mindlx/mlx-webui?style=flat)
![GitHub last commit](https://img.shields.io/github/last-commit/Mindlx/mlx-webui?style=flat&color=red)
![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg?style=flat)
![GitHub issues](https://img.shields.io/github/issues/Mindlx/mlx-webui?style=flat&color=orange)
![GitHub pull requests](https://img.shields.io/github/issues-pr/Mindlx/mlx-webui?style=flat&color=green)

[![Discord](https://img.shields.io/badge/Discord-MindLynx_Agent-blue?logo=discord&logoColor=white&style=flat)](https://discord.gg/5rJgQTnV4s)
[![GitHub](https://img.shields.io/badge/GitHub-MindLynx_Agent-blue?logo=github&logoColor=white&style=flat)](https://github.com/Mindlx/mlx-webui)

</div>

<div align="center">

![MindLynx Agent Banner](./banner.png)

</div>

---

## 📖 项目简介

**MindLynx Agent** 是一个可扩展、功能丰富且用户友好的**离线 AI 平台**，专为中文用户深度定制。它支持多种 LLM 推理引擎，内置强大的 RAG 检索增强功能，是企业级 AI 部署的理想选择。

> [!IMPORTANT]
> 本项目基于 [Open WebUI](https://github.com/open-webui/open-webui) 开源项目深度定制，针对中文用户体验进行了全面优化。

---

## ✨ 核心特性

### 🚀 开箱即用
- **一键部署**：支持 Docker 和 Kubernetes，5 分钟快速启动
- **离线运行**：无需联网，数据完全本地化，保障隐私安全
- **自动构建**：首次运行自动构建镜像，零配置上手

### 🤝 多模型兼容
- **Ollama**：原生支持，本地模型推理
- **OpenAI API**：兼容所有 OpenAI 格式 API
- **GroqCloud**：高速推理云服务集成
- **Mistral**：支持 Mistral 系列模型
- **OpenRouter**：多模型路由聚合
- **自定义 API**：支持任意 OpenAI 兼容接口

### 🛡️ 精细权限管理
- **用户组**：灵活的用户分组管理
- **角色权限**：细粒度的 RBAC 权限控制
- **API 密钥**：支持多密钥管理
- **数据隔离**：用户数据完全隔离

### 📚 本地 RAG 检索增强
- **向量数据库**：支持多种向量存储引擎
- **文档解析**：PDF、Word、Markdown 等多种格式
- **知识库管理**：可视化知识库创建与管理
- **智能检索**：优化的语义搜索算法

### 🔍 联网搜索
- **15+ 搜索引擎**：集成 Google、Bing、DuckDuckGo 等
- **实时搜索**：支持实时网络信息获取
- **自定义源**：支持添加自定义搜索引擎

### 🎨 图像生成
- **DALL-E**：AI 图像生成
- **ComfyUI**：工作流式图像生成
- **AUTOMATIC1111**：Stable Diffusion 支持
- **多种模型**：支持 SDXL、SD1.5 等

### 🌐 多语言支持
- **60+ 种语言**：内置多语言界面
- **中文优化**：针对中文用户深度定制
- **国际化**：支持多语言切换

### 🧩 插件扩展
- **自定义函数**：支持自定义工具调用
- **API 集成**：可调用外部 API
- **插件市场**：丰富的插件生态

### 📱 响应式设计
- **全平台支持**：PC、平板、手机完美适配
- **暗黑模式**：内置主题切换
- **流畅体验**：优化的前端性能

---

## 🎯 适用场景

| 场景 | 说明 |
|------|------|
| 🏢 **企业知识库** | 构建企业内部知识问答系统 |
| 📝 **文档助手** | 辅助编写和审查技术文档 |
| 💼 **客服系统** | 智能客服和 FAQ 问答 |
| 🎓 **教育辅助** | 学习助手和作业辅导 |
| 🔬 **数据分析** | 数据分析和报告生成 |
| 🎨 **创意辅助** | 图像生成和内容创作 |
| 📊 **代码助手** | 代码生成和调试辅助 |

---

## 🚀 快速开始

### 方式一：使用 Docker Compose（推荐）⭐

```bash
# 克隆仓库
git clone https://github.com/Mindlx/mlx-webui.git
cd mlx-webui

# 启动服务（首次运行会自动构建镜像）
docker compose up -d

# 查看日志
docker compose logs -f

# 访问应用
# 启动后访问 http://localhost:3026
```

### 方式二：使用 Docker 命令

```bash
# 从源码构建镜像
git clone https://github.com/Mindlx/mlx-webui.git
cd mlx-webui
docker build -t mindlx-webui:latest .

# 运行容器
docker run -d -p 3026:8080 \
  -v mindlx-webui:/app/backend/data \
  --add-host=host.docker.internal:host-gateway \
  --name mindlx-webui \
  --restart always \
  mindlx-webui:latest
```

### 方式三：使用 pip 安装

```bash
# 克隆仓库后本地安装
git clone https://github.com/Mindlx/mlx-webui.git
cd mlx-webui
pip install -e .

# 启动服务
open-webui serve
```

---

## 📦 环境变量配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `MINDLX_WEBUI_PORT` | `3026` | Web 服务端口 |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama 服务地址 |
| `WEBUI_SECRET_KEY` | `(随机生成)` | 会话加密密钥 |
| `DATABASE_URL` | `sqlite:////app/backend/data/data.db` | 数据库连接 |
| `REDIS_URL` | `redis://redis:6379` | Redis 连接（可选） |
| `ENABLE_OPENAI_API` | `true` | 是否启用 OpenAI API |
| `ENABLE_GROQ_API` | `false` | 是否启用 Groq API |

---

## 🗂️ 项目结构

```
mlx-webui/
├── backend/              # 后端 Python 代码
│   ├── open_webui/      # 核心业务逻辑
│   ├── internal/        # 内部模块
│   └── migrations/      # 数据库迁移脚本
├── src/                  # 前端 Svelte 代码
│   ├── lib/             # 核心库
│   ├── components/      # 组件
│   └── stores/          # 状态管理
├── static/               # 静态资源（图标、图片等）
├── docker-compose.yaml   # Docker Compose 配置
├── Dockerfile            # Docker 镜像构建文件
└── README.md             # 项目说明
```

---

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 贡献流程

1. **Fork** 本仓库
2. **创建** 特性分支 (`git checkout -b feature/amazing`)
3. **提交** 修改 (`git commit -m 'Add some amazing feature'`)
4. **推送** 到分支 (`git push origin feature/amazing`)
5. **打开** Pull Request

### 代码规范

- 遵循 PEP 8 Python 风格指南
- 使用 TypeScript 进行前端开发
- 提交信息清晰明确

---

## 🐛 问题反馈

### 提交 Issue

- 发现 Bug？请提交 Issue
- 功能建议？欢迎提出 PR
- 使用问题？查看常见问题 FAQ

### 讨论交流

- **Discord 社区**：[加入 Discord](https://discord.gg/5rJgQTnV4s)
- **GitHub Discussions**：[讨论区](https://github.com/Mindlx/mlx-webui/discussions)

---

## 📄 许可证

本项目基于 **Apache 2.0** 许可证开源，详见 [LICENSE](LICENSE) 文件。

### 开源依赖

- [Open WebUI](https://github.com/open-webui/open-webui) - 核心基础项目
- [Ollama](https://github.com/ollama/ollama) - 本地模型推理
- [Svelte](https://svelte.dev/) - 前端框架
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架

---

## 🙏 致谢

- ❤️ 感谢 **Open WebUI** 团队提供的优秀基础项目
- 🌟 感谢所有 **贡献者** 的支持与贡献
- 📖 感谢所有 **用户** 的反馈与建议

---

## 📊 项目统计

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/Mindlx/mlx-webui?style=flat-square&label=⭐&color=gold)
![GitHub forks](https://img.shields.io/github/forks/Mindlx/mlx-webui?style=flat-square&label=🍴&color=blue)
![GitHub watchers](https://img.shields.io/github/watchers/Mindlx/mlx-webui?style=flat-square&label=👁&color=green)
![GitHub repo size](https://img.shields.io/github/repo-size/Mindlx/mlx-webui?style=flat-square&color=blue)

</div>

---

## 🌟 Star History

<div align="center">

![Star History Chart](https://api.star-history.com/svg?repos=Mindlx/mlx-webui&type=Date)

</div>

---

<div align="center">

如果这个项目对你有帮助，请给个 **Star ⭐** 支持一下！
你的支持是我们持续优化的动力！

</div>

---

<div align="center">

Made with ❤️ by Mindlx

</div>

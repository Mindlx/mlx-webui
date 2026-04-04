# MindLynx Agent 🚀

![GitHub stars](https://img.shields.io/github/stars/Mindlx/mlx-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/Mindlx/mlx-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/Mindlx/mlx-webui?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/Mindlx/mlx-webui)
![GitHub language count](https://img.shields.io/github/languages/count/Mindlx/mlx-webui)
![GitHub top language](https://img.shields.io/github/languages/top/Mindlx/mlx-webui)
![GitHub last commit](https://img.shields.io/github/last-commit/Mindlx/mlx-webui?color=red)
[![Discord](https://img.shields.io/badge/Discord-MindLynx_Agent-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)

![MindLynx Agent Banner](./banner.png)

**MindLynx Agent is an extensible, feature-rich, and user-friendly self-hosted AI platform designed to operate entirely offline.** It supports various LLM runners like **Ollama** and **OpenAI-compatible APIs**, with **built-in inference engine** for RAG, making it a **powerful AI deployment solution**.

> [!NOTE]
> 本项目是基于 [Open WebUI](https://github.com/open-webui/open-webui) 的品牌化定制版本，针对中文用户体验进行了优化。

## ✨ 主要特性

- 🚀 **一键部署**：支持 Docker 和 Kubernetes，开箱即用
- 🤝 **多模型支持**：兼容 Ollama、OpenAI API、GroqCloud、Mistral、OpenRouter 等
- 🛡️ **精细权限管理**：支持用户组、角色权限控制
- 📚 **本地 RAG 检索增强**：支持多种向量数据库和文档解析引擎
- 🔍 **联网搜索**：集成 15+ 搜索引擎
- 🎨 **图像生成**：支持 DALL-E、ComfyUI、AUTOMATIC1111
- 🌐 **多语言支持**：内置 60+ 种语言界面
- 🧩 **插件扩展**：支持自定义函数和工具调用
- 📱 **响应式设计**：支持 PC、平板、手机访问

## 🚀 快速开始

### 使用 Docker Compose（推荐）

```bash
# 克隆仓库
git clone https://github.com/Mindlx/mlx-webui.git
cd mlx-webui

# 启动服务（首次运行会自动构建镜像）
docker compose up -d

# 查看日志
docker compose logs -f

启动后访问 http://localhost:3026
使用 Docker 命令
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

### 使用 pip 安装
```bash
# 克隆仓库后本地安装
git clone https://github.com/Mindlx/mlx-webui.git
cd mlx-webui
pip install -e .
open-webui serve
```

### 📦 环境变量
变量	默认值	说明
MINDLX_WEBUI_PORT	3026	Web 服务端口
OLLAMA_BASE_URL	http://ollama:11434	Ollama 服务地址
WEBUI_SECRET_KEY	(随机生成)	会话加密密钥

### 🗂️ 项目结构
mlx-webui/
├── backend/          # 后端 Python 代码
├── src/              # 前端 Svelte 代码
├── static/           # 静态资源（图标、图片等）
├── docker-compose.yaml  # Docker Compose 配置
├── Dockerfile        # Docker 镜像构建文件
└── README.md         # 项目说明

### 🤝 贡献指南
欢迎提交 Issue 和 Pull Request！
1. Fork 本仓库
2. 创建你的特性分支 (git checkout -b feature/amazing)
3. 提交你的修改 (git commit -m 'Add some amazing feature')
4. 推送到分支 (git push origin feature/amazing)
5. 打开 Pull Request

### 📄 许可证
本项目基于 Apache 2.0 许可证开源，详见 LICENSE 文件。

### 🙏 致谢
- 感谢 Open WebUI 团队提供的优秀基础项目
-  感谢所有贡献者的支持

### 📞 联系方式
- 问题反馈：GitHub Issues
- 讨论交流：Discord 社区
---
如果这个项目对你有帮助，请给个 Star ⭐ 支持一下！

# CC-SOP Monitor 部署指南

> 客舱乘务员姿态与操作规范监测系统 - Windows 完整部署指南

---

## 目录

1. [硬件要求](#1-硬件要求)
2. [WSL2 安装与配置](#2-wsl2-安装与配置)
3. [Miniconda 安装与配置](#3-miniconda-安装与配置)
4. [项目部署](#4-项目部署)
5. [后端环境配置](#5-后端环境配置)
6. [前端环境配置](#6-前端环境配置)
7. [启动服务](#7-启动服务)
8. [常见问题](#8-常见问题)

---

## 1. 硬件要求

### 最低配置

| 项目 | 要求 |
|-----|------|
| CPU | Intel i5 第8代 / AMD Ryzen 5 3000系列 或更高 |
| 内存 | 16 GB |
| 硬盘 | 50 GB 可用空间（SSD 推荐）|
| 显卡 | 集成显卡可运行（仅CPU推理）|
| 摄像头 | USB 摄像头 或 RTSP 网络摄像头 |
| 麦克风 | 任意音频输入设备 |
| 操作系统 | Windows 10 版本 2004+ / Windows 11 |

### 推荐配置

| 项目 | 要求 |
|-----|------|
| CPU | Intel i7 第10代+ / AMD Ryzen 7 5000+ |
| 内存 | 32 GB |
| 硬盘 | 100 GB SSD（NVMe 推荐）|
| 显卡 | NVIDIA RTX 3060+ (用于GPU加速推理) |
| 摄像头 | 1080P 30fps 以上 |
| 网络 | 稳定互联网连接（用于语音识别和AI分析API）|

### GPU 加速说明

- **无独立显卡**：系统使用 CPU 进行 MediaPipe 姿态检测，性能足够日常使用
- **有 NVIDIA 显卡**：可安装 CUDA 版本 PyTorch 获得更好性能
- **CUDA 版本要求**：CUDA 11.8 或 12.1

---

## 2. WSL2 安装与配置

### 2.1 启用 WSL2

以**管理员身份**打开 PowerShell，执行：

```powershell
# 启用 WSL 功能
wsl --install

# 重启电脑后，设置默认版本为 WSL2
wsl --set-default-version 2
```

### 2.2 安装 Ubuntu

```powershell
# 安装 Ubuntu 22.04 LTS
wsl --install -d Ubuntu-22.04

# 或者从 Microsoft Store 安装
```

安装完成后，设置用户名和密码。

### 2.3 配置 WSL2 资源

创建或编辑 `C:\Users\<用户名>\.wslconfig`：

```ini
[wsl2]
memory=8GB
processors=4
swap=4GB
localhostForwarding=true

[experimental]
autoMemoryReclaim=gradual
```

重启 WSL 使配置生效：

```powershell
wsl --shutdown
wsl
```

### 2.4 更换 APT 镜像源（加速下载）

进入 WSL Ubuntu 终端：

```bash
# 备份原文件
sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak

# 使用清华镜像源
sudo tee /etc/apt/sources.list << 'EOF'
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-backports main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-security main restricted universe multiverse
EOF

# 更新软件包列表
sudo apt update && sudo apt upgrade -y
```

### 2.5 安装基础依赖

```bash
sudo apt install -y \
    build-essential \
    git \
    curl \
    wget \
    vim \
    htop \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libportaudio2 \
    portaudio19-dev \
    ffmpeg
```

---

## 3. Miniconda 安装与配置

### 3.1 下载并安装 Miniconda

```bash
# 下载 Miniconda 安装脚本
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh

# 安装（按提示操作，建议安装到默认路径）
bash ~/miniconda.sh -b -p $HOME/miniconda3

# 初始化 conda
~/miniconda3/bin/conda init bash

# 重新加载 shell
source ~/.bashrc
```

### 3.2 配置 Conda 镜像源

```bash
# 配置清华镜像源
cat > ~/.condarc << 'EOF'
channels:
  - defaults
show_channel_urls: true
default_channels:
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/msys2
custom_channels:
  conda-forge: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
  pytorch: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
EOF

# 清理缓存
conda clean -i
```

### 3.3 配置 pip 镜像源

```bash
# 创建 pip 配置目录
mkdir -p ~/.pip

# 配置阿里云镜像源
cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
trusted-host = mirrors.aliyun.com
EOF
```

### 3.4 创建项目环境

```bash
# 创建 Python 3.10 环境
conda create -n cc-sop python=3.10 -y

# 激活环境
conda activate cc-sop

# 验证 Python 版本
python --version  # 应显示 Python 3.10.x
```

---

## 4. 项目部署

### 4.1 克隆项目代码

```bash
# 创建项目目录
mkdir -p ~/Project
cd ~/Project

# 克隆代码（替换为实际仓库地址）
git clone <repository-url> AI-Monitor-CSA

# 或者从本地复制
# 在 Windows 中，WSL 可以访问 Windows 文件系统
# 路径映射: C:\ -> /mnt/c/
cp -r /mnt/c/Users/<用户名>/Desktop/AI-Monitor-CSA ~/Project/
```

### 4.2 项目结构

```
AI-Monitor-CSA/
├── backend/                 # 后端服务
│   ├── src/                 # 源代码
│   ├── config/              # 配置文件
│   ├── data/                # 数据文件
│   ├── requirements.txt     # Python 依赖
│   └── .env                 # 环境变量
├── frontend/                # 前端应用
│   ├── src/                 # 源代码
│   ├── package.json         # Node.js 依赖
│   └── vite.config.ts       # Vite 配置
├── CLAUDE.md                # 项目说明
└── DEPLOYMENT.md            # 本部署文档
```

---

## 5. 后端环境配置

### 5.1 安装 Python 依赖

```bash
# 确保激活 conda 环境
conda activate cc-sop

# 进入后端目录
cd ~/Project/AI-Monitor-CSA/backend

# 安装依赖
pip install -r requirements.txt
```

### 5.2 PyTorch GPU 版本（可选）

如果有 NVIDIA 显卡并希望使用 GPU 加速：

```bash
# 卸载 CPU 版本
pip uninstall torch torchvision torchaudio -y

# 安装 CUDA 11.8 版本
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 或 CUDA 12.1 版本
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 验证 GPU 是否可用
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### 5.3 配置环境变量

创建或编辑 `backend/.env` 文件：

```bash
cd ~/Project/AI-Monitor-CSA/backend

cat > .env << 'EOF'
# CC-SOP Monitor Backend Environment Variables

# ========== 语音识别 API (火山引擎/豆包) ==========
# 申请地址: https://console.volcengine.com/speech/app
DOUBAO_APP_ID=<your-app-id>
DOUBAO_ACCESS_TOKEN=<your-access-token>
DOUBAO_SECRET_KEY=<your-secret-key>
DOUBAO_CLUSTER=volcengine_streaming_common

# ========== AI 大模型 API (阿里云千问) ==========
# 申请地址: https://dashscope.console.aliyun.com/
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=<your-api-key>
OPENAI_MODEL=qwen-plus

# ========== 数据库配置（可选）==========
# DATABASE_PASSWORD=
# REDIS_PASSWORD=
EOF
```

### 5.4 验证后端配置

```bash
# 测试导入是否正常
cd ~/Project/AI-Monitor-CSA/backend
python -c "from src.main import app; print('Backend imports OK')"
```

---

## 6. 前端环境配置

### 6.1 安装 Node.js

```bash
# 使用 nvm 安装 Node.js（推荐）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# 重新加载 shell
source ~/.bashrc

# 安装 Node.js 20 LTS
nvm install 20
nvm use 20

# 验证版本
node --version  # 应显示 v20.x.x
npm --version   # 应显示 10.x.x
```

### 6.2 配置 npm 镜像源

```bash
# 使用淘宝镜像源
npm config set registry https://registry.npmmirror.com

# 验证配置
npm config get registry
```

### 6.3 安装前端依赖

```bash
# 进入前端目录
cd ~/Project/AI-Monitor-CSA/frontend

# 安装依赖
npm install

# 或使用 pnpm（更快）
npm install -g pnpm
pnpm install
```

### 6.4 构建前端（生产环境）

```bash
# 构建生产版本
npm run build

# 构建产物在 dist/ 目录
```

---

## 7. 启动服务

### 7.1 启动后端服务

```bash
# 激活环境
conda activate cc-sop

# 进入后端目录
cd ~/Project/AI-Monitor-CSA/backend

# 开发模式启动
python -m src.main

# 或使用 uvicorn 直接启动
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

后端服务地址: `http://localhost:8000`
API 文档地址: `http://localhost:8000/docs`

### 7.2 启动前端服务

打开**新的终端窗口**：

```bash
# 进入前端目录
cd ~/Project/AI-Monitor-CSA/frontend

# 开发模式启动
npm run dev
```

前端服务地址: `http://localhost:5173`

### 7.3 一键启动脚本

创建启动脚本 `start.sh`：

```bash
cat > ~/Project/AI-Monitor-CSA/start.sh << 'EOF'
#!/bin/bash

# CC-SOP Monitor 启动脚本

PROJECT_DIR="$HOME/Project/AI-Monitor-CSA"
CONDA_ENV="cc-sop"

echo "=========================================="
echo "  CC-SOP Monitor 启动中..."
echo "=========================================="

# 启动后端
echo "[1/2] 启动后端服务..."
cd "$PROJECT_DIR/backend"
source ~/miniconda3/etc/profile.d/conda.sh
conda activate $CONDA_ENV
python -m src.main &
BACKEND_PID=$!
echo "后端 PID: $BACKEND_PID"

# 等待后端启动
sleep 3

# 启动前端
echo "[2/2] 启动前端服务..."
cd "$PROJECT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
echo "前端 PID: $FRONTEND_PID"

echo ""
echo "=========================================="
echo "  服务已启动！"
echo "  后端: http://localhost:8000"
echo "  前端: http://localhost:5173"
echo "  API文档: http://localhost:8000/docs"
echo "=========================================="
echo ""
echo "按 Ctrl+C 停止所有服务"

# 捕获退出信号
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM

# 等待
wait
EOF

chmod +x ~/Project/AI-Monitor-CSA/start.sh
```

运行启动脚本：

```bash
~/Project/AI-Monitor-CSA/start.sh
```

### 7.4 从 Windows 浏览器访问

在 Windows 浏览器中打开：
- 前端界面: `http://localhost:5173`
- 后端API: `http://localhost:8000`

---

## 8. 常见问题

### Q1: 摄像头和麦克风如何工作？

**架构说明**：本系统采用浏览器原生媒体采集方案，无需在 WSL2 中配置 USB 设备。

```
┌─────────────────────────────────────────────────────────┐
│                    Windows 主机                          │
│  ┌─────────────┐     ┌─────────────────────────────┐   │
│  │ USB 摄像头   │────▶│    Windows 浏览器 (Chrome)   │   │
│  │ USB 麦克风   │────▶│  - getUserMedia() 采集视频  │   │
│  └─────────────┘     │  - MediaRecorder 采集音频   │   │
│                      │  - WebSocket 发送到后端     │   │
│                      └──────────────┬──────────────┘   │
│                                     │                   │
│                                     ▼                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │                   WSL2 (Ubuntu)                   │  │
│  │  ┌────────────────────────────────────────────┐  │  │
│  │  │           后端服务 (FastAPI)                │  │  │
│  │  │  - 接收视频帧 (WebSocket)                  │  │  │
│  │  │  - 接收音频流 (WebSocket)                  │  │  │
│  │  │  - MediaPipe 姿态检测                      │  │  │
│  │  │  - 豆包 ASR 语音识别                       │  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**工作流程**：
1. 用户在 Windows 浏览器中打开前端 (`http://localhost:5173`)
2. 浏览器请求摄像头/麦克风权限（使用 Windows USB 设备）
3. 前端通过 WebSocket 将视频帧发送到 WSL2 后端
4. 后端进行姿态检测和语音识别
5. 结果通过 WebSocket 实时返回前端显示

**浏览器权限设置**：
- 首次访问时，浏览器会弹出权限请求
- 点击「允许」授权摄像头和麦克风访问
- 如果不小心拒绝了，在地址栏左侧点击锁图标重新设置

**推荐浏览器**：Chrome / Edge（基于 Chromium）

**注意事项**：
- 确保使用 `http://localhost:5173` 而非 IP 地址访问
- `localhost` 被浏览器视为安全上下文，允许访问媒体设备
- 如需远程访问，需配置 HTTPS

### Q2: MediaPipe 报错 "libGL error"

```bash
# 安装 OpenGL 依赖
sudo apt install -y libgl1-mesa-glx libgl1-mesa-dev
```

### Q3: 端口被占用

```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>
```

### Q4: npm install 很慢或失败

```bash
# 清理缓存
npm cache clean --force

# 使用淘宝镜像
npm config set registry https://registry.npmmirror.com

# 重试
npm install
```

### Q5: Conda 环境激活失败

```bash
# 重新初始化 conda
conda init bash
source ~/.bashrc

# 如果仍有问题，手动激活
source ~/miniconda3/etc/profile.d/conda.sh
conda activate cc-sop
```

### Q6: 语音识别不工作

检查：
1. `.env` 中的 `DOUBAO_APP_ID` 和 `DOUBAO_ACCESS_TOKEN` 是否正确
2. 网络是否能访问火山引擎 API
3. 麦克风权限是否已授予

### Q7: AI 报告生成失败

检查：
1. `.env` 中的 `OPENAI_API_KEY` 是否正确
2. `OPENAI_BASE_URL` 是否为 `https://dashscope.aliyuncs.com/compatible-mode/v1`
3. 账户余额是否充足

---

## API 密钥申请指南

### 火山引擎语音识别（豆包 ASR）

1. 访问 https://console.volcengine.com/
2. 注册/登录账号
3. 进入「语音技术」-「语音识别」
4. 创建应用，获取 App ID 和 Access Token

### 阿里云千问（Qwen API）

1. 访问 https://dashscope.console.aliyun.com/
2. 注册/登录阿里云账号
3. 开通 DashScope 服务
4. 创建 API Key

---

## 版本信息

| 组件 | 版本 |
|-----|------|
| Python | 3.10+ |
| Node.js | 20 LTS |
| FastAPI | 0.100+ |
| Vue | 3.5+ |
| MediaPipe | 0.10.14 |
| PyTorch | 2.0+ |

---

*文档版本: 1.0*
*更新日期: 2025-01*

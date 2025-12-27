# CC-SOP Monitor 部署指南

## 部署架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        客户端浏览器                              │
│                    http://localhost:5173                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      前端 (Vue 3 + Vite)                         │
│  ├── 仪表盘 (Dashboard)                                          │
│  ├── 实时监控 (LiveMonitor)                                      │
│  ├── 录像分析 (PlaybackAnalysis)                                 │
│  └── 报告详情 (Reports)                                          │
│                                                                 │
│  服务端口: 5173 (开发) / 80 (生产)                               │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP / WebSocket
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    后端 API (FastAPI)                            │
│  ├── /api/sessions - 会话管理                                    │
│  ├── /api/evaluation - 评估结果                                  │
│  ├── /api/playback - 回放数据                                    │
│  ├── /api/config - 系统配置                                      │
│  └── /api/ws/live/{id} - WebSocket 实时推送                      │
│                                                                 │
│  服务端口: 8000                                                  │
│  文档: http://localhost:8000/docs                                │
└─────────────────────────────────────────────────────────────────┘
```

## 环境要求

### 后端
- Python 3.10+
- Conda (推荐) 或 virtualenv
- 依赖包见 `backend/requirements.txt`

### 前端
- Node.js 18+
- npm 或 pnpm

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd AI-Monitor-CSA
```

### 2. 后端设置

```bash
# 创建 Conda 环境
conda create -n cc-sop python=3.10 -y
conda activate cc-sop

# 安装依赖
cd backend
pip install -r requirements.txt

# 运行后端
python -m src.main
# 或
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

后端服务将在 `http://localhost:8000` 启动
- API 文档: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 3. 前端设置

```bash
cd frontend
npm install
npm run dev
```

前端将在 `http://localhost:5173` 启动

### 4. 一键启动 (开发模式)

```bash
./scripts/start_dev.sh
```

## 生产部署

### 使用 Docker Compose (推荐)

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 手动部署

#### 后端

```bash
# 安装生产依赖
pip install gunicorn

# 使用 Gunicorn 运行
gunicorn src.api.app:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile -
```

#### 前端

```bash
# 构建生产版本
npm run build

# 使用 nginx 托管静态文件
# 将 dist/ 目录复制到 nginx 的 web 根目录
```

## 配置

### 后端配置

配置文件: `backend/config/config.yaml`

```yaml
# 视频源配置
video:
  source: camera  # camera / file / rtsp
  camera_id: 0
  fps: 30

# ASR 配置
asr:
  mode: auto  # auto / online / offline
  # 豆包 API (在线模式)
  doubao:
    app_id: ${DOUBAO_APP_ID}
    access_token: ${DOUBAO_ACCESS_TOKEN}

# 评估权重
evaluation:
  weights:
    pose: 0.3
    action: 0.4
    communication: 0.3
```

### 环境变量

```bash
# 豆包 ASR API (可选)
export DOUBAO_APP_ID=your_app_id
export DOUBAO_ACCESS_TOKEN=your_token

# 云端大模型（报告生成，可选，OpenAI 兼容）
export LLM_PROVIDER=openai
export LLM_API_KEY=your_api_key
export LLM_BASE_URL=https://api.moonshot.cn/v1
export LLM_MODEL=moonshot-v1-8k

# 兼容老变量（如已使用可保留）
export OPENAI_API_KEY=your_api_key
```

### 前端配置

配置文件: `frontend/.env`

```bash
# API 地址
VITE_API_URL=http://localhost:8000

# WebSocket 地址
VITE_WS_URL=ws://localhost:8000
```

## 测试

### 运行所有测试

```bash
# 后端测试
cd backend
python -m pytest -v

# 前端测试
cd frontend
npm run test
```

### 运行集成测试

```bash
cd backend
python -m pytest tests/test_integration.py -v
```

## 目录结构

```
AI-Monitor-CSA/
├── backend/                    # 后端代码
│   ├── src/
│   │   ├── api/               # FastAPI 应用
│   │   ├── analysis/          # 分析模块
│   │   ├── evaluation/        # 评估模块
│   │   ├── input/             # 输入源
│   │   └── perception/        # 感知模块
│   ├── tests/                 # 测试用例
│   ├── config/                # 配置文件
│   └── requirements.txt
│
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── views/             # 页面组件
│   │   ├── components/        # 通用组件
│   │   ├── stores/            # Pinia 状态
│   │   ├── services/          # API 服务
│   │   └── types/             # TypeScript 类型
│   ├── package.json
│   └── vite.config.ts
│
├── scripts/                    # 脚本
│   ├── start_dev.sh           # 开发启动脚本
│   └── test_all.sh            # 测试脚本
│
├── docs/                       # 文档
│   ├── ARCHITECTURE.md        # 架构文档
│   ├── EXECUTION_PLAN.md      # 执行计划
│   └── DEPLOYMENT.md          # 部署指南
│
└── docker-compose.yml          # Docker 配置
```

## 常见问题

### Q: 后端启动失败 "ModuleNotFoundError"
A: 确保已激活正确的 Python 环境并安装了所有依赖
```bash
conda activate cc-sop
pip install -r requirements.txt
```

### Q: 前端无法连接后端
A: 检查后端是否正在运行，以及 CORS 配置是否正确

### Q: WebSocket 连接失败
A: 确保使用正确的 WebSocket URL，检查防火墙设置

### Q: 评估结果为空
A: 确保会话有足够的数据帧后再停止会话

## 支持

如有问题，请提交 Issue 或联系开发团队。

# CC-SOP Monitor

**客舱乘务员姿态与操作规范监测系统** (Cabin Crew Standard Operating Procedure Monitor)

> 为中国南方航空开发的AI训练评估系统

---

## 项目简介

本系统通过计算机视觉与时序逻辑分析，对客舱乘务员在模拟舱内的训练表现进行全方位监测。系统不仅关注静态姿态，更侧重于关键安全动作的时间戳合规性及设备交互的精准度。

### 核心能力

- **骨骼姿态识别**: 实时追踪33个人体关键点，分析"标准立姿"、"深蹲取物"、"应急撤离指挥"等特定姿态的夹角
- **关键动作识别**: 识别"按压呼叫按钮"、"提起灭火器"、"佩戴防烟面罩"等关键交互动作
- **SOP时序分析**: 基于SOP标准库，监测动作发生的先后顺序及持续时间
- **通讯监测**: 通过ASR监测乘务员与驾驶舱沟通的术语规范性与及时性
- **智能评估**: 三维度评分（姿态标准分、动作时效分、沟通协同分）+ AI改进建议

### 运行模式

- **实时监测**: 训练进行时实时分析并给出反馈
- **录像分析**: 训练结束后对录像进行离线分析

---

## 技术栈

| 模块 | 技术 |
|------|------|
| 后端框架 | Python 3.10+, FastAPI |
| 姿态检测 | MediaPipe Pose |
| 动作识别 | ST-GCN + LSTM |
| 语音识别 | Whisper |
| 数据库 | PostgreSQL + Redis |
| 前端框架 | React + TypeScript |
| 可视化 | ECharts + Three.js |

---

## 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 18
- PostgreSQL >= 14
- Redis >= 6
- CUDA >= 11.8 (可选，用于GPU加速)

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd AI-Monitor-CSA

# 后端安装
cd backend
pip install -r requirements.txt

# 下载模型
bash scripts/download_models.sh

# 前端安装
cd ../frontend
npm install
```

### 运行

```bash
# 启动后端服务
cd backend
python -m src.main

# 启动前端（新终端）
cd frontend
npm run dev
```

访问 http://localhost:5173 查看界面

---

## 项目结构

```
AI-Monitor-CSA/
├── backend/              # 后端服务
│   ├── src/
│   │   ├── input/        # 视频/音频输入
│   │   ├── perception/   # 姿态检测/动作识别/ASR
│   │   ├── analysis/     # SOP时序分析
│   │   ├── evaluation/   # 评估引擎
│   │   └── api/          # REST API
│   └── config/           # 配置文件
├── frontend/             # 前端项目
│   └── src/
│       ├── pages/        # 页面
│       └── components/   # 组件
├── models/               # AI模型文件
├── docs/                 # 文档
│   ├── ARCHITECTURE.md   # 架构设计
│   ├── DEVELOPMENT_GUIDE.md # 开发指南
│   └── EXECUTION_PLAN.md # 执行计划
└── scripts/              # 脚本
```

---

## 配置说明

主配置文件: `backend/config/config.yaml`

```yaml
# 示例配置
system:
  name: "CC-SOP Monitor"
  language: "zh"

asr:
  model: whisper-small
  language: zh

pose:
  model: mediapipe
  confidence_threshold: 0.5

evaluation:
  pose_weight: 0.3
  action_weight: 0.4
  communication_weight: 0.3
```

---

## 文档

- [架构设计文档](docs/ARCHITECTURE.md) - 系统架构与模块设计
- [开发指南](docs/DEVELOPMENT_GUIDE.md) - 开发环境搭建与编码规范
- [执行计划](docs/EXECUTION_PLAN.md) - 项目开发阶段与任务分解

---

## API文档

启动后端后访问: http://localhost:8000/docs

---

## UI设计规范

- **风格**: 航空工业科技感，深色半透明HUD界面
- **主色调**: 深蓝(#0a1628) + 青色发光(#00d4ff)
- **字体**:
  - 中文: 微软雅黑
  - 英文/数字: Times New Roman

---

## 许可证

Proprietary - China Southern Airlines

---

## 联系方式

如有问题，请联系项目负责人。

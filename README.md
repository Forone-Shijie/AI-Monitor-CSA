# CC-SOP Monitor

**客舱乘务员姿态与操作规范监测系统** (Cabin Crew Standard Operating Procedure Monitor)

> 为中国南方航空开发的AI训练评估系统

---

## 项目概述

本系统通过**计算机视觉与时序逻辑分析**，对客舱乘务员在模拟舱内的训练表现进行全方位、客观化监测。

### 服务对象

- **客舱训练质量评估** - 对乘务员训练表现进行客观化、数据化评估
- **教员教学复盘** - 提供详细的训练数据支持教学改进
- **胜任力评估基础** - 为后续智能化胜任力评估系统建设提供数据积累

### 运行模式

| 模式 | 说明 |
|------|------|
| **实时监测** | 训练进行时实时分析并给出反馈 |
| **录像分析** | 训练结束后对录像进行离线分析 |

---

## 核心功能

### 1. 骨骼姿态识别

实时追踪人体关键点，分析姿态合规性：

- **关键点追踪**: 头部、颈部、脊柱（上背/下背）、肩肘腕、髋膝踝
- **姿态分类**: 标准立姿、深蹲取物、应急撤离指挥、服务鞠躬
- **夹角计算**: 实时计算关节角度，与标准姿态对比

### 2. 防冲击姿势场景检测 (Brace Position)

针对防冲击姿势训练场景的专项检测能力：

| 检测维度 | 检测内容 |
|---------|---------|
| **场景触发** | 教员指令识别 / 训练系统事件 / 姿态突变检测 |
| **躯干与背部** | 上背/下背是否紧贴座椅靠背 |
| **头部与颈部** | 面向机尾：贴靠头枕 / 面向机头：下颌内收 |
| **上肢与手部** | 双臂交叉 或 双手放置大腿 |
| **下肢与脚部** | 膝关节约90°、双脚平放 |
| **时序判别** | 场景触发→姿态到位时间、保持稳定性 |

### 3. 关键动作识别

识别乘务员关键交互动作：

- 按压呼叫按钮
- 提起灭火器
- 佩戴防烟面罩
- 打开应急门
- 安全带检查

### 4. SOP时序分析

基于SOP标准库，监测动作序列合规性：

- 动作发生的先后顺序
- 动作完成的时间窗口
- 关键步骤是否遗漏

### 5. 通讯监测

通过ASR监测乘务员与驾驶舱沟通：

- 术语规范性检测
- 响应及时性分析

### 6. 智能评估

三维度综合评分 + AI改进建议：

| 维度 | 权重 | 评分标准 |
|------|-----|---------|
| 姿态标准分 | 30% | 关键姿态夹角偏差 |
| 动作时效分 | 40% | SOP时间窗口合规性 |
| 沟通协同分 | 30% | 通讯及时性与术语规范 |

---

## 技术架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CC-SOP Monitor System                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   输入层          感知层              分析层           评估层        │
│  ┌────────┐    ┌────────────┐    ┌────────────┐    ┌──────────┐   │
│  │视频输入│───→│ 姿态检测   │───→│ SOP时序    │───→│ 评估引擎 │   │
│  │音频输入│───→│ 动作识别   │───→│ 分析引擎   │───→│ 报告生成 │   │
│  │事件触发│───→│ 语音识别   │    │            │    │          │   │
│  └────────┘    └────────────┘    └────────────┘    └──────────┘   │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                          前端展示层 (HUD风格)                         │
│                   实时监控 / 录像回放 / 报告查看                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 技术栈

| 模块 | 技术 |
|------|------|
| 后端框架 | Python 3.10+, FastAPI |
| 姿态检测 | MediaPipe Pose (33关键点) |
| 动作识别 | ST-GCN + LSTM |
| 语音识别 | 豆包 ASR API / Whisper (双模式) |
| 数据库 | PostgreSQL + Redis |
| 前端框架 | Vue 3 + TypeScript, Vite |
| UI组件库 | Element Plus |
| 可视化 | ECharts + Three.js (3D骨骼) |

---

## 开发状态

**当前阶段**: Phase 0 - 项目初始化

| 阶段 | 目标 | 状态 |
|------|------|------|
| Phase 0 | 项目初始化 | 进行中 |
| Phase 1 | 视频输入层 | 待开始 |
| Phase 2 | 姿态检测（含防冲击姿势） | 待开始 |
| Phase 3 | 动作识别 | 待开始 |
| Phase 4 | 语音识别 | 待开始 |
| Phase 5 | SOP分析（含场景触发） | 待开始 |
| Phase 6 | 评估引擎 | 待开始 |
| Phase 7 | 后端API | 待开始 |
| Phase 8 | 前端开发 | 待开始 |
| Phase 9 | 系统集成 | 待开始 |
| Phase 10 | 部署交付 | 待开始 |

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
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
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
├── backend/                  # 后端服务
│   ├── src/
│   │   ├── input/            # 视频/音频输入
│   │   ├── perception/       # 姿态检测/动作识别/ASR
│   │   ├── analysis/         # SOP时序分析/防冲击姿势检测
│   │   ├── evaluation/       # 评估引擎
│   │   └── api/              # REST API
│   ├── config/               # 配置文件
│   └── tests/                # 测试
│
├── frontend/                 # 前端项目 (Vue 3 + TypeScript)
│   └── src/
│       ├── views/            # 页面视图
│       ├── components/       # 组件
│       ├── stores/           # Pinia 状态管理
│       └── router/           # Vue Router
│
├── models/                   # AI模型文件
├── docs/                     # 文档
├── scripts/                  # 脚本
└── docker/                   # Docker配置
```

---

## 文档导航

| 文档 | 说明 |
|------|------|
| [架构设计](docs/ARCHITECTURE.md) | 系统架构与模块设计 |
| [开发指南](docs/DEVELOPMENT_GUIDE.md) | 开发环境搭建与编码规范 |
| [执行计划](docs/EXECUTION_PLAN.md) | 项目开发阶段与任务分解 |
| [技术栈推荐](docs/Technology_Stack_Recommendation.md) | 企业级技术选型规范参考 |

---

## 配置说明

主配置文件: `backend/config/config.yaml`

```yaml
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

SOP规则文件: `backend/config/sop_rules.yaml`

---

## UI设计规范

- **风格**: 航空工业科技感，深色半透明HUD界面
- **主色调**: 深蓝(#0a1628) + 青色发光(#00d4ff)
- **字体**:
  - 中文: 微软雅黑
  - 英文/数字: Times New Roman

---

## 开发命令

### 后端

```bash
cd backend
python -m src.main              # 运行
black src && isort src          # 格式化
mypy src                        # 类型检查
pytest                          # 测试
pytest --cov=src                # 覆盖率
```

### 前端

```bash
cd frontend
npm run dev                     # 开发服务器
npm run lint                    # 代码检查
npm run format                  # 格式化
npm run test                    # 测试
```

### Docker

```bash
docker-compose build
docker-compose up -d
docker-compose logs -f
```

---

## API文档

启动后端后访问: http://localhost:8000/docs

---

## 许可证

Proprietary - China Southern Airlines

---

## 联系方式

如有问题，请联系项目负责人 张士杰，Email：sjzhang1130@gmail.com。

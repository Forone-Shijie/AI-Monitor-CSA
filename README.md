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
| 姿态检测 | RTMPose-M (MMPose, COCO 17关键点, GPU加速) |
| 动作识别 | ST-GCN + LSTM |
| 语音识别 | 豆包 ASR API / Whisper (双模式) |
| 数据库 | PostgreSQL + Redis |
| 前端框架 | Vue 3 + TypeScript, Vite |
| UI组件库 | Element Plus |
| 可视化 | ECharts + Three.js (3D骨骼) |

---

## 开发状态

**当前阶段**: Phase 5 - 核心功能已实现

| 阶段 | 目标 | 状态 |
|------|------|------|
| Phase 0 | 项目初始化 | 完成 |
| Phase 1 | 视频输入层 | 完成 |
| Phase 2 | 姿态检测（RTMPose多人检测） | 完成 |
| Phase 3 | 动作识别 | 进行中 |
| Phase 4 | 语音识别（豆包ASR流式） | 完成 |
| Phase 5 | SOP分析（含场景触发） | 进行中 |
| Phase 6 | 评估引擎 | 待开始 |
| Phase 7 | 后端API | 完成 |
| Phase 8 | 前端开发 | 完成 |
| Phase 9 | 系统集成 | 进行中 |
| Phase 10 | 部署交付 | 待开始 |

### 已实现功能

- **实时监控**: 摄像头输入 + WebSocket实时骨骼叠加显示
- **视频分析**: 视频上传 + 离线分析 + 骨骼可视化
- **多人姿态检测**: RTMPose-M 支持同时检测5人
- **语音识别**: 豆包ASR流式识别 + 实时字幕显示
- **SOP时间轴**: ECharts时间轴展示动作序列

---

## 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 18
- PostgreSQL >= 14
- Redis >= 6
- **NVIDIA GPU** (必需，RTMPose 姿态检测)
- CUDA >= 12.0 (推荐 12.4，RTX 50系列需要 12.8)

#### GPU 兼容性说明

| GPU 架构 | 显卡型号 | CUDA 要求 | 特殊处理 |
|----------|----------|-----------|----------|
| Ampere | RTX 30系列 | 12.0+ | 无 |
| Ada Lovelace | RTX 40系列 | 12.0+ | 无 |
| Blackwell | RTX 50系列 (5070/5080/5090) | **12.8+** | 需要特殊安装 |

> **RTX 50系列用户注意**: Blackwell架构(sm_120)需要PyTorch nightly + 源码编译mmcv，详见下方安装说明。

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

### RTX 50系列 (Blackwell架构) 特殊安装

RTX 5070/5080/5090 等 Blackwell 架构显卡需要额外步骤：

```bash
# 运行 Blackwell 兼容性修复脚本
bash scripts/fix_cuda_blackwell.sh
```

**脚本会自动完成以下步骤：**

1. **安装 PyTorch nightly (CUDA 12.8)**
   ```bash
   pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
   ```

2. **安装 CUDA toolkit 12.8**
   ```bash
   conda install -y -c conda-forge cuda-nvcc=12.8.93 cuda-cudart-dev cuda-libraries-dev ninja
   ```

3. **安装 MM 系列依赖**
   ```bash
   pip install openmim mmengine mmdet
   pip install mmpose --no-deps
   pip install xtcocotools munkres json_tricks
   ```

4. **从源码编译 mmcv (支持 sm_120)**
   ```bash
   cd /tmp && git clone --depth 1 -b v2.1.0 https://github.com/open-mmlab/mmcv.git
   cd mmcv
   export TORCH_CUDA_ARCH_LIST="8.0;8.6;9.0;12.0"
   python setup.py develop
   ```

> **注意**: 源码编译 mmcv 需要 GCC < 14.0，脚本会自动使用系统 GCC。编译过程约需 10-15 分钟。

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

## AI报告（云API）

系统支持 **OpenAI 兼容协议** 的云端大模型，用于生成训练报告的 AI 改进建议。

**环境变量配置：**

```bash
export LLM_PROVIDER=openai
export LLM_API_KEY=你的API_KEY
export LLM_BASE_URL=你的服务BaseURL
export LLM_MODEL=模型名称
```

**国内云API推荐（均支持 OpenAI 兼容调用）：**

- **阿里云通义千问（DashScope）**: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- **月之暗面 Moonshot**: `https://api.moonshot.cn/v1`
- **DeepSeek**: `https://api.deepseek.com/v1`

未配置时报告会提示「AI未配置」。

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
│   │   ├── services/         # 业务服务（视频管理等）
│   │   └── api/              # REST API + WebSocket
│   │       └── routes/       # API路由（websocket/uploads）
│   ├── config/               # 配置文件
│   ├── uploads/              # 上传视频存储目录
│   └── tests/                # 测试
│
├── frontend/                 # 前端项目 (Vue 3 + TypeScript)
│   └── src/
│       ├── views/            # 页面视图（Dashboard/VideoAnalyzer）
│       ├── components/       # 组件（骨骼叠加/评分面板/上传组件）
│       ├── stores/           # Pinia 状态管理
│       ├── services/         # API/WebSocket服务
│       └── router/           # Vue Router
│
├── models/                   # AI模型文件
├── docs/                     # 文档
├── scripts/                  # 脚本（安装/模型下载/CUDA修复）
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
| [RTX 50系列部署](docs/DEPLOYMENT_BLACKWELL.md) | Blackwell架构GPU部署指南 |
| [CLAUDE.md](CLAUDE.md) | Claude Code AI辅助开发指南 |

### GPU兼容性脚本

| 脚本 | 说明 |
|------|------|
| `scripts/install_deps.sh` | 标准依赖安装（RTX 30/40系列） |
| `scripts/fix_cuda_blackwell.sh` | RTX 50系列 Blackwell架构修复 |
| `scripts/download_models.sh` | 下载RTMPose模型权重 |

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
  engine: rtmpose
  device: "cuda:0"
  det_score_thr: 0.3
  pose_score_thr: 0.3
  max_persons: 5

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

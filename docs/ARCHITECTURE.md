# CC-SOP Monitor 系统架构设计文档

## 1. 系统概述

### 1.1 项目信息

| 项目 | 信息 |
|------|------|
| **项目名称** | 客舱乘务员姿态与操作规范监测系统 (CC-SOP Monitor) |
| **客户** | 中国南方航空 |
| **系统类型** | 独立部署，本地服务器 |
| **运行模式** | 实时监测 + 录像回放分析 |

### 1.2 核心目标

通过计算机视觉与时序逻辑分析，对客舱乘务员在模拟舱内的训练表现进行全方位监测：

1. **骨骼与姿态高精度识别** - 实时追踪头、颈、脊柱、四肢等关键点
2. **关键动作与时序逻辑分析** - 识别关键交互动作，监测SOP合规性
3. **通讯及时性监测** - 通过ASR监测术语规范性和响应时间
4. **评估与打分** - 三维度评分 + AI改进建议报告

### 1.3 需求概述

#### 服务对象
- **客舱训练质量评估** - 对乘务员训练表现进行客观化、数据化评估
- **教员教学复盘** - 提供详细的训练数据支持教学改进
- **胜任力评估数据基础** - 为后续智能化胜任力评估系统建设提供数据积累

#### 核心能力要求
系统不仅关注静态姿态是否标准，更侧重于：
- 关键安全动作是否被正确执行
- 动作发生的**时间点、持续时间与先后顺序**是否符合 SOP 要求
- 人员与设备之间的**关键交互是否精准、及时**

#### 骨骼关键点识别要求
需至少识别并持续追踪以下关键点：
- 头部、颈部
- 脊柱（上背 / 下背）
- 肩、肘、腕
- 髋、膝、踝

支持坐姿、站姿及动作切换过程中的稳定识别。

---

## 2. 系统架构

### 2.1 总体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CC-SOP Monitor System                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ 视频输入层  │  │ 音频输入层  │  │ 事件触发层  │  │ 配置管理层  │    │
│  │ VideoInput  │  │ AudioInput  │  │EventTrigger │  │  ConfigMgr  │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│         │                │                │                │            │
│         ▼                ▼                ▼                ▼            │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      数据同步与对齐层 (Synchronizer)              │  │
│  │                    时间戳对齐 / 多模态数据融合                     │  │
│  └────────────────────────────┬─────────────────────────────────────┘  │
│                               │                                         │
│         ┌─────────────────────┼─────────────────────┐                   │
│         ▼                     ▼                     ▼                   │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐           │
│  │  姿态检测   │       │  动作识别   │       │  语音识别   │           │
│  │PoseDetector │       │ActionRecog  │       │    ASR      │           │
│  │ MediaPipe   │       │ ST-GCN/CNN  │       │  豆包 ASR   │           │
│  └──────┬──────┘       └──────┬──────┘       └──────┬──────┘           │
│         │                     │                     │                   │
│         └─────────────────────┼─────────────────────┘                   │
│                               ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    时序逻辑分析引擎 (SOP Analyzer)                │  │
│  │           SOP标准库 / 动作序列比对 / 时间窗口校验                  │  │
│  └────────────────────────────┬─────────────────────────────────────┘  │
│                               │                                         │
│                               ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      评估引擎 (Evaluator)                         │  │
│  │           姿态标准分 / 动作时效分 / 沟通协同分                     │  │
│  └────────────────────────────┬─────────────────────────────────────┘  │
│                               │                                         │
│         ┌─────────────────────┼─────────────────────┐                   │
│         ▼                     ▼                     ▼                   │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐           │
│  │  报告生成   │       │  实时反馈   │       │  数据存储   │           │
│  │ReportEngine │       │ LiveFeedback│       │  Database   │           │
│  └─────────────┘       └─────────────┘       └─────────────┘           │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                         前端展示层 (Frontend)                            │
│                    HUD风格 / 实时监控 / 报告查看                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流Pipeline

```
语音输入 ─┬─→ ASR转文本 ──────────────────────────┐
          │                                        │
视频输入 ─┼─→ 姿态检测 ─→ 夹角计算 ────────────────┼─→ 多模态同步
          │                                        │      │
          └─→ 动作识别 ─→ 动作事件 ────────────────┘      │
                                                          ▼
                                                   SOP时序分析
                                                          │
                                                          ▼
                                                     评估引擎
                                                          │
                                          ┌───────────────┼───────────────┐
                                          ▼               ▼               ▼
                                      实时反馈        报告生成        数据存储
```

---

## 3. 技术选型

| 模块 | 技术选型 | 备选方案 | 说明 |
|------|---------|---------|------|
| **后端框架** | FastAPI | Flask | 高性能异步API |
| **姿态检测** | MediaPipe Pose | OpenPose | 实时性好，部署简单 |
| **动作识别** | ST-GCN + LSTM | SlowFast | 基于骨骼的动作识别 |
| **语音识别** | 豆包 ASR (bigmodel_async) | - | 火山引擎流式语音识别 |
| **时序分析** | 自定义规则引擎 | - | 基于SOP标准库 |
| **数据库** | PostgreSQL + Redis | - | 持久化 + 缓存 |
| **前端框架** | Vue 3 + TypeScript | React | 企业推荐，Vite构建 |
| **UI组件库** | Element Plus | Ant Design Vue | 桌面端组件丰富 |
| **可视化** | ECharts + Three.js | D3.js | 3D骨骼可视化 |
| **视频处理** | OpenCV + FFmpeg | - | 视频流处理 |
| **消息队列** | Redis Streams | RabbitMQ | 实时数据流 |

---

## 4. 核心模块设计

### 4.1 姿态检测模块 (PoseDetector)

#### 职责
- 实时检测人体33个关键点
- 计算关键姿态夹角（如膝关节角度、脊柱弯曲度）
- 支持标准姿态比对

#### 输出数据结构
```python
@dataclass
class PoseResult:
    timestamp: float                    # 时间戳
    keypoints: List[Keypoint]           # 33个关键点
    angles: Dict[str, float]            # 关键夹角
    pose_type: str                      # 姿态类型: standing/squatting/bending
    confidence: float                   # 置信度
    deviations: Dict[str, float]        # 与标准姿态的偏差
```

#### 关键姿态定义
| 姿态名称 | 英文标识 | 检测要点 |
|---------|---------|---------|
| 标准立姿 | standard_standing | 脊柱角度<10°, 双腿并拢 |
| 深蹲取物 | deep_squat | 膝关节角度<90°, 背部挺直 |
| 应急撤离指挥 | evacuation_command | 手臂伸直指向出口 |
| 服务鞠躬 | service_bow | 腰部弯曲15-30° |

---

### 4.2 动作识别模块 (ActionRecognizer)

#### 职责
- 识别乘务员关键交互动作
- 输出动作类型、开始/结束时间、置信度

#### 关键动作列表
| 动作ID | 动作名称 | 检测方法 |
|--------|---------|---------|
| ACT_001 | 按压呼叫按钮 | 手部位置+按压动作 |
| ACT_002 | 提起灭火器 | 物体检测+抓握姿态 |
| ACT_003 | 佩戴防烟面罩 | 面部遮挡检测 |
| ACT_004 | 打开应急门 | 手臂动作轨迹 |
| ACT_005 | 安全带检查 | 巡视动作+注视方向 |

#### 输出数据结构
```python
@dataclass
class ActionEvent:
    action_id: str                      # 动作ID
    action_name: str                    # 动作名称
    start_time: float                   # 开始时间
    end_time: float                     # 结束时间
    duration: float                     # 持续时间
    confidence: float                   # 置信度
    keyframes: List[float]              # 关键帧时间戳
```

---

### 4.3 SOP时序分析引擎 (SOPAnalyzer)

#### 职责
- 加载SOP标准规则库
- 比对动作序列与标准流程
- 检测时间窗口合规性

#### SOP规则定义格式
```yaml
# sop_rules.yaml
scenarios:
  fire_emergency:
    name: "火警处置流程"
    trigger_event: "fire_alarm"
    steps:
      - step_id: 1
        action: "ACT_001"  # 按压呼叫按钮
        time_limit: 3      # 必须在3秒内完成
        required: true
      - step_id: 2
        action: "ACT_002"  # 提起灭火器
        time_limit: 10
        required: true
      - step_id: 3
        action: "ACT_003"  # 佩戴防烟面罩
        time_limit: 15
        required: true
    max_total_time: 30     # 总流程不超过30秒
```

#### 输出数据结构
```python
@dataclass
class SOPComplianceResult:
    scenario_id: str
    scenario_name: str
    trigger_time: float
    steps_compliance: List[StepCompliance]
    total_time: float
    is_compliant: bool
    violations: List[str]              # 违规项描述
```

---

### 4.4 评估引擎 (Evaluator)

#### 评分维度

| 维度 | 权重 | 评分标准 |
|------|-----|---------|
| 姿态标准分 | 30% | 关键姿态夹角偏差 |
| 动作时效分 | 40% | SOP时间窗口合规性 |
| 沟通协同分 | 30% | 通讯及时性与术语规范 |

#### AI分析报告生成
- 使用LLM（如Qwen2.5）生成自然语言改进建议
- 报告包含：总分、各维度得分、具体问题点、改进建议

示例报告输出：
> "在火情处置中，由于重心不稳导致取灭火器动作延迟2秒，建议加强核心力量训练"

---

### 4.5 防冲击姿势场景检测模块 (BracePositionDetector)

防冲击姿势（Brace Position）是客舱安全训练的核心场景之一，属于**单一关键动作场景 + 多姿态约束 + 时间维度判别**的复合检测任务。

#### 4.5.1 场景触发识别

系统需识别防冲击姿势场景的开始条件：

| 触发类型 | 触发方式 | 检测方法 |
|---------|---------|---------|
| 教员指令 | "Brace" / "防冲击姿势" | ASR关键词检测 |
| 系统事件 | 模拟迫降、紧急着陆 | 训练系统事件API |
| 姿态变化 | 乘务员开始调整姿态 | 姿态突变检测 |

系统记录**场景触发时间戳**。

#### 4.5.2 姿态到位判别逻辑

基于 SOP 标准库，对防冲击姿势是否"到位"进行综合判定：

**（1）躯干与背部姿态**
- 上背部、下背部是否紧贴座椅靠背
- 脊柱是否处于稳定收紧状态
- 检测指标：背部与座椅夹角 < 10°

**（2）头部与颈部姿态**
- 面向机尾：头部是否贴靠座椅靠背或头枕
- 面向机头：下颌是否内收并靠近胸部
- 检测指标：颈椎角度偏差

**（3）上肢与手部姿态**
- 面向机尾：双臂是否在胸前交叉，且未抓握安全带
- 面向机头：双手是否自然放置于大腿
- 检测指标：手腕位置相对于胸部/大腿的距离

**（4）下肢与脚部姿态**
- 膝关节弯曲角度是否接近 SOP 要求（约90°）
- 双脚是否平放地板
- 是否符合有/无前舱壁条件下的腿部位置要求
- 检测指标：膝关节角度 85°-95°

#### 4.5.3 时序判别与稳定性检测

**时序判别**
- 从场景触发到姿态"完全到位"的时间
- 是否在 SOP 规定的时间窗口内完成
- 是否存在明显延迟或反复调整行为

**稳定性检测**
- 姿态是否在规定时间内保持稳定
- 是否出现明显抬头、松背、松腿等姿态松散行为
- 是否提前解除防冲击姿势

#### 4.5.4 输出数据结构

```python
@dataclass
class BodyPartStatus:
    part_name: str                      # 部位名称: torso/head/arms/legs
    is_compliant: bool                  # 是否合规
    deviation: float                    # 偏差值
    description: str                    # 状态描述

@dataclass
class BracePositionResult:
    scenario_id: str                    # 场景ID
    trigger_time: float                 # 场景触发时间
    trigger_type: str                   # 触发类型: voice/event/posture
    completion_time: float              # 姿态到位时间
    time_to_complete: float             # 完成耗时
    is_compliant: bool                  # 整体是否合规
    body_parts: Dict[str, BodyPartStatus]  # 各部位状态
    stability_duration: float           # 稳定保持时长
    stability_lost_at: Optional[float]  # 姿态失效时间点
    violations: List[str]               # 违规项列表
```

#### 4.5.5 SOP规则定义

```yaml
# sop_rules.yaml
scenarios:
  brace_position:
    name: "防冲击姿势"
    trigger_keywords: ["brace", "防冲击", "防冲击姿势"]
    time_limit: 5                       # 5秒内完成姿态
    min_hold_duration: 30               # 至少保持30秒
    body_parts:
      torso:
        name: "躯干与背部"
        max_angle_deviation: 10         # 背部与座椅最大夹角
      head:
        name: "头部与颈部"
        position: "rear_facing"         # 或 front_facing
      arms:
        name: "上肢与手部"
        position: "crossed"             # 或 on_thighs
      legs:
        name: "下肢与脚部"
        knee_angle_min: 85
        knee_angle_max: 95
        feet_flat: true
```

---

## 5. 代码目录结构

```
AI-Monitor-CSA/
├── README.md                          # 项目说明文档
├── docs/                              # 文档目录
│   ├── ARCHITECTURE.md                # 架构设计文档
│   ├── DEVELOPMENT_GUIDE.md           # 开发指南
│   ├── EXECUTION_PLAN.md              # 执行计划
│   └── API.md                         # API接口文档
│
├── backend/                           # 后端服务
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── config/
│   │   ├── config.yaml                # 主配置文件
│   │   ├── sop_rules.yaml             # SOP规则定义
│   │   └── actions.yaml               # 动作定义
│   │
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI入口
│   │   │
│   │   ├── input/                     # 输入层
│   │   │   ├── video_source.py        # 视频源抽象
│   │   │   ├── camera_input.py        # 摄像头输入
│   │   │   ├── rtsp_input.py          # RTSP流输入
│   │   │   ├── file_input.py          # 文件输入
│   │   │   └── audio_input.py         # 音频输入
│   │   │
│   │   ├── perception/                # 感知层
│   │   │   ├── pose_detector.py       # 姿态检测基类
│   │   │   ├── mediapipe_pose.py      # MediaPipe实现
│   │   │   ├── action_recognizer.py   # 动作识别基类
│   │   │   ├── stgcn_recognizer.py    # ST-GCN实现
│   │   │   ├── asr_engine.py          # ASR基类
│   │   │   └── doubao_asr_engine.py   # 豆包流式ASR (bigmodel_async)
│   │   │
│   │   ├── analysis/                  # 分析层
│   │   │   ├── synchronizer.py        # 多模态数据同步
│   │   │   ├── sop_analyzer.py        # SOP时序分析引擎
│   │   │   ├── pose_analyzer.py       # 姿态分析
│   │   │   ├── action_sequence.py     # 动作序列分析
│   │   │   └── communication_analyzer.py # 通讯分析
│   │   │
│   │   ├── evaluation/                # 评估层
│   │   │   ├── evaluator.py           # 评估引擎
│   │   │   ├── pose_scorer.py         # 姿态标准分
│   │   │   ├── action_scorer.py       # 动作时效分
│   │   │   ├── communication_scorer.py # 沟通协同分
│   │   │   └── report_generator.py    # 报告生成器
│   │   │
│   │   ├── models/                    # 数据模型
│   │   │   ├── pose.py                # 姿态数据模型
│   │   │   ├── action.py              # 动作数据模型
│   │   │   ├── event.py               # 事件数据模型
│   │   │   └── session.py             # 训练会话模型
│   │   │
│   │   ├── database/                  # 数据库层
│   │   │   ├── db.py                  # 数据库连接
│   │   │   └── repositories/          # 数据仓库
│   │   │
│   │   ├── api/                       # API路由
│   │   │   ├── router.py              # 主路由
│   │   │   ├── session.py             # 会话管理API
│   │   │   ├── monitoring.py          # 实时监控API
│   │   │   ├── playback.py            # 录像回放API
│   │   │   ├── reports.py             # 报告API
│   │   │   └── websocket.py           # WebSocket实时推送
│   │   │
│   │   └── utils/                     # 工具类
│   │       ├── logger.py              # 日志
│   │       ├── config_loader.py       # 配置加载
│   │       └── time_utils.py          # 时间工具
│   │
│   └── tests/                         # 测试
│       ├── test_pose_detector.py
│       ├── test_action_recognizer.py
│       └── test_sop_analyzer.py
│
├── frontend/                          # 前端项目 (Vue 3 + TypeScript)
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.ts                    # 入口文件
│       ├── App.vue                    # 根组件
│       ├── components/                # 组件
│       │   ├── layout/
│       │   ├── monitoring/            # 实时监控组件
│       │   ├── playback/              # 录像回放组件
│       │   └── reports/               # 报告组件
│       ├── views/                     # 页面视图
│       │   ├── Dashboard.vue
│       │   ├── LiveMonitor.vue
│       │   ├── PlaybackAnalysis.vue
│       │   └── Reports.vue
│       ├── stores/                    # Pinia 状态管理
│       │   └── index.ts
│       ├── router/                    # Vue Router
│       │   └── index.ts
│       └── styles/                    # 样式
│           ├── hud-theme.css
│           └── variables.css
│
├── models/                            # AI模型文件
│   ├── pose/                          # 姿态检测模型
│   ├── action/                        # 动作识别模型
│   └── asr/                           # 语音识别模型
│
├── scripts/                           # 脚本
│   ├── setup.sh
│   ├── download_models.sh
│   └── train_action_model.py
│
├── docker/                            # Docker配置
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
│
└── data/                              # 数据目录
    ├── sop_standards/                 # SOP标准数据
    ├── training_data/                 # 训练数据
    └── sample_videos/                 # 示例视频
```

---

## 6. 接口定义

### 6.1 模块间接口

#### ASR -> 分析层
```python
@dataclass
class ASRResult:
    text: str
    confidence: float
    timestamp: float
    language: str = "zh"
```

#### 姿态检测 -> 分析层
```python
@dataclass
class PoseResult:
    timestamp: float
    keypoints: List[Keypoint]
    angles: Dict[str, float]
    pose_type: str
    confidence: float
```

#### 动作识别 -> 分析层
```python
@dataclass
class ActionEvent:
    action_id: str
    action_name: str
    start_time: float
    end_time: float
    confidence: float
```

#### 评估引擎 -> 报告生成
```python
@dataclass
class EvaluationResult:
    session_id: str
    total_score: float
    pose_score: float
    action_score: float
    communication_score: float
    violations: List[Violation]
    recommendations: List[str]
```

---

## 7. 前端UI设计规范

### 7.1 视觉风格
- **主题**: 航空工业科技感，深色半透明HUD界面
- **主色调**: 深蓝(#0a1628) + 青色发光(#00d4ff)
- **字体**:
  - 中文: 微软雅黑
  - 英文/数字: Times New Roman
- **特效**: 边框发光、数据扫描线、半透明玻璃效果

### 7.2 HUD样式变量
```css
:root {
  --hud-bg: rgba(10, 22, 40, 0.85);
  --hud-border: #00d4ff;
  --hud-glow: 0 0 10px rgba(0, 212, 255, 0.5);
  --hud-text: #e0f7ff;
  --hud-warning: #ffaa00;
  --hud-error: #ff4444;
  --hud-success: #00ff88;
  --font-cn: "Microsoft YaHei", sans-serif;
  --font-en: "Times New Roman", serif;
}
```

### 7.3 核心页面
1. **仪表盘 (Dashboard)** - 系统状态总览
2. **实时监控 (LiveMonitor)** - 视频流+骨骼叠加+实时评分
3. **录像分析 (PlaybackAnalysis)** - 时间轴+标注+慢放
4. **报告详情 (Reports)** - 雷达图+时间线+改进建议

---

## 8. 技术风险与应对

| 风险 | 影响 | 应对措施 |
|-----|-----|---------|
| 动作识别准确率不足 | 评估不准确 | 收集更多标注数据，采用数据增强 |
| 多模态同步延迟 | 时序分析不准 | 使用统一时间戳，毫秒级对齐 |
| 实时性能不足 | 延迟过高 | GPU加速，模型量化，多线程处理 |
| LLM生成质量不稳定 | 报告质量差 | 使用Few-shot Prompt，增加约束 |

---

## 9. 硬件需求

| 配置 | 最低要求 | 推荐配置 |
|------|---------|---------|
| **CPU** | 4核 | 8核+ |
| **内存** | 8GB | 16GB+ |
| **存储** | 50GB | 100GB+ |
| **GPU** | 可选 | NVIDIA RTX 3060+ (8GB显存) |

---

## 10. 参考文档

- [技术栈推荐矩阵](./Technology_Stack_Recommendation.md) - 企业级技术选型规范参考

---

**文档版本**: v1.1
**最后更新**: 2025-12-23
**作者**: AI Monitor Project Team

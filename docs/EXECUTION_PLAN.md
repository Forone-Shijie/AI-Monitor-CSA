# CC-SOP Monitor 项目执行计划

## 项目信息

| 项目 | 信息 |
|------|------|
| **项目名称** | 客舱乘务员姿态与操作规范监测系统 (CC-SOP Monitor) |
| **项目路径** | `/home/sjzhang/Project/AI-Monitor-CSA` |
| **开发模式** | 迭代式开发，分阶段交付 |
| **当前进度** | Phase 9 已完成，Phase 10 待开发 |

---

## 阶段总览

| 阶段 | 目标 | 产出 | 验收标准 | 状态 |
|------|------|------|---------|------|
| **Phase 0** | 项目初始化 | 目录结构/配置文件 | 项目骨架完整 | ✅ 完成 |
| **Phase 1** | 视频输入层 | 多源视频输入 | 能读取摄像头/文件/RTSP | ✅ 完成 |
| **Phase 2** | 姿态检测 | 骨骼关键点检测 | 实时显示骨骼叠加 | ✅ 完成 |
| **Phase 3** | 动作识别 | 关键动作识别 | 能识别预定义动作 | 暂缓 |
| **Phase 4** | 语音识别 | ASR转写 | 实时语音转文字 | ✅ 完成 |
| **Phase 5** | SOP分析 | 时序合规检测 | 能检测动作序列合规性 | ✅ 完成 |
| **Phase 6** | 评估引擎 | 三维度评分 | 生成评估报告 | ✅ 完成 |
| **Phase 7** | 后端API | REST + WebSocket | API文档完整可用 | ✅ 完成 |
| **Phase 8** | 前端开发 | HUD界面 | 实时监控/回放/报告页面 | ✅ 完成 |
| **Phase 9** | 系统集成 | 端到端测试 | 全流程跑通 | ✅ 完成 |
| **Phase 10** | 部署交付 | Docker部署 | 可独立运行 | 待开发 |

---

## Phase 0: 项目初始化 ✅

### 目标
搭建项目骨架，完成基础配置

### 任务清单
- [x] 创建完整目录结构
- [x] 初始化 `backend/pyproject.toml`
- [x] 初始化 `backend/requirements.txt`
- [x] 初始化 `frontend/package.json`
- [x] 创建 `backend/config/config.yaml` 基础配置
- [x] 创建 `backend/config/sop_rules.yaml` 示例规则
- [ ] 创建 `backend/config/actions.yaml` 动作定义 (暂未实现，已在sop_rules.yaml中定义)
- [x] 编写 `.gitignore`
- [x] 更新 `README.md`

### 验收标准
- [x] 项目结构完整
- [x] 能启动空白后端/前端

### 完成时间
2025-12-23

### 产出文件
```
backend/
├── pyproject.toml
├── requirements.txt
├── config/
│   ├── config.yaml
│   ├── sop_rules.yaml
│   └── actions.yaml
└── src/
    ├── __init__.py
    └── main.py

frontend/
├── package.json
├── tsconfig.json
└── vite.config.ts
```

---

## Phase 1: 视频输入层 ✅

### 目标
支持多种视频源输入

### 任务清单
- [x] 实现 `VideoSource` 抽象基类
- [x] 实现 `CameraInput` 本地摄像头输入
- [x] 实现 `FileInput` 视频文件输入
- [x] 实现 `RTSPInput` 网络流输入
- [x] 实现 `AudioSource` 音频抽象基类
- [x] 实现 `MicrophoneInput` 麦克风输入
- [x] 实现 `AudioFileInput` 音频文件输入
- [x] 编写单元测试 (25个测试全部通过)

### 完成时间
2025-12-23

### 核心文件
```
backend/src/input/
├── __init__.py
├── video_source.py      # 抽象基类
├── camera_input.py      # 摄像头输入
├── file_input.py        # 文件输入
├── rtsp_input.py        # RTSP流输入
└── audio_input.py       # 音频输入
```

### 关键接口
```python
class VideoSource(ABC):
    @abstractmethod
    def read_frame(self) -> Tuple[bool, np.ndarray]:
        """读取一帧，返回(成功标志, 图像数据)"""
        pass

    @abstractmethod
    def get_fps(self) -> float:
        """获取帧率"""
        pass

    @abstractmethod
    def release(self) -> None:
        """释放资源"""
        pass
```

### 验收标准
- [x] 能从摄像头读取视频帧
- [x] 能从视频文件读取帧
- [x] 能从RTSP流读取帧
- [x] 能从麦克风读取音频
- [x] 能从音频文件读取音频
- [x] 所有测试通过 (25/25)

---

## Phase 2: 姿态检测模块 ✅

### 目标
实时检测人体骨骼关键点

### 任务清单
- [x] 集成 MediaPipe Pose
- [x] 实现 `PoseDetector` 基类
- [x] 实现 `MediaPipePose` 具体实现
- [x] 实现关键点提取
- [x] 实现关键夹角计算（肘、膝、脊柱）
- [x] 定义标准姿态模板
- [x] 实现姿态偏差分析
- [x] 实现 `PoseAnalyzer` 姿态分析器
- [x] 编写单元测试 (43个测试全部通过)

#### 防冲击姿势检测（Brace Position）
- [x] 实现 `BracePositionDetector` 模块
- [x] 实现躯干/背部姿态判别（背部与座椅夹角检测）
- [x] 实现头部/颈部姿态判别（面向机头/机尾两种模式）
- [x] 实现上肢/手部姿态判别（双臂交叉/双手放大腿）
- [x] 实现下肢/脚部姿态判别（膝关节角度85°-95°）
- [x] 实现姿态稳定性检测算法
- [x] 定义 `BodyPartStatus` 和 `BracePositionResult` 数据结构
- [x] 编写防冲击姿势单元测试

### 完成时间
2025-12-23

### 核心文件
```
backend/src/perception/
├── pose_detector.py          # 基类、数据结构、枚举定义
├── mediapipe_pose.py         # MediaPipe实现

backend/src/analysis/
├── pose_analyzer.py          # 夹角计算/姿态分析/稳定性追踪
├── brace_position_detector.py  # 防冲击姿势检测模块
```

### 验收标准
- [x] 能检测33个人体关键点
- [x] 能计算并输出关节角度
- [x] 能判断当前姿态类型
- [x] 能检测防冲击姿势各部位合规性
- [x] 能输出姿态到位时间和稳定保持时长
- [x] 所有测试通过 (43/43)

---

## Phase 3: 动作识别模块

### 目标
识别乘务员关键操作动作

### 任务清单
- [ ] 设计动作识别网络结构 (ST-GCN)
- [ ] 准备训练数据（使用NTU RGB+D预训练）
- [ ] 定义动作类别映射
- [ ] 实现 `ActionRecognizer` 基类
- [ ] 实现 `STGCNRecognizer` 具体实现
- [ ] 实现推理Pipeline
- [ ] 编写单元测试

### 核心文件
```
backend/src/perception/
├── action_recognizer.py   # 基类
├── stgcn_recognizer.py    # ST-GCN实现

models/action/
├── stgcn.pth              # 模型权重
└── action_classes.json    # 动作类别映射
```

### 训练数据
- 使用 NTU RGB+D 数据集预训练
- 定义5-10个关键动作类别
- 后续采集真实数据微调

### 验收标准
- 能识别预定义动作
- 输出动作类型和置信度
- 输出动作开始/结束时间

---

## Phase 4: 语音识别模块 ✅

### 目标
监测通讯术语规范性

### 任务清单
- [x] 实现 `ASREngine` 基类
- [x] 实现 `ASRResult`, `ASRSegment` 数据结构
- [x] 实现 `WhisperASR` 本地语音识别 (离线模式)
- [x] 实现 `DoubaoASR` 豆包API在线识别 (在线模式)
- [x] 实现 `HybridASR` 智能切换器 (联网用API，断网用本地)
- [x] 实现 `MockWhisperASR`, `MockDoubaoASR`, `MockHybridASR` 测试用实现
- [x] 定义标准航空术语词表 (`STANDARD_TERMINOLOGY`)
- [x] 实现 `CommunicationAnalyzer` 通讯分析器
- [x] 实现术语匹配检测
- [x] 实现响应时间分析
- [x] 实现清晰度评分
- [x] 编写单元测试 (47个测试全部通过)

### 完成时间
2025-12-23

### 核心文件
```
backend/src/perception/
├── asr_engine.py          # 基类、数据结构、标准术语
├── whisper_asr.py         # Whisper本地实现 (离线)
├── doubao_asr.py          # 豆包API实现 (在线)
├── hybrid_asr.py          # 智能切换 (自动 online/offline)

backend/src/analysis/
├── communication_analyzer.py  # 术语分析、响应时间、清晰度评分
```

### ASR 模式说明
| 模式 | 引擎 | 适用场景 |
|------|------|---------|
| **在线模式** | DoubaoASR | 联网状态，高精度、低延迟 |
| **离线模式** | WhisperASR | 断网/隐私要求，本地模型 |
| **自动模式** | HybridASR | 自动检测网络，智能切换 |

### 术语检测功能
- 紧急指令检测 (brace/evacuate/fire)
- 安全检查术语 (安全带/小桌板/座椅靠背)
- 通讯确认术语 (收到/明白/确认)
- 协调术语 (准备完毕/已清空/协助)

### 环境变量配置
```bash
# 豆包API配置 (可选，不配置则使用本地Whisper)
DOUBAO_APP_ID=your_app_id
DOUBAO_ACCESS_TOKEN=your_access_token
DOUBAO_CLUSTER=volcengine_streaming_common
```

### 验收标准
- [x] 能识别中文语音转文字
- [x] 能检测标准航空术语
- [x] 能分析响应时间
- [x] 能评估通讯清晰度
- [x] 支持在线/离线智能切换
- [x] 所有测试通过 (47/47)

---

## Phase 5: SOP时序分析引擎 ✅

### 目标
检测动作序列合规性

### 任务清单
- [x] 设计SOP规则YAML格式
- [x] 实现规则加载器
- [x] 实现 `SOPAnalyzer` 核心引擎
- [x] 实现动作序列比对算法
- [x] 实现时间窗口校验
- [x] 实现 `Synchronizer` 多模态数据同步器
- [x] 编写单元测试 (63个测试全部通过)

#### 场景触发识别
- [x] 实现教员指令触发识别（ASR关键词检测："Brace"/"防冲击"等）
- [x] 实现训练系统事件触发识别（API对接）
- [x] 实现姿态突变触发检测
- [x] 记录场景触发时间戳

#### 防冲击场景时序判别
- [x] 定义 `brace_position` SOP规则（见示例）
- [x] 实现防冲击姿势完成时序判别
- [x] 实现姿态保持时长监测
- [x] 实现姿态偏移/失效检测
- [x] 输出场景级综合判定结论

### 完成时间
2025-12-23

### 核心文件
```
backend/src/analysis/
├── sop_analyzer.py           # 核心引擎
├── synchronizer.py           # 多模态同步
├── action_sequence.py        # 动作序列分析
├── scenario_trigger.py       # 场景触发识别

backend/config/
├── sop_rules.yaml            # SOP规则定义
```

### 示例SOP规则
```yaml
scenarios:
  fire_emergency:
    name: "火警处置流程"
    trigger_event: "fire_alarm"
    steps:
      - action: "press_call_button"
        time_limit: 3
      - action: "grab_extinguisher"
        time_limit: 10
    max_total_time: 30

  brace_position:
    name: "防冲击姿势"
    trigger_keywords: ["brace", "防冲击", "防冲击姿势"]
    time_limit: 5                     # 5秒内完成姿态
    min_hold_duration: 30             # 至少保持30秒
    body_parts:
      torso:
        name: "躯干与背部"
        max_angle_deviation: 10
      head:
        name: "头部与颈部"
        position: "rear_facing"
      arms:
        name: "上肢与手部"
        position: "crossed"
      legs:
        name: "下肢与脚部"
        knee_angle_min: 85
        knee_angle_max: 95
        feet_flat: true
```

### 验收标准
- [x] 能加载SOP规则
- [x] 能检测动作序列是否符合规范
- [x] 能检测时间窗口合规性
- [x] 能输出违规项列表
- [x] 能识别防冲击场景触发
- [x] 能判别防冲击姿势完成时序
- [x] 能监测姿态保持稳定性
- [x] 所有测试通过 (63/63)

### 关键接口
```python
# SOPAnalyzer - SOP合规分析
class SOPAnalyzer:
    def start_scenario(scenario_id, trigger_type, trigger_text, trigger_time) -> bool
    def record_action(action_id, action_name, timestamp, confidence) -> None
    def analyze() -> SOPAnalysisResult
    def detect_trigger(text, keywords) -> Optional[str]

# Synchronizer - 多模态数据同步
class Synchronizer:
    def add_pose(timestamp, pose_result) -> None
    def add_asr(timestamp, asr_result) -> None
    def add_action(timestamp, action_event) -> None
    def get_synced_frame(timestamp, tolerance) -> SyncedFrame

# ScenarioTriggerDetector - 场景触发检测
class ScenarioTriggerDetector:
    def register_scenario(scenario_id, keywords, events) -> None
    def check_asr(text, timestamp, confidence) -> Optional[TriggerEvent]
    def check_event(event_name, timestamp) -> Optional[TriggerEvent]
    def check_pose_change(pose_data, timestamp) -> Optional[TriggerEvent]
```

---

## Phase 6: 评估引擎 ✅

### 目标
三维度评分 + AI分析报告

### 任务清单
- [x] 实现 `Evaluator` 评估引擎
- [x] 实现 `PoseScorer` 姿态标准分
- [x] 实现 `ActionScorer` 动作时效分
- [x] 实现 `CommunicationScorer` 沟通协同分
- [x] 实现权重配置
- [x] 集成LLM生成改进建议 (MockLLM + OpenAI支持)
- [x] 实现 `ReportGenerator` 报告生成器
- [x] 实现Markdown报告导出
- [x] 编写单元测试 (65个测试全部通过)

### 完成时间
2025-12-23

### 核心文件
```
backend/src/evaluation/
├── __init__.py              # 模块导出
├── evaluator.py             # 评估引擎
├── pose_scorer.py           # 姿态评分
├── action_scorer.py         # 动作评分
├── communication_scorer.py  # 沟通评分
├── report_generator.py      # 报告生成
```

### 评分维度
| 维度 | 权重 | 评分标准 |
|------|-----|---------|
| 姿态标准分 | 30% | 关键姿态夹角偏差 |
| 动作时效分 | 40% | SOP时间窗口合规性 |
| 沟通协同分 | 30% | 通讯及时性与术语规范 |

### 关键接口
```python
# Evaluator - 综合评估引擎
class Evaluator:
    def set_weights(pose, action, communication) -> None
    def evaluate(session_id, scenario_id, pose_data, sop_result, comm_result) -> EvaluationResult

# PoseScorer - 姿态评分
class PoseScorer:
    def score(pose_data, brace_result) -> PoseScoreResult
    def score_with_history(pose_history, min_hold_duration) -> PoseScoreResult

# ActionScorer - 动作评分
class ActionScorer:
    def score(sop_result) -> ActionScoreResult

# CommunicationScorer - 沟通评分
class CommunicationScorer:
    def score(comm_result, scenario) -> CommunicationScoreResult

# ReportGenerator - 报告生成
class ReportGenerator:
    def generate(evaluation, trainee_id, trainee_name) -> TrainingReport
    def generate_suggestions(evaluation) -> List[ImprovementSuggestion]
    def export_to_markdown(report, file_path) -> bool
```

### 验收标准
- [x] 能计算三个维度的分数
- [x] 能生成总分和等级 (A/B/C/D/F)
- [x] 能生成AI改进建议
- [x] 能导出Markdown报告
- [x] 所有测试通过 (65/65)

---

## Phase 7: 后端API开发 ✅

### 目标
完善REST API + WebSocket实时推送

### 任务清单
- [x] 实现 FastAPI 主框架
- [x] 实现会话管理API (`/api/sessions`)
- [x] 实现实时监控WebSocket (`/ws/live/{id}`)
- [x] 实现录像回放API (`/api/playback`)
- [x] 实现报告查询API (`/api/reports`)
- [x] 实现配置管理API (`/api/config`)
- [x] 编写API文档 (Swagger)
- [x] 编写集成测试 (42个测试全部通过)

### 完成时间
2025-12-23

### 核心文件
```
backend/src/api/
├── __init__.py            # 模块导出
├── app.py                 # FastAPI应用工厂
├── router.py              # 主路由
├── schemas.py             # Pydantic数据模型
├── session_manager.py     # 会话生命周期管理
└── routes/
    ├── __init__.py        # 路由导出
    ├── sessions.py        # 会话CRUD
    ├── evaluation.py      # 评估与报告
    ├── playback.py        # 录像回放
    ├── config.py          # 系统配置
    └── websocket.py       # WebSocket实时监控
```

### API端点
| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | API根端点 |
| `/health` | GET | 健康检查 |
| `/api/sessions` | POST | 创建训练会话 |
| `/api/sessions` | GET | 获取会话列表 |
| `/api/sessions/{id}` | GET | 获取会话信息 |
| `/api/sessions/{id}` | DELETE | 删除会话 |
| `/api/sessions/{id}/start` | POST | 开始监测 |
| `/api/sessions/{id}/stop` | POST | 停止监测 |
| `/api/sessions/{id}/pause` | POST | 暂停监测 |
| `/api/sessions/{id}/cancel` | POST | 取消会话 |
| `/api/sessions/{id}/status` | GET | 获取监控状态 |
| `/api/ws/live/{id}` | WebSocket | 实时数据推送 |
| `/api/playback/{id}` | GET | 获取回放数据 |
| `/api/playback/{id}/frames` | GET | 获取帧数据 |
| `/api/playback/{id}/timeline` | GET | 获取时间轴 |
| `/api/playback/{id}/summary` | GET | 获取回放摘要 |
| `/api/evaluation/{id}` | GET | 获取评估结果 |
| `/api/evaluation/{id}` | POST | 执行评估 |
| `/api/reports` | GET | 获取报告列表 |
| `/api/reports/{id}` | GET | 获取报告详情 |
| `/api/config` | GET | 获取系统配置 |
| `/api/config` | PUT | 更新系统配置 |
| `/api/config/scenarios` | GET | 获取场景列表 |
| `/api/config/scenarios/{id}` | GET | 获取场景详情 |
| `/api/config/weights` | GET | 获取评分权重 |
| `/api/config/weights` | PUT | 更新评分权重 |
| `/api/config/asr-modes` | GET | 获取ASR模式列表 |
| `/api/config/asr-modes` | PUT | 设置ASR模式 |

### 关键接口
```python
# SessionManager - 会话生命周期管理
class SessionManager:
    def create_session(trainee_id, trainee_name, ...) -> SessionInfo
    def get_session(session_id) -> Optional[SessionData]
    def start_session(session_id, trigger_type) -> bool
    def stop_session(session_id, generate_report) -> bool
    def pause_session(session_id) -> bool
    def cancel_session(session_id) -> bool
    def add_frame_data(session_id, pose, action, asr, brace) -> MonitoringFrame
    def get_monitoring_status(session_id) -> Optional[MonitoringStatus]

# ConnectionManager - WebSocket连接管理
class ConnectionManager:
    async def connect(websocket, session_id) -> bool
    async def disconnect(websocket, session_id) -> None
    async def broadcast(session_id, message) -> None
```

### 验收标准
- [x] 所有API端点可用
- [x] Swagger文档完整 (/docs, /redoc)
- [x] WebSocket实时推送正常
- [x] 所有测试通过 (42/42)

---

## Phase 8: 前端开发 ✅

### 目标
实现HUD风格监控界面

### 任务清单
- [x] 搭建 Vue 3 + TypeScript + Vite 项目
- [x] 实现 HUD 主题样式 (CSS变量 + 扫描线效果)
- [x] 实现布局组件 (`HUDLayout`, `Sidebar`)
- [x] 实现状态管理 (Pinia stores: session, config, report)
- [x] 实现API服务 (Axios HTTP客户端)
- [x] 实现WebSocket服务 (实时数据推送)
- [x] 实现仪表盘页面 (`Dashboard`)
  - [x] 系统状态显示
  - [x] 快速操作按钮
  - [x] 最近报告列表
  - [x] 新建会话弹窗
- [x] 实现实时监控页面 (`LiveMonitor`)
  - [x] 视频占位符组件
  - [x] 骨骼叠加组件 (`SkeletonOverlay`)
  - [x] 实时评分面板 (`ScorePanel`)
  - [x] 动作时间轴 (`ActionTimeline`)
  - [x] 告警面板 (`AlertPanel`)
  - [x] 防冲击姿势状态
  - [x] ASR实时转写显示
- [x] 实现录像分析页面 (`PlaybackAnalysis`)
  - [x] 会话选择器
  - [x] 视频回放控制器
  - [x] 进度条 + 逐帧控制
  - [x] 时间轴事件标记
  - [x] 帧数据详情
- [x] 实现报告详情页面 (`Reports`)
  - [x] 报告列表
  - [x] ECharts雷达图 (`RadarChart`)
  - [x] 评分面板
  - [x] AI改进建议列表
- [x] 响应式适配 (移动端/平板)

### 完成时间
2025-12-23

### 核心文件
```
frontend/src/
├── views/
│   ├── Dashboard.vue          # 仪表盘页面
│   ├── LiveMonitor.vue        # 实时监控页面
│   ├── PlaybackAnalysis.vue   # 录像分析页面
│   └── Reports.vue            # 报告详情页面
├── components/
│   ├── layout/
│   │   ├── HUDLayout.vue      # 主布局 (扫描线效果)
│   │   └── Sidebar.vue        # 侧边导航栏
│   ├── monitoring/
│   │   ├── SkeletonOverlay.vue   # 骨骼叠加 (Canvas)
│   │   ├── ScorePanel.vue        # 评分面板
│   │   ├── AlertPanel.vue        # 告警面板
│   │   └── ActionTimeline.vue    # 动作时间轴
│   └── charts/
│       └── RadarChart.vue        # ECharts雷达图
├── stores/
│   ├── session.ts             # 会话状态管理
│   ├── config.ts              # 系统配置管理
│   └── report.ts              # 报告数据管理
├── services/
│   ├── api.ts                 # Axios HTTP客户端
│   └── websocket.ts           # WebSocket客户端
├── types/
│   └── api.ts                 # TypeScript接口定义
└── assets/
    └── styles/
        └── hud-theme.css      # HUD主题样式
```

### 技术栈
| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.5+ | 前端框架 |
| TypeScript | 5.8+ | 类型安全 |
| Vite | 7.3+ | 构建工具 |
| Pinia | 3.0+ | 状态管理 |
| Axios | 1.9+ | HTTP请求 |
| ECharts | 5.6+ | 图表可视化 |
| Element Plus | 2.10+ | UI组件库 |
| Vue Router | 4.5+ | 路由管理 |

### HUD样式要点
```css
:root {
  --hud-bg-dark: #0a1628;
  --hud-bg-medium: #0d1f35;
  --hud-bg-light: #132742;
  --hud-border: #00d4ff;
  --hud-border-dim: rgba(0, 212, 255, 0.3);
  --hud-glow: 0 0 10px rgba(0, 212, 255, 0.5);
  --hud-text-primary: #e6f4ff;
  --hud-success: #00ff88;
  --hud-warning: #ffcc00;
  --hud-danger: #ff4444;
  --font-cn: "Microsoft YaHei", sans-serif;
  --font-en: "Times New Roman", serif;
}

/* 扫描线动画效果 */
@keyframes scanline {
  0% { top: -100%; }
  100% { top: 100%; }
}
```

### 验收标准
- [x] HUD风格界面完成
- [x] 实时监控页面正常显示
- [x] 录像回放功能正常
- [x] 报告页面数据正确
- [x] TypeScript编译通过
- [x] 生产构建成功

---

## Phase 9: 系统集成与测试 ✅

### 目标
完成端到端集成测试

### 任务清单
- [x] 前后端联调 (Vite proxy + CORS配置)
- [x] 更新 main.py 集成 Phase 7 API
- [x] 创建集成测试脚本 (22个测试)
- [x] API响应格式统一验证
- [x] WebSocket 连接测试
- [x] 会话生命周期测试
- [x] Bug修复 (API响应结构)
- [x] 编写部署文档 (DEPLOYMENT.md)
- [x] 创建开发启动脚本 (start_dev.sh)

### 完成时间
2025-12-23

### 核心文件
```
backend/tests/
└── test_integration.py       # 22个集成测试

scripts/
├── start_dev.sh              # 开发环境启动脚本
└── test_all.sh               # 自测脚本

docs/
└── DEPLOYMENT.md             # 部署指南
```

### 集成测试覆盖
| 测试类 | 测试数 | 说明 |
|--------|--------|------|
| TestAPIIntegration | 2 | 健康检查、根端点 |
| TestSessionLifecycle | 4 | 创建、启动、停止、列表 |
| TestConfigAPI | 5 | 配置、场景、权重、ASR |
| TestPlaybackAPI | 2 | 回放数据获取 |
| TestEvaluationAPI | 2 | 评估结果 |
| TestWebSocketIntegration | 2 | WS连接、更新 |
| TestErrorHandling | 3 | 错误处理 |
| TestDataIntegrity | 2 | 数据一致性 |

### 验收标准
- [x] 22个集成测试全部通过
- [x] 前后端联调正常
- [x] WebSocket实时推送正常
- [x] 部署文档完整

---

## Phase 10: 部署与交付

### 目标
完成Docker部署和文档交付

### 任务清单
- [ ] 编写 `Dockerfile.backend`
- [ ] 编写 `Dockerfile.frontend`
- [ ] 编写 `docker-compose.yml`
- [ ] 编写部署文档
- [ ] 部署到本地服务器
- [ ] 系统演示
- [ ] 交付全部文档

### Docker配置
```
docker/
├── Dockerfile.backend
├── Dockerfile.frontend
└── docker-compose.yml
```

### 交付物清单
- [ ] 源代码
- [ ] Docker镜像
- [ ] 部署文档
- [ ] API文档
- [ ] 用户手册
- [ ] 培训材料

### 验收标准
- Docker一键部署成功
- 系统独立运行
- 文档完整

---

## 后续迭代方向

完成基础版本后，可考虑的扩展方向：

1. **多摄像头支持** - 多角度覆盖
2. **3D姿态重建** - 更精确的姿态分析
3. **表情识别** - 分析乘务员情绪状态
4. **多人检测** - 同时监测多名乘务员
5. **移动端适配** - 平板/手机查看
6. **数据分析大屏** - 培训数据统计
7. **模型自动更新** - 持续学习优化

---

**文档版本**: v1.6
**最后更新**: 2025-12-23 (Phase 0/1/2/4/5/6/7/8/9 完成，共307个测试通过，系统集成完成)

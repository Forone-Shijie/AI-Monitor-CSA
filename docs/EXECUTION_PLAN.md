# CC-SOP Monitor 项目执行计划

## 项目信息

| 项目 | 信息 |
|------|------|
| **项目名称** | 客舱乘务员姿态与操作规范监测系统 (CC-SOP Monitor) |
| **项目路径** | `/home/sjzhang/Project/AI-Monitor-CSA` |
| **开发模式** | 迭代式开发，分阶段交付 |

---

## 阶段总览

| 阶段 | 目标 | 产出 | 验收标准 |
|------|------|------|---------|
| **Phase 0** | 项目初始化 | 目录结构/配置文件 | 项目骨架完整 |
| **Phase 1** | 视频输入层 | 多源视频输入 | 能读取摄像头/文件/RTSP |
| **Phase 2** | 姿态检测 | 骨骼关键点检测 | 实时显示骨骼叠加 |
| **Phase 3** | 动作识别 | 关键动作识别 | 能识别预定义动作 |
| **Phase 4** | 语音识别 | ASR转写 | 实时语音转文字 |
| **Phase 5** | SOP分析 | 时序合规检测 | 能检测动作序列合规性 |
| **Phase 6** | 评估引擎 | 三维度评分 | 生成评估报告 |
| **Phase 7** | 后端API | REST + WebSocket | API文档完整可用 |
| **Phase 8** | 前端开发 | HUD界面 | 实时监控/回放/报告页面 |
| **Phase 9** | 系统集成 | 端到端测试 | 全流程跑通 |
| **Phase 10** | 部署交付 | Docker部署 | 可独立运行 |

---

## Phase 0: 项目初始化

### 目标
搭建项目骨架，完成基础配置

### 任务清单
- [ ] 创建完整目录结构
- [ ] 初始化 `backend/pyproject.toml`
- [ ] 初始化 `backend/requirements.txt`
- [ ] 初始化 `frontend/package.json`
- [ ] 创建 `backend/config/config.yaml` 基础配置
- [ ] 创建 `backend/config/sop_rules.yaml` 示例规则
- [ ] 创建 `backend/config/actions.yaml` 动作定义
- [ ] 编写 `.gitignore`
- [ ] 更新 `README.md`

### 验收标准
- 项目结构完整
- 能启动空白后端/前端

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

## Phase 1: 视频输入层

### 目标
支持多种视频源输入

### 任务清单
- [ ] 实现 `VideoSource` 抽象基类
- [ ] 实现 `CameraInput` 本地摄像头输入
- [ ] 实现 `FileInput` 视频文件输入
- [ ] 实现 `RTSPInput` 网络流输入
- [ ] 实现 `AudioInput` 音频输入
- [ ] 编写单元测试

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
- 能从摄像头读取视频帧
- 能从视频文件读取帧
- 能从RTSP流读取帧
- 所有测试通过

---

## Phase 2: 姿态检测模块

### 目标
实时检测人体骨骼关键点

### 任务清单
- [ ] 集成 MediaPipe Pose
- [ ] 实现 `PoseDetector` 基类
- [ ] 实现 `MediaPipePose` 具体实现
- [ ] 实现关键点提取
- [ ] 实现关键夹角计算（肘、膝、脊柱）
- [ ] 定义标准姿态模板
- [ ] 实现姿态偏差分析
- [ ] 实现 `PoseAnalyzer` 姿态分析器
- [ ] 编写单元测试

#### 防冲击姿势检测（Brace Position）
- [ ] 实现 `BracePositionDetector` 模块
- [ ] 实现躯干/背部姿态判别（背部与座椅夹角检测）
- [ ] 实现头部/颈部姿态判别（面向机头/机尾两种模式）
- [ ] 实现上肢/手部姿态判别（双臂交叉/双手放大腿）
- [ ] 实现下肢/脚部姿态判别（膝关节角度85°-95°）
- [ ] 实现姿态稳定性检测算法
- [ ] 定义 `BodyPartStatus` 和 `BracePositionResult` 数据结构
- [ ] 编写防冲击姿势单元测试

### 核心文件
```
backend/src/perception/
├── pose_detector.py          # 基类
├── mediapipe_pose.py         # MediaPipe实现

backend/src/analysis/
├── pose_analyzer.py          # 夹角计算/姿态分析
├── brace_position_detector.py  # 防冲击姿势检测模块
```

### 关键算法
- 33关键点提取
- 三角函数计算关节角度
- 姿态分类（standing/squatting/bending/brace）
- 多部位姿态综合判定
- 姿态稳定性时序分析

### 验收标准
- 视频画面实时叠加骨骼显示
- 能计算并显示关节角度
- 能判断当前姿态类型
- **能检测防冲击姿势各部位合规性**
- **能输出姿态到位时间和稳定保持时长**

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

## Phase 4: 语音识别模块

### 目标
监测通讯术语规范性

### 任务清单
- [ ] 集成 Whisper ASR
- [ ] 实现 `ASREngine` 基类
- [ ] 实现 `WhisperASR` 具体实现
- [ ] 实现音频流处理
- [ ] 实现术语规范性检测
- [ ] 实现 `CommunicationAnalyzer` 通讯分析器
- [ ] 编写单元测试

### 核心文件
```
backend/src/perception/
├── asr_engine.py          # 基类
├── whisper_asr.py         # Whisper实现

backend/src/analysis/
├── communication_analyzer.py  # 术语分析
```

### 术语检测
- 定义标准术语词表
- 检测关键术语出现
- 分析响应时间

### 验收标准
- 能实时识别中文语音
- 能检测关键术语
- 能计算响应时间

---

## Phase 5: SOP时序分析引擎

### 目标
检测动作序列合规性

### 任务清单
- [ ] 设计SOP规则YAML格式
- [ ] 实现规则加载器
- [ ] 实现 `SOPAnalyzer` 核心引擎
- [ ] 实现动作序列比对算法
- [ ] 实现时间窗口校验
- [ ] 实现 `Synchronizer` 多模态数据同步器
- [ ] 编写单元测试

#### 场景触发识别
- [ ] 实现教员指令触发识别（ASR关键词检测："Brace"/"防冲击"等）
- [ ] 实现训练系统事件触发识别（API对接）
- [ ] 实现姿态突变触发检测
- [ ] 记录场景触发时间戳

#### 防冲击场景时序判别
- [ ] 定义 `brace_position` SOP规则（见示例）
- [ ] 实现防冲击姿势完成时序判别
- [ ] 实现姿态保持时长监测
- [ ] 实现姿态偏移/失效检测
- [ ] 输出场景级综合判定结论

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
- 能加载SOP规则
- 能检测动作序列是否符合规范
- 能检测时间窗口合规性
- 能输出违规项列表
- **能识别防冲击场景触发**
- **能判别防冲击姿势完成时序**
- **能监测姿态保持稳定性**

---

## Phase 6: 评估引擎

### 目标
三维度评分 + AI分析报告

### 任务清单
- [ ] 实现 `Evaluator` 评估引擎
- [ ] 实现 `PoseScorer` 姿态标准分
- [ ] 实现 `ActionScorer` 动作时效分
- [ ] 实现 `CommunicationScorer` 沟通协同分
- [ ] 实现权重配置
- [ ] 集成LLM生成改进建议
- [ ] 实现 `ReportGenerator` 报告生成器
- [ ] 实现PDF报告导出
- [ ] 编写单元测试

### 核心文件
```
backend/src/evaluation/
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

### 验收标准
- 能计算三个维度的分数
- 能生成总分
- 能生成AI改进建议
- 能导出PDF报告

---

## Phase 7: 后端API开发

### 目标
完善REST API + WebSocket实时推送

### 任务清单
- [ ] 实现 FastAPI 主框架
- [ ] 实现会话管理API (`/api/sessions`)
- [ ] 实现实时监控WebSocket (`/ws/live/{id}`)
- [ ] 实现录像回放API (`/api/playback`)
- [ ] 实现报告查询API (`/api/reports`)
- [ ] 实现配置管理API (`/api/config`)
- [ ] 编写API文档 (Swagger)
- [ ] 编写集成测试

### 核心文件
```
backend/src/api/
├── router.py              # 主路由
├── session.py             # 会话管理
├── monitoring.py          # 实时监控
├── playback.py            # 录像回放
├── reports.py             # 报告
├── websocket.py           # WebSocket
```

### API端点
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/sessions` | POST | 创建训练会话 |
| `/api/sessions/{id}` | GET | 获取会话信息 |
| `/api/sessions/{id}/start` | POST | 开始监测 |
| `/api/sessions/{id}/stop` | POST | 停止监测 |
| `/ws/live/{id}` | WebSocket | 实时数据推送 |
| `/api/playback/{id}` | GET | 获取录像数据 |
| `/api/reports/{id}` | GET | 获取评估报告 |

### 验收标准
- 所有API端点可用
- Swagger文档完整
- WebSocket实时推送正常
- 所有测试通过

---

## Phase 8: 前端开发

### 目标
实现HUD风格监控界面

### 任务清单
- [ ] 搭建 React + TypeScript 项目
- [ ] 实现 HUD 主题样式
- [ ] 实现布局组件 (`HUDFrame`, `Sidebar`)
- [ ] 实现仪表盘页面 (`Dashboard`)
- [ ] 实现实时监控页面 (`LiveMonitor`)
  - [ ] 视频播放器组件
  - [ ] 骨骼叠加组件
  - [ ] 实时评分面板
  - [ ] 动作时间轴
  - [ ] 告警面板
- [ ] 实现录像分析页面 (`PlaybackAnalysis`)
  - [ ] 时间轴控制器
  - [ ] 标注工具
- [ ] 实现报告详情页面 (`Reports`)
  - [ ] 雷达图组件
  - [ ] 改进建议列表
- [ ] WebSocket实时数据对接
- [ ] 响应式适配

### 核心文件
```
frontend/src/
├── pages/
│   ├── Dashboard.tsx
│   ├── LiveMonitor.tsx
│   ├── PlaybackAnalysis.tsx
│   └── Reports.tsx
├── components/
│   ├── layout/
│   ├── monitoring/
│   ├── playback/
│   └── reports/
├── styles/
│   ├── hud-theme.css
│   └── variables.css
```

### HUD样式要点
```css
:root {
  --hud-bg: rgba(10, 22, 40, 0.85);
  --hud-border: #00d4ff;
  --hud-glow: 0 0 10px rgba(0, 212, 255, 0.5);
  --font-cn: "Microsoft YaHei", sans-serif;
  --font-en: "Times New Roman", serif;
}
```

### 验收标准
- HUD风格界面完成
- 实时监控页面正常显示
- 录像回放功能正常
- 报告页面数据正确

---

## Phase 9: 系统集成与测试

### 目标
完成端到端集成测试

### 任务清单
- [ ] 前后端联调
- [ ] 端到端测试
- [ ] 性能测试
- [ ] 压力测试
- [ ] Bug修复
- [ ] 性能优化
- [ ] 编写部署文档

### 测试用例
1. **完整流程测试**: 从视频输入到报告生成
2. **实时性测试**: 延迟 < 500ms
3. **准确性测试**: 动作识别准确率 > 80%
4. **稳定性测试**: 连续运行24小时无崩溃

### 验收标准
- 全流程跑通
- 性能指标达标
- 无严重Bug

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

**文档版本**: v1.1
**最后更新**: 2025-12-23

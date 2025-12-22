# CC-SOP Monitor 开发指南

## 1. 开发环境搭建

### 1.1 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Ubuntu 20.04+ / Windows 10+ / macOS 12+ |
| Python | >= 3.10 |
| Node.js | >= 18 |
| PostgreSQL | >= 14 |
| Redis | >= 6 |
| CUDA | >= 11.8 (可选，GPU加速) |

### 1.2 Python环境配置

```bash
# 创建虚拟环境
cd AI-Monitor-CSA/backend
python -m venv venv

# 激活虚拟环境
# Linux/macOS:
source venv/bin/activate
# Windows:
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 1.3 Node.js环境配置

```bash
# 进入前端目录
cd AI-Monitor-CSA/frontend

# 安装依赖
npm install

# 或使用 pnpm (推荐)
pnpm install
```

### 1.4 数据库配置

```bash
# PostgreSQL
sudo -u postgres createdb cc_sop_monitor
sudo -u postgres psql -c "CREATE USER cc_admin WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE cc_sop_monitor TO cc_admin;"

# Redis (通常默认配置即可)
redis-server
```

### 1.5 模型下载

```bash
# 运行模型下载脚本
bash scripts/download_models.sh
```

---

## 2. 项目配置

### 2.1 后端配置

主配置文件: `backend/config/config.yaml`

```yaml
# 系统配置
system:
  name: "CC-SOP Monitor"
  language: "zh"
  log_level: "INFO"
  debug: true

# 数据库配置
database:
  host: "localhost"
  port: 5432
  name: "cc_sop_monitor"
  user: "cc_admin"
  password: "your_password"

# Redis配置
redis:
  host: "localhost"
  port: 6379
  db: 0

# ASR配置
asr:
  engine: "whisper"
  model: "small"
  language: "zh"
  device: "cuda"  # 或 "cpu"

# 姿态检测配置
pose:
  engine: "mediapipe"
  confidence_threshold: 0.5
  tracking_confidence: 0.5

# 动作识别配置
action:
  engine: "stgcn"
  model_path: "models/action/stgcn.pth"
  confidence_threshold: 0.6
  window_size: 30  # 帧数

# 评估配置
evaluation:
  pose_weight: 0.3
  action_weight: 0.4
  communication_weight: 0.3
  llm_model: "qwen2.5:7b"
  llm_base_url: "http://localhost:11434"

# 服务器配置
server:
  host: "0.0.0.0"
  port: 8000
  workers: 4
```

### 2.2 SOP规则配置

SOP规则文件: `backend/config/sop_rules.yaml`

```yaml
# SOP场景定义
scenarios:
  # 火警处置流程
  fire_emergency:
    name: "火警处置流程"
    name_en: "Fire Emergency Procedure"
    trigger_event: "fire_alarm"
    steps:
      - step_id: 1
        action: "ACT_001"
        action_name: "按压呼叫按钮"
        time_limit: 3
        required: true
        description: "立即通知驾驶舱"
      - step_id: 2
        action: "ACT_002"
        action_name: "提起灭火器"
        time_limit: 10
        required: true
        description: "取出灭火器准备灭火"
      - step_id: 3
        action: "ACT_003"
        action_name: "佩戴防烟面罩"
        time_limit: 15
        required: true
        description: "保护呼吸道"
    max_total_time: 30
    priority: "high"

  # 应急撤离流程
  emergency_evacuation:
    name: "应急撤离流程"
    name_en: "Emergency Evacuation Procedure"
    trigger_event: "evacuation_command"
    steps:
      - step_id: 1
        action: "ACT_004"
        action_name: "打开应急门"
        time_limit: 5
        required: true
      - step_id: 2
        action: "ACT_006"
        action_name: "指挥撤离"
        time_limit: null  # 持续进行
        required: true
    max_total_time: 90
    priority: "critical"

# 动作定义
actions:
  ACT_001:
    name: "按压呼叫按钮"
    name_en: "Press Call Button"
    category: "communication"
  ACT_002:
    name: "提起灭火器"
    name_en: "Grab Fire Extinguisher"
    category: "safety_equipment"
  ACT_003:
    name: "佩戴防烟面罩"
    name_en: "Put on Smoke Hood"
    category: "safety_equipment"
  ACT_004:
    name: "打开应急门"
    name_en: "Open Emergency Exit"
    category: "evacuation"
  ACT_005:
    name: "安全带检查"
    name_en: "Seatbelt Check"
    category: "inspection"
  ACT_006:
    name: "指挥撤离"
    name_en: "Direct Evacuation"
    category: "evacuation"
```

---

## 3. 开发规范

### 3.1 代码风格

#### Python
- 遵循 PEP 8 规范
- 使用 Black 进行代码格式化
- 使用 isort 进行 import 排序
- 使用 mypy 进行类型检查

```bash
# 格式化代码
black backend/src
isort backend/src

# 类型检查
mypy backend/src
```

#### TypeScript/React
- 遵循 ESLint + Prettier 规范
- 使用函数式组件 + Hooks
- 使用 TypeScript 严格模式

```bash
# 格式化代码
npm run lint
npm run format
```

### 3.2 Git 提交规范

使用 Conventional Commits 格式:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 类型**:
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

**示例**:
```
feat(pose): 添加MediaPipe姿态检测模块

- 实现33个关键点检测
- 添加关节角度计算
- 支持标准姿态比对

Closes #12
```

### 3.3 分支管理

```
main          # 生产分支
├── develop   # 开发分支
│   ├── feature/xxx   # 功能分支
│   ├── fix/xxx       # 修复分支
│   └── refactor/xxx  # 重构分支
└── release/x.x.x     # 发布分支
```

---

## 4. 模块开发指南

### 4.1 添加新的视频输入源

1. 创建新文件 `backend/src/input/new_input.py`
2. 继承 `VideoSource` 基类
3. 实现必要的抽象方法

```python
from abc import ABC, abstractmethod
from typing import Tuple
import numpy as np

class VideoSource(ABC):
    """视频源抽象基类"""

    @abstractmethod
    def read_frame(self) -> Tuple[bool, np.ndarray]:
        """读取一帧"""
        pass

    @abstractmethod
    def get_fps(self) -> float:
        """获取帧率"""
        pass

    @abstractmethod
    def get_frame_size(self) -> Tuple[int, int]:
        """获取帧尺寸 (width, height)"""
        pass

    @abstractmethod
    def release(self) -> None:
        """释放资源"""
        pass

    @abstractmethod
    def is_opened(self) -> bool:
        """检查是否打开"""
        pass


# 示例: 新增一个自定义输入源
class NewVideoInput(VideoSource):
    def __init__(self, config: dict):
        self.config = config
        # 初始化逻辑

    def read_frame(self) -> Tuple[bool, np.ndarray]:
        # 实现帧读取
        pass

    def get_fps(self) -> float:
        return 30.0

    def get_frame_size(self) -> Tuple[int, int]:
        return (1920, 1080)

    def release(self) -> None:
        # 释放资源
        pass

    def is_opened(self) -> bool:
        return True
```

### 4.2 添加新的动作类型

1. 在 `config/sop_rules.yaml` 中添加动作定义
2. 准备训练数据并标注
3. 重新训练或微调动作识别模型
4. 更新动作识别器的类别映射

```yaml
# config/sop_rules.yaml
actions:
  ACT_NEW:
    name: "新动作名称"
    name_en: "New Action Name"
    category: "category_name"
```

### 4.3 添加新的SOP场景

1. 在 `config/sop_rules.yaml` 中定义新场景
2. 定义触发事件和步骤序列
3. 设置时间限制和优先级

```yaml
scenarios:
  new_scenario:
    name: "新场景名称"
    trigger_event: "trigger_event_name"
    steps:
      - step_id: 1
        action: "ACT_XXX"
        time_limit: 5
        required: true
    max_total_time: 60
    priority: "medium"
```

---

## 5. 测试指南

### 5.1 后端测试

```bash
# 运行所有测试
cd backend
pytest

# 运行特定测试
pytest tests/test_pose_detector.py

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 5.2 前端测试

```bash
# 运行单元测试
cd frontend
npm run test

# 运行端到端测试
npm run test:e2e
```

### 5.3 集成测试

```bash
# 启动完整环境
docker-compose up -d

# 运行集成测试
pytest tests/integration/
```

---

## 6. 调试技巧

### 6.1 后端调试

```python
# 使用 logging 模块
import logging
logger = logging.getLogger(__name__)
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
```

### 6.2 可视化调试

```python
import cv2

# 在视频帧上绘制骨骼
def draw_pose(frame, keypoints):
    for kp in keypoints:
        cv2.circle(frame, (int(kp.x), int(kp.y)), 5, (0, 255, 0), -1)
    return frame

# 显示调试窗口
cv2.imshow("Debug", frame)
cv2.waitKey(1)
```

### 6.3 性能分析

```python
import cProfile
import pstats

# 使用 cProfile 分析
profiler = cProfile.Profile()
profiler.enable()

# 运行代码
result = some_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

---

## 7. API开发

### 7.1 添加新的API端点

```python
# backend/src/api/new_endpoint.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/new", tags=["New Feature"])

class NewRequest(BaseModel):
    param1: str
    param2: int

class NewResponse(BaseModel):
    result: str
    status: str

@router.post("/action", response_model=NewResponse)
async def new_action(request: NewRequest):
    """
    新功能端点

    - **param1**: 参数1说明
    - **param2**: 参数2说明
    """
    try:
        # 业务逻辑
        result = process(request.param1, request.param2)
        return NewResponse(result=result, status="success")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 7.2 WebSocket实时推送

```python
# backend/src/api/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/live/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # 处理接收到的数据
            await manager.broadcast({"session_id": session_id, "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

---

## 8. 部署说明

### 8.1 Docker部署

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 8.2 手动部署

```bash
# 后端
cd backend
gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.main:app --bind 0.0.0.0:8000

# 前端
cd frontend
npm run build
# 使用 nginx 或其他服务器托管 dist 目录
```

---

## 9. 常见问题

### Q1: MediaPipe初始化失败
**A**: 确保安装了正确版本的 mediapipe，并检查是否有足够的系统权限。

### Q2: Whisper模型加载慢
**A**: 首次加载会下载模型，后续会使用缓存。可以预先运行下载脚本。

### Q3: GPU内存不足
**A**: 减小batch size，或使用更小的模型（如 whisper-small 替代 whisper-medium）。

### Q4: WebSocket连接断开
**A**: 检查网络连接，增加心跳检测机制，或调整超时时间。

---

**文档版本**: v1.0
**最后更新**: 2024-12-22

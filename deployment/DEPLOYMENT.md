# CC-SOP Monitor 部署指南

本文档提供从零开始部署 CC-SOP Monitor 的完整步骤。

---

## 目录

1. [系统要求](#1-系统要求)
2. [通用安装步骤](#2-通用安装步骤)
3. [RTX 50 系列 (Blackwell) 专用安装](#3-rtx-50-系列-blackwell-专用安装)
4. [前端安装](#4-前端安装)
5. [验证安装](#5-验证安装)
6. [常见问题](#6-常见问题)

---

## 1. 系统要求

### 1.1 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| GPU | RTX 2060 (4GB VRAM) | RTX 3090 (24GB) / RTX 4070 (8GB) |
| CPU | 4核心 | 8核心+ |
| 内存 | 16GB | 32GB |
| 存储 | 20GB SSD | 50GB+ SSD |

### 1.2 GPU 架构兼容性

| 架构 | GPU 系列 | CUDA 版本 | 安装方式 |
|------|----------|-----------|----------|
| Turing | RTX 20xx | 12.1+ | 标准安装 |
| Ampere | RTX 30xx | 12.1+ | 标准安装 |
| Ada Lovelace | RTX 40xx | 12.1+ | 标准安装 |
| **Blackwell** | **RTX 50xx** | **12.8+** | **[特殊安装](#3-rtx-50-系列-blackwell-专用安装)** |

### 1.3 软件要求

- **操作系统**: Ubuntu 20.04+ / Windows 11 (WSL2)
- **Python**: 3.10 (必须)
- **Node.js**: 18+ (前端)
- **GCC**: 11.x-13.x (不支持 GCC 14+)
- **CUDA Driver**: 550+ (RTX 50系列需要 560+)

---

## 2. 通用安装步骤

> 适用于 **RTX 20/30/40 系列**显卡。RTX 50 系列请直接跳转到 [第3节](#3-rtx-50-系列-blackwell-专用安装)。

### 2.1 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y build-essential git curl wget \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev \
    libffi-dev libssl-dev

# 检查 GCC 版本 (必须 < 14.0)
gcc --version
```

### 2.2 安装 Miniconda

```bash
# 下载安装
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3

# 初始化
~/miniconda3/bin/conda init bash
source ~/.bashrc
```

### 2.3 创建 Conda 环境

```bash
conda create -n cc-sop python=3.10 -y
conda activate cc-sop
```

### 2.4 克隆项目

```bash
git clone https://github.com/your-org/AI-Monitor-CSA.git
cd AI-Monitor-CSA
```

### 2.5 运行安装脚本

```bash
chmod +x scripts/install_deps.sh
./scripts/install_deps.sh
```

安装脚本会自动完成以下工作：
- 安装 CUDA Toolkit 12.1
- 安装 PyTorch 2.1.0 + CUDA 12.1
- 安装 mmcv 2.1.0 (带 CUDA 扩展)
- 安装 mmpose 1.3.1 + mmdet 3.2.0
- 锁定 NumPy 1.24.4 和 OpenCV 4.8.1.78

### 2.6 下载模型

```bash
chmod +x scripts/download_models.sh
./scripts/download_models.sh
```

---

## 3. RTX 50 系列 (Blackwell) 专用安装

> **适用于**: RTX 5070 / 5080 / 5090

### 3.1 为什么需要特殊处理?

RTX 50 系列使用 NVIDIA Blackwell 架构，计算能力为 **sm_120**。截至 2026 年初：

| 差异点 | 标准安装 | RTX 50 系列 |
|--------|----------|-------------|
| PyTorch | 2.1.0 stable | **nightly (cu128)** |
| CUDA Toolkit | 12.1 | **12.8** |
| mmcv | 预编译包 | **从源码编译** |
| CUDA Arch | 8.0/8.6/9.0 | **8.0/8.6/9.0/12.0** |

### 3.2 前置检查

#### 检查 NVIDIA 驱动

```bash
nvidia-smi
```

输出应显示：
- Driver Version: **560.xx+**
- CUDA Version: **12.8**
- GPU: NVIDIA GeForce RTX 5070/5080/5090

#### 检查 GCC 版本

```bash
gcc --version
```

**要求**: GCC 版本 < 14.0。如果版本过高：

```bash
# 安装 GCC 11
sudo apt install gcc-11 g++-11

# 验证
gcc-11 --version
```

### 3.3 安装方法

#### 方法 A: 使用自动安装脚本 (推荐)

**从零开始安装：**

```bash
# 1. 创建并激活环境
conda create -n cc-sop python=3.10 -y
conda activate cc-sop

# 2. 克隆项目
git clone https://github.com/your-org/AI-Monitor-CSA.git
cd AI-Monitor-CSA

# 3. 运行 RTX 50 专用脚本
chmod +x scripts/install_rtx50.sh
./scripts/install_rtx50.sh
```

**已安装标准版本后升级：**

```bash
conda activate cc-sop
./scripts/fix_cuda_blackwell.sh
```

#### 方法 B: 手动安装 (详细步骤)

以下是完整的手动安装步骤。

##### Step 1: 创建 Conda 环境

```bash
conda create -n cc-sop python=3.10 -y
conda activate cc-sop
```

##### Step 2: 安装 NumPy 1.x

**重要**: 必须在 PyTorch 之前安装，防止 PyTorch 拉取 NumPy 2.x

```bash
pip install "numpy>=1.24.0,<2.0.0"
```

##### Step 3: 安装 PyTorch nightly + CUDA 12.8

```bash
pip install --pre torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/nightly/cu128
```

验证：
```bash
python -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA: {torch.version.cuda}')
print(f'GPU: {torch.cuda.get_device_name(0)}')
cap = torch.cuda.get_device_capability(0)
print(f'Compute Capability: {cap[0]}.{cap[1]} (sm_{cap[0]}{cap[1]})')
"
```

##### Step 4: 安装 CUDA Toolkit 12.8 (nvcc)

```bash
conda install -y -c conda-forge \
    cuda-nvcc=12.8 \
    cuda-cudart-dev \
    cuda-libraries-dev \
    ninja
```

**关键**: 设置环境变量让编译器找到 CUDA 头文件：

```bash
export CUDA_HOME=$CONDA_PREFIX
export PATH=$CONDA_PREFIX/bin:$PATH
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
export CPLUS_INCLUDE_PATH=$CONDA_PREFIX/include:$CPLUS_INCLUDE_PATH
export C_INCLUDE_PATH=$CONDA_PREFIX/include:$C_INCLUDE_PATH
export LIBRARY_PATH=$CONDA_PREFIX/lib:$LIBRARY_PATH
```

验证 nvcc：
```bash
nvcc --version
# 应显示 cuda_12.8.x
```

##### Step 5: 安装 OpenCV 和其他依赖

```bash
pip install opencv-python==4.8.1.78
pip install openmim mmengine mmdet
pip install mmpose --no-deps
pip install xtcocotools munkres json_tricks scipy matplotlib
```

##### Step 6: 从源码编译 mmcv

```bash
# 进入临时目录
cd /tmp
rm -rf mmcv

# 克隆 mmcv 源码
git clone --depth 1 -b v2.1.0 https://github.com/open-mmlab/mmcv.git
cd mmcv

# 设置编译环境变量
export CC=/usr/bin/gcc    # 或 gcc-11
export CXX=/usr/bin/g++   # 或 g++-11
export MMCV_WITH_OPS=1
export FORCE_CUDA=1
export TORCH_CUDA_ARCH_LIST="8.0;8.6;9.0;12.0"  # 包含 sm_120

# 确保 CUDA 路径正确
export CUDA_HOME=$CONDA_PREFIX
export CPLUS_INCLUDE_PATH=$CONDA_PREFIX/include:$CPLUS_INCLUDE_PATH
export C_INCLUDE_PATH=$CONDA_PREFIX/include:$C_INCLUDE_PATH

# 卸载旧版本
pip uninstall -y mmcv 2>/dev/null || true

# 编译安装 (需要 15-30 分钟)
python setup.py develop
```

##### Step 7: 锁定关键版本

```bash
# 确保 NumPy 1.x (编译过程可能升级它)
pip install numpy==1.24.4 --force-reinstall

# 确保 OpenCV 兼容
pip install opencv-python==4.8.1.78 --force-reinstall

# 锁定 setuptools
pip install "setuptools==69.5.1" --force-reinstall
```

##### Step 8: 安装项目依赖

```bash
cd /path/to/AI-Monitor-CSA/backend
pip install -r requirements.txt
```

### 3.4 环境变量持久化

将以下内容添加到 `~/.bashrc` 或 `~/.zshrc`：

```bash
# CC-SOP CUDA 环境变量 (RTX 50 系列)
ccsop_activate() {
    conda activate cc-sop
    export CUDA_HOME=$CONDA_PREFIX
    export PATH=$CONDA_PREFIX/bin:$PATH
    export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
    export CPLUS_INCLUDE_PATH=$CONDA_PREFIX/include:$CPLUS_INCLUDE_PATH
    export C_INCLUDE_PATH=$CONDA_PREFIX/include:$C_INCLUDE_PATH
    export LIBRARY_PATH=$CONDA_PREFIX/lib:$LIBRARY_PATH
}
```

使用时：
```bash
source ~/.bashrc
ccsop_activate
```

---

## 4. 前端安装

```bash
cd frontend
npm install   # 或 pnpm install
npm run dev   # 开发服务器启动在 http://localhost:5173
```

---

## 5. 验证安装

### 5.1 后端验证

```bash
cd backend

# 运行测试
pytest tests/test_pose_detector.py -v

# 启动服务
python -m src.main
```

### 5.2 验证 GPU 加速

```bash
python << 'EOF'
import warnings
warnings.filterwarnings('ignore')

print("=" * 50)
print("CC-SOP Monitor 环境验证")
print("=" * 50)

# 1. NumPy
import numpy
print(f"\n[1/6] NumPy: {numpy.__version__}")

# 2. PyTorch
import torch
print(f"[2/6] PyTorch: {torch.__version__}")
print(f"      CUDA: {torch.version.cuda}")
if torch.cuda.is_available():
    cap = torch.cuda.get_device_capability(0)
    print(f"      GPU: {torch.cuda.get_device_name(0)}")
    print(f"      Compute: sm_{cap[0]}{cap[1]}")
else:
    print("      GPU: 不可用 (仅 CPU)")

# 3. CUDA 计算测试
if torch.cuda.is_available():
    x = torch.rand(1000, 1000).cuda()
    y = torch.matmul(x, x)
    print(f"[3/6] CUDA 计算: 通过")
else:
    print(f"[3/6] CUDA 计算: 跳过")

# 4. OpenCV
import cv2
print(f"[4/6] OpenCV: {cv2.__version__}")

# 5. mmcv
import mmcv
try:
    from mmcv.ops import MultiScaleDeformableAttention
    print(f"[5/6] mmcv: {mmcv.__version__} (CUDA ops: OK)")
except ImportError:
    print(f"[5/6] mmcv: {mmcv.__version__} (CUDA ops: 不可用)")

# 6. MMPose
from mmpose.apis import MMPoseInferencer
print(f"[6/6] MMPose: OK")

print("\n" + "=" * 50)
print("验证完成!")
print("=" * 50)
EOF
```

### 5.3 RTX 50 系列性能参考

| 场景 | FPS | GPU 使用率 | VRAM |
|------|-----|------------|------|
| 单人姿态检测 | 60+ | ~30% | ~2GB |
| 3人姿态检测 | 45+ | ~50% | ~3GB |
| 5人姿态检测 | 35+ | ~70% | ~4GB |

---

## 6. 常见问题

### Q1: `cuda_runtime_api.h: No such file or directory`

**原因**: conda 安装的 CUDA toolkit 头文件路径未添加到编译器搜索路径

**解决方案**:
```bash
# 检查头文件是否存在
ls $CONDA_PREFIX/include/cuda_runtime_api.h

# 设置环境变量
export CUDA_HOME=$CONDA_PREFIX
export CPLUS_INCLUDE_PATH=$CONDA_PREFIX/include:$CPLUS_INCLUDE_PATH
export C_INCLUDE_PATH=$CONDA_PREFIX/include:$C_INCLUDE_PATH
export LIBRARY_PATH=$CONDA_PREFIX/lib:$LIBRARY_PATH

# 然后重新编译 mmcv
```

### Q2: `numpy.core.multiarray failed to import` / `_ARRAY_API not found`

**原因**: NumPy 2.x 与 OpenCV/mmcv 的 C 扩展不兼容

**解决方案**:
```bash
pip install "numpy>=1.24.0,<2.0.0" --force-reinstall
pip install opencv-python==4.8.1.78 --force-reinstall
```

### Q3: `No module named 'mmcv._ext'`

**原因**: mmcv 未正确编译 CUDA 扩展

**解决方案**: 从源码重新编译 mmcv
```bash
pip uninstall mmcv -y
export MMCV_WITH_OPS=1
export FORCE_CUDA=1
pip install mmcv==2.1.0 --no-binary mmcv
```

### Q4: RTX 50 系列 `CUDA error: no kernel image is available for execution`

**原因**: PyTorch/mmcv 不支持 sm_120 架构

**解决方案**: 使用 RTX 50 专用安装脚本
```bash
./scripts/fix_cuda_blackwell.sh
# 或
./scripts/install_rtx50.sh
```

### Q5: GCC 版本过高导致编译失败

**错误信息**: `#error -- unsupported GNU version! gcc versions later than 13 are not supported!`

**解决方案**:
```bash
# 安装 GCC 11
sudo apt install gcc-11 g++-11

# 编译时指定
export CC=/usr/bin/gcc-11
export CXX=/usr/bin/g++-11
```

### Q6: mmcv 编译卡住或内存不足

**解决方案**:
```bash
# 清理缓存重新编译
cd /tmp/mmcv
rm -rf build/ mmcv/*.so mmcv/ops/csrc/*.o

# 减少并行编译数 (降低内存使用)
MAX_JOBS=2 python setup.py develop
```

### Q7: `pkg_resources` 相关错误

**原因**: setuptools 版本过高

**解决方案**:
```bash
pip install "setuptools==69.5.1" --force-reinstall
```

---

## 联系支持

如遇其他问题，请提交 Issue: https://github.com/your-org/AI-Monitor-CSA/issues

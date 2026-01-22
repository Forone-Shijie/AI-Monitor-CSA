# RTX 50系列 (Blackwell架构) 部署指南

本文档详细说明如何在配备 RTX 5070/5080/5090 等 Blackwell 架构显卡的设备上部署 CC-SOP Monitor 系统。

---

## 问题背景

NVIDIA RTX 50系列显卡采用全新的 **Blackwell 架构**，计算能力为 **sm_120**。这带来了以下兼容性问题：

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| PyTorch 不支持 sm_120 | Stable 版本只支持到 sm_90 | 使用 nightly 版本 |
| mmcv 预编译包不支持 | 预编译仅包含 sm_70-90 | 从源码编译 |
| CUDA toolkit 版本 | Blackwell 需要 CUDA 12.8+ | conda 安装 nvcc 12.8 |
| GCC 版本限制 | nvcc 12.8 要求 GCC < 14 | 使用系统 GCC 11 |

---

## 环境要求

### 硬件
- **GPU**: NVIDIA RTX 5070 / 5080 / 5090
- **显存**: 8GB+ (推荐 12GB+)
- **内存**: 16GB+

### 软件
- **操作系统**: Ubuntu 22.04+ 或 Windows 11 (WSL2)
- **驱动**: NVIDIA Driver 550+
- **Python**: 3.10+
- **Conda/Miniconda**: 推荐使用 conda 管理环境

---

## 快速部署

### 一键安装脚本

```bash
# 确保在项目根目录
cd AI-Monitor-CSA

# 运行 Blackwell 兼容性修复脚本
bash scripts/fix_cuda_blackwell.sh
```

脚本会自动完成所有配置，约需 15-20 分钟。

---

## 手动安装步骤

如果一键脚本失败，可按以下步骤手动安装：

### 步骤 1: 创建 Conda 环境

```bash
conda create -n cc-sop python=3.10 -y
conda activate cc-sop
```

### 步骤 2: 安装 PyTorch Nightly (CUDA 12.8)

```bash
# 卸载已有的 PyTorch
pip uninstall -y torch torchvision torchaudio

# 安装 nightly 版本
pip install --pre torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/nightly/cu128
```

**验证安装：**
```python
import torch
print(f"PyTorch: {torch.__version__}")
print(f"CUDA: {torch.version.cuda}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
# 应显示 sm_120 或 12.0 计算能力
```

### 步骤 3: 安装 CUDA Toolkit 12.8

```bash
conda install -y -c conda-forge \
    cuda-nvcc=12.8.93 \
    cuda-cudart-dev \
    cuda-libraries-dev \
    ninja
```

**验证安装：**
```bash
nvcc --version
# 应显示 Cuda compilation tools, release 12.8
```

### 步骤 4: 安装 MM 系列基础依赖

```bash
pip install openmim mmengine mmdet
pip install mmpose --no-deps
pip install xtcocotools munkres json_tricks
```

### 步骤 5: 从源码编译 mmcv

这是最关键的一步，需要从源码编译以支持 sm_120。

```bash
# 克隆 mmcv 源码
cd /tmp
rm -rf mmcv
git clone --depth 1 -b v2.1.0 https://github.com/open-mmlab/mmcv.git
cd mmcv

# 设置编译环境变量
export CC=/usr/bin/gcc
export CXX=/usr/bin/g++
export MMCV_WITH_OPS=1
export FORCE_CUDA=1
export TORCH_CUDA_ARCH_LIST="8.0;8.6;9.0;12.0"

# 卸载已有 mmcv
pip uninstall -y mmcv

# 编译安装
python setup.py develop
python setup.py build_ext --inplace
```

**编译说明：**
- `TORCH_CUDA_ARCH_LIST` 包含 `12.0` 即可支持 Blackwell (sm_120)
- 编译过程约需 10-15 分钟
- 如果遇到 GCC 版本错误，确保使用系统自带的 GCC 11

**验证安装：**
```python
from mmcv.ops import MultiScaleDeformableAttention
print("mmcv.ops 加载成功!")
```

### 步骤 6: 验证完整环境

```python
import warnings
warnings.filterwarnings('ignore')

print("=== 环境验证 ===")

# 1. PyTorch
import torch
print(f"PyTorch: {torch.__version__}")
print(f"CUDA: {torch.version.cuda}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    cap = torch.cuda.get_device_capability(0)
    print(f"计算能力: sm_{cap[0]}{cap[1]}")

# 2. mmcv
from mmcv.ops import MultiScaleDeformableAttention
print("mmcv: OK")

# 3. MMPose
from mmpose.apis import MMPoseInferencer
print("MMPose: OK")

print("\n所有检查通过!")
```

---

## 常见问题

### Q1: 编译 mmcv 时报 "unsupported GNU version"

**原因**: nvcc 12.8 要求 GCC < 14.0

**解决方案**:
```bash
# 检查系统 GCC 版本
/usr/bin/gcc --version

# 如果是 GCC 14+，安装 GCC 11
sudo apt install gcc-11 g++-11

# 编译时指定 GCC 11
export CC=/usr/bin/gcc-11
export CXX=/usr/bin/g++-11
```

### Q2: PyTorch 报 "no kernel image is available for execution"

**原因**: PyTorch 版本不支持 sm_120

**解决方案**: 确保安装的是 nightly 版本，不是 stable 版本
```bash
pip install --pre torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/nightly/cu128
```

### Q3: mmcv 编译失败 "ninja: build stopped"

**原因**: 内存不足或编译器错误

**解决方案**:
```bash
# 减少并行编译数
export MAX_JOBS=2
python setup.py develop
```

### Q4: 运行时报 "CUDA out of memory"

**原因**: RTMPose 多人检测需要较多显存

**解决方案**: 调整配置
```yaml
# backend/config/config.yaml
pose:
  max_persons: 3  # 从 5 减少到 3
  det_score_thr: 0.4  # 提高检测阈值
```

---

## 性能参考

在 RTX 5080 (16GB) 上的测试结果：

| 场景 | 分辨率 | 人数 | FPS |
|------|--------|------|-----|
| 单人检测 | 1920x1080 | 1 | 45+ |
| 多人检测 | 1920x1080 | 3 | 35+ |
| 多人检测 | 1920x1080 | 5 | 25+ |

---

## 部署检查清单

- [ ] NVIDIA 驱动 550+ 已安装
- [ ] Conda 环境已创建
- [ ] PyTorch nightly (CUDA 12.8) 已安装
- [ ] CUDA toolkit 12.8 已安装
- [ ] mmcv 从源码编译完成
- [ ] MMPose 已安装
- [ ] RTMPose 模型已下载
- [ ] 后端服务可正常启动
- [ ] 前端可正常访问

---

## 参考链接

- [PyTorch Nightly Builds](https://pytorch.org/get-started/locally/)
- [mmcv GitHub](https://github.com/open-mmlab/mmcv)
- [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit)
- [Blackwell Architecture](https://developer.nvidia.com/blackwell-gpu-architecture)

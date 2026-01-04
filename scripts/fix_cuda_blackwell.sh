#!/bin/bash
# =============================================================================
# fix_cuda_blackwell.sh
# 修复 RTX 5070 (Blackwell架构 sm_120) CUDA兼容性问题
#
# 问题链:
# 1. RTX 5070 (Blackwell) 需要 sm_120 支持
# 2. PyTorch stable 不支持 sm_120，需要 nightly
# 3. mmcv 需要从源码编译，需要 nvcc 12.8+
# 4. CUDA 12.8 需要 GCC < 14，使用系统 GCC 11
# =============================================================================

echo "======================================"
echo "修复 RTX 5070 (Blackwell) CUDA 兼容性"
echo "======================================"

# 检测 conda 环境
CONDA_ENV="cc-sop"
if [ -n "$CONDA_PREFIX" ]; then
    echo "当前 conda 环境: $(basename $CONDA_PREFIX)"
else
    echo "激活 conda 环境: $CONDA_ENV"
    eval "$(conda shell.bash hook)"
    conda activate $CONDA_ENV
fi

echo ""
echo "======================================"
echo "步骤 1: 安装 PyTorch nightly (CUDA 12.8)"
echo "======================================"
pip uninstall -y torch torchvision torchaudio 2>/dev/null || true
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

echo ""
echo "======================================"
echo "步骤 2: 安装 CUDA toolkit 12.8 (nvcc)"
echo "======================================"
conda install -y -c conda-forge cuda-nvcc=12.8.93 cuda-cudart-dev cuda-libraries-dev ninja

echo ""
echo "======================================"
echo "步骤 3: 安装 MM 系列依赖"
echo "======================================"
pip install openmim mmengine mmdet
pip install mmpose --no-deps
pip install xtcocotools munkres json_tricks

echo ""
echo "======================================"
echo "步骤 4: 从源码编译 mmcv (支持 sm_120)"
echo "======================================"
cd /tmp
rm -rf mmcv
git clone --depth 1 -b v2.1.0 https://github.com/open-mmlab/mmcv.git
cd mmcv

# 使用系统 GCC (< 14.0) 和新 nvcc 编译
export CC=/usr/bin/gcc
export CXX=/usr/bin/g++
export MMCV_WITH_OPS=1
export FORCE_CUDA=1
export TORCH_CUDA_ARCH_LIST="8.0;8.6;9.0;12.0"

pip uninstall -y mmcv 2>/dev/null || true
python setup.py develop
python setup.py build_ext --inplace

echo ""
echo "======================================"
echo "步骤 5: 验证安装"
echo "======================================"
python << 'EOF'
import warnings
warnings.filterwarnings('ignore')

print("测试 PyTorch...")
import torch
print(f"  PyTorch: {torch.__version__}")
print(f"  CUDA: {torch.version.cuda}")

if torch.cuda.is_available():
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    cap = torch.cuda.get_device_capability(0)
    print(f"  计算能力: {cap[0]}.{cap[1]} (sm_{cap[0]}{cap[1]})")
    x = torch.rand(3,3).cuda()
    print("  CUDA 计算: 通过")

print("\n测试 mmcv...")
from mmcv.ops import MultiScaleDeformableAttention
print("  mmcv.ops: 成功")

print("\n测试 MMPose...")
from mmpose.apis import MMPoseInferencer
print("  MMPose: 成功")

print("\n✓ 所有测试通过!")
EOF

echo ""
echo "======================================"
echo "完成!"
echo "======================================"
echo ""
echo "请重新启动后端服务："
echo "  cd backend && python -m src.main"

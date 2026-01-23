#!/bin/bash
# =============================================================================
# fix_cuda_blackwell.sh
# 修复 RTX 5070/5080/5090 (Blackwell架构 sm_120) CUDA兼容性问题
#
# 问题链:
# 1. RTX 50xx (Blackwell) 需要 sm_120 支持
# 2. PyTorch stable 不支持 sm_120，需要 nightly
# 3. mmcv 需要从源码编译，需要 nvcc 12.8+
# 4. CUDA 12.8 需要 GCC < 14
# 5. conda cuda-toolkit 头文件需要设置 CPLUS_INCLUDE_PATH
# 6. NumPy 2.x 与 opencv-python 不兼容
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}修复 RTX 50xx (Blackwell) CUDA 兼容性${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# 检测 conda 环境
CONDA_ENV="cc-sop"
if [ -n "$CONDA_PREFIX" ]; then
    echo -e "${GREEN}✓ 当前 conda 环境: $(basename $CONDA_PREFIX)${NC}"
else
    echo -e "${YELLOW}激活 conda 环境: $CONDA_ENV${NC}"
    eval "$(conda shell.bash hook)"
    conda activate $CONDA_ENV
fi

# 检查 GCC 版本
GCC_VERSION=$(gcc -dumpversion | cut -d. -f1)
if [ "$GCC_VERSION" -ge 14 ]; then
    echo -e "${RED}警告: 检测到 GCC $GCC_VERSION，CUDA 12.8 需要 GCC < 14${NC}"
    if [ -f /usr/bin/gcc-11 ]; then
        echo -e "${YELLOW}将使用 gcc-11 进行编译${NC}"
        USE_GCC11=true
    else
        echo -e "${RED}请先安装 gcc-11: sudo apt install gcc-11 g++-11${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${YELLOW}[1/6] 安装 NumPy 1.x (必须先于 PyTorch)...${NC}"
pip install "numpy>=1.24.0,<2.0.0" --force-reinstall --quiet
echo -e "${GREEN}  ✓ NumPy $(python -c 'import numpy; print(numpy.__version__)')${NC}"

echo ""
echo -e "${YELLOW}[2/6] 安装 PyTorch nightly (CUDA 12.8)...${NC}"
pip uninstall -y torch torchvision torchaudio 2>/dev/null || true
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

# 验证 PyTorch
python -c "
import torch
print(f'  PyTorch: {torch.__version__}')
print(f'  CUDA: {torch.version.cuda}')
if torch.cuda.is_available():
    print(f'  GPU: {torch.cuda.get_device_name(0)}')
    cap = torch.cuda.get_device_capability(0)
    print(f'  计算能力: sm_{cap[0]}{cap[1]}')
"
echo -e "${GREEN}  ✓ PyTorch nightly 安装完成${NC}"

echo ""
echo -e "${YELLOW}[3/6] 安装 CUDA toolkit 12.8 (nvcc)...${NC}"
conda install -y -c conda-forge cuda-nvcc=12.8 cuda-cudart-dev cuda-libraries-dev ninja --quiet 2>/dev/null || \
conda install -y -c conda-forge cuda-nvcc cuda-cudart-dev cuda-libraries-dev ninja --quiet

# 设置 CUDA 环境变量 (关键修复!)
export CUDA_HOME=$CONDA_PREFIX
export PATH=$CONDA_PREFIX/bin:$PATH
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH

# 查找 CUDA 头文件的实际位置 (conda-forge 可能放在不同目录)
CUDA_INCLUDE_DIR=""
for dir in \
    "$CONDA_PREFIX/include" \
    "$CONDA_PREFIX/targets/x86_64-linux/include" \
    "$CONDA_PREFIX/lib/python3.10/site-packages/nvidia/cuda_runtime/include"; do
    if [ -f "$dir/cuda_runtime_api.h" ]; then
        CUDA_INCLUDE_DIR="$dir"
        break
    fi
done

if [ -z "$CUDA_INCLUDE_DIR" ]; then
    # 使用 find 作为后备方案
    CUDA_INCLUDE_DIR=$(find $CONDA_PREFIX -name "cuda_runtime_api.h" -printf '%h\n' 2>/dev/null | head -1)
fi

if [ -n "$CUDA_INCLUDE_DIR" ]; then
    echo -e "${GREEN}  ✓ CUDA 头文件目录: $CUDA_INCLUDE_DIR${NC}"
    export CPLUS_INCLUDE_PATH=$CUDA_INCLUDE_DIR:$CPLUS_INCLUDE_PATH
    export C_INCLUDE_PATH=$CUDA_INCLUDE_DIR:$C_INCLUDE_PATH
else
    echo -e "${RED}  ✗ cuda_runtime_api.h 未找到${NC}"
    echo -e "${YELLOW}  尝试搜索头文件...${NC}"
    find $CONDA_PREFIX -name "cuda*.h" 2>/dev/null | head -10
    exit 1
fi

# 查找 CUDA 库文件目录
CUDA_LIB_DIR=""
for dir in \
    "$CONDA_PREFIX/lib" \
    "$CONDA_PREFIX/targets/x86_64-linux/lib" \
    "$CONDA_PREFIX/lib64"; do
    if [ -f "$dir/libcudart.so" ] || [ -d "$dir" ]; then
        CUDA_LIB_DIR="$dir"
        break
    fi
done

if [ -n "$CUDA_LIB_DIR" ]; then
    export LIBRARY_PATH=$CUDA_LIB_DIR:$LIBRARY_PATH
    export LD_LIBRARY_PATH=$CUDA_LIB_DIR:$LD_LIBRARY_PATH
fi

# 验证 nvcc
if command -v nvcc &> /dev/null; then
    NVCC_VERSION=$(nvcc --version | grep "release" | sed 's/.*release \([0-9]*\.[0-9]*\).*/\1/')
    echo -e "${GREEN}  ✓ nvcc ${NVCC_VERSION}${NC}"
else
    echo -e "${RED}  ✗ nvcc 未找到${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}[4/6] 安装 MM 系列依赖...${NC}"
pip install openmim mmengine mmdet --quiet
pip install mmpose --no-deps --quiet
pip install xtcocotools munkres json_tricks scipy matplotlib --quiet
echo -e "${GREEN}  ✓ MM 依赖安装完成${NC}"

echo ""
echo -e "${YELLOW}[5/6] 从源码编译 mmcv (支持 sm_120)...${NC}"
echo -e "${CYAN}  (这需要 15-30 分钟，请耐心等待)${NC}"

cd /tmp
rm -rf mmcv
git clone --depth 1 -b v2.1.0 https://github.com/open-mmlab/mmcv.git
cd mmcv

# 设置编译环境变量
if [ "$USE_GCC11" = true ]; then
    export CC=/usr/bin/gcc-11
    export CXX=/usr/bin/g++-11
else
    export CC=/usr/bin/gcc
    export CXX=/usr/bin/g++
fi

export MMCV_WITH_OPS=1
export FORCE_CUDA=1
export TORCH_CUDA_ARCH_LIST="8.0;8.6;9.0;12.0"

# 关键: 确保 CUDA 头文件路径正确 (使用之前检测到的路径)
export CUDA_HOME=$CONDA_PREFIX
# CUDA_INCLUDE_DIR 和 CUDA_LIB_DIR 在上面已设置

pip uninstall -y mmcv 2>/dev/null || true

# 编译 (限制并行度以避免内存问题)
MAX_JOBS=4 python setup.py develop 2>&1 | tee /tmp/mmcv_build.log

if [ $? -ne 0 ]; then
    echo -e "${RED}  ✗ mmcv 编译失败，查看日志: /tmp/mmcv_build.log${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ mmcv 编译完成${NC}"

echo ""
echo -e "${YELLOW}[6/6] 强制锁定关键版本...${NC}"

# 卸载当前的 numpy 和 opencv
pip uninstall -y numpy opencv-python opencv-python-headless 2>/dev/null || true

# 强制安装 NumPy 1.x (使用 --no-deps 防止被其他包覆盖)
pip install "numpy==1.24.4" --force-reinstall --no-deps
NUMPY_VER=$(python -c "import numpy; print(numpy.__version__)" 2>/dev/null)
if [[ "$NUMPY_VER" != "1.24.4" ]]; then
    echo -e "${RED}  NumPy 版本不正确: $NUMPY_VER，重试...${NC}"
    pip uninstall -y numpy
    pip install "numpy==1.24.4" --no-deps --ignore-installed
fi
echo -e "${GREEN}  ✓ NumPy $(python -c 'import numpy; print(numpy.__version__)')${NC}"

# 安装与 NumPy 1.x 兼容的 OpenCV
pip install "opencv-python==4.8.1.78" --force-reinstall --no-deps
echo -e "${GREEN}  ✓ OpenCV $(python -c 'import cv2; print(cv2.__version__)')${NC}"

# 锁定 setuptools
pip install "setuptools==69.5.1" --force-reinstall --quiet

# 安装缺失的 mmpose 依赖
pip install chumpy --quiet 2>/dev/null || true

echo -e "${GREEN}  ✓ 关键版本已锁定${NC}"

echo ""
echo -e "${BLUE}======================================${NC}"
echo -e "${YELLOW}验证安装${NC}"
echo -e "${BLUE}======================================${NC}"

python << 'EOF'
import warnings
warnings.filterwarnings('ignore')

success = True

print("\n测试 NumPy...")
import numpy
print(f"  NumPy: {numpy.__version__}")
if not numpy.__version__.startswith("1."):
    print("  ⚠ 警告: NumPy 应为 1.x 版本")
    success = False

print("\n测试 PyTorch...")
import torch
print(f"  PyTorch: {torch.__version__}")
print(f"  CUDA: {torch.version.cuda}")

if torch.cuda.is_available():
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    cap = torch.cuda.get_device_capability(0)
    print(f"  计算能力: {cap[0]}.{cap[1]} (sm_{cap[0]}{cap[1]})")
    x = torch.rand(3,3).cuda()
    print("  CUDA 计算: 通过")
else:
    print("  ✗ CUDA 不可用")
    success = False

print("\n测试 OpenCV...")
import cv2
print(f"  OpenCV: {cv2.__version__}")

print("\n测试 mmcv...")
try:
    from mmcv.ops import MultiScaleDeformableAttention
    import mmcv
    print(f"  mmcv: {mmcv.__version__} (CUDA ops: OK)")
except ImportError as e:
    print(f"  ✗ mmcv CUDA ops 加载失败: {e}")
    success = False

print("\n测试 MMPose...")
try:
    from mmpose.apis import MMPoseInferencer
    print("  MMPose: 成功")
except Exception as e:
    print(f"  ✗ MMPose 加载失败: {e}")
    success = False

print()
if success:
    print("✓ 所有测试通过!")
else:
    print("⚠ 部分测试失败，请检查上方输出")
EOF

echo ""
echo -e "${BLUE}======================================${NC}"
echo -e "${GREEN}完成!${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "下一步:"
echo -e "  ${CYAN}cd backend && python -m src.main${NC}"
echo ""
echo -e "${YELLOW}提示: 每次激活环境后需要设置 CUDA 路径:${NC}"
echo -e "  ${CYAN}export CUDA_HOME=\$CONDA_PREFIX${NC}"
echo -e "  ${CYAN}export CPLUS_INCLUDE_PATH=\$CONDA_PREFIX/include:\$CPLUS_INCLUDE_PATH${NC}"
echo ""
echo -e "或者将以下函数添加到 ~/.bashrc:"
echo -e '  ccsop_activate() {'
echo -e '      conda activate cc-sop'
echo -e '      export CUDA_HOME=$CONDA_PREFIX'
echo -e '      export CPLUS_INCLUDE_PATH=$CONDA_PREFIX/include:$CPLUS_INCLUDE_PATH'
echo -e '  }'
echo ""

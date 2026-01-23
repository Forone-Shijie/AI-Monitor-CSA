#!/bin/bash
# =============================================================================
# install_rtx50.sh
# RTX 5070/5080/5090 (Blackwell架构 sm_120) 完整安装脚本
#
# 使用方法:
#   conda create -n cc-sop python=3.10 -y
#   conda activate cc-sop
#   ./scripts/install_rtx50.sh
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   CC-SOP Monitor 安装 (RTX 50 系列专用)${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# ============================================
# 前置检查
# ============================================

# 检查 conda 环境
CONDA_ENV="cc-sop"
if [[ "$CONDA_DEFAULT_ENV" != "$CONDA_ENV" ]]; then
    echo -e "${RED}请先创建并激活 conda 环境:${NC}"
    echo -e "  conda create -n $CONDA_ENV python=3.10 -y"
    echo -e "  conda activate $CONDA_ENV"
    exit 1
fi
echo -e "${GREEN}✓ Conda 环境: $CONDA_ENV${NC}"

# 检查 Python 版本
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ "$PYTHON_VERSION" != "3.10" ]]; then
    echo -e "${YELLOW}警告: 推荐使用 Python 3.10，当前版本: $PYTHON_VERSION${NC}"
fi
echo -e "${GREEN}✓ Python: $PYTHON_VERSION${NC}"

# 检查 GCC 版本
GCC_VERSION=$(gcc -dumpversion | cut -d. -f1)
USE_GCC11=false
if [ "$GCC_VERSION" -ge 14 ]; then
    echo -e "${YELLOW}警告: 检测到 GCC $GCC_VERSION，CUDA 12.8 需要 GCC < 14${NC}"
    if [ -f /usr/bin/gcc-11 ]; then
        echo -e "${GREEN}✓ 将使用 gcc-11 进行编译${NC}"
        USE_GCC11=true
    else
        echo -e "${RED}请先安装 gcc-11:${NC}"
        echo -e "  sudo apt install gcc-11 g++-11"
        exit 1
    fi
else
    echo -e "${GREEN}✓ GCC: $GCC_VERSION${NC}"
fi

# 检查 NVIDIA 驱动
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}✗ nvidia-smi 未找到，请先安装 NVIDIA 驱动${NC}"
    exit 1
fi

GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n1)
DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -n1)
echo -e "${GREEN}✓ GPU: $GPU_NAME (Driver: $DRIVER_VERSION)${NC}"

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo ""

# ============================================
# Step 1: 清理旧包
# ============================================
echo -e "${YELLOW}[1/8] 卸载可能冲突的旧包...${NC}"
pip uninstall -y torch torchvision torchaudio 2>/dev/null || true
pip uninstall -y mmcv mmcv-full mmcv-lite mmdet mmpose mmengine openmim 2>/dev/null || true
pip uninstall -y xtcocotools pycocotools 2>/dev/null || true
pip uninstall -y numpy 2>/dev/null || true
echo -e "${GREEN}  ✓ 旧包已清理${NC}"
echo ""

# ============================================
# Step 2: 安装 NumPy 1.x
# ============================================
echo -e "${YELLOW}[2/8] 安装 NumPy 1.x (必须先于 PyTorch)...${NC}"
pip install "numpy>=1.24.0,<2.0.0"
NUMPY_VERSION=$(python -c "import numpy; print(numpy.__version__)")
echo -e "${GREEN}  ✓ NumPy ${NUMPY_VERSION}${NC}"
echo ""

# ============================================
# Step 3: 安装 PyTorch nightly + CUDA 12.8
# ============================================
echo -e "${YELLOW}[3/8] 安装 PyTorch nightly (CUDA 12.8)...${NC}"
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

# ============================================
# Step 4: 安装 CUDA Toolkit 12.8
# ============================================
echo -e "${YELLOW}[4/8] 安装 CUDA Toolkit 12.8 (nvcc)...${NC}"
conda install -y -c conda-forge cuda-nvcc=12.8 cuda-cudart-dev cuda-libraries-dev ninja 2>/dev/null || \
conda install -y -c conda-forge cuda-nvcc cuda-cudart-dev cuda-libraries-dev ninja

# 设置 CUDA 环境变量
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
    echo -e "${RED}  ✗ nvcc 安装失败${NC}"
    exit 1
fi
echo ""

# ============================================
# Step 5: 安装 OpenCV 和 MM 系列依赖
# ============================================
echo -e "${YELLOW}[5/8] 安装 OpenCV 和 MM 系列依赖...${NC}"

# OpenCV (锁定版本)
pip install opencv-python==4.8.1.78

# MM 系列
pip install openmim==0.3.9 mmengine==0.10.2
pip install mmdet==3.2.0

# mmpose 依赖
pip install munkres scipy matplotlib json-tricks

# mmpose (跳过依赖)
pip install mmpose==1.3.1 --no-deps

# xtcocotools
pip install cython
pip install xtcocotools --no-cache-dir --no-binary xtcocotools --no-build-isolation 2>/dev/null || \
pip install pycocotools

echo -e "${GREEN}  ✓ OpenCV 和 MM 依赖安装完成${NC}"
echo ""

# ============================================
# Step 6: 从源码编译 mmcv
# ============================================
echo -e "${YELLOW}[6/8] 从源码编译 mmcv (支持 sm_120)...${NC}"
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

# 确保 CUDA 路径正确 (使用之前检测到的路径)
export CUDA_HOME=$CONDA_PREFIX
# CUDA_INCLUDE_DIR 和 CUDA_LIB_DIR 在上面已设置

pip uninstall -y mmcv 2>/dev/null || true

# 编译
MAX_JOBS=4 python setup.py develop 2>&1 | tee /tmp/mmcv_build.log

if [ $? -ne 0 ]; then
    echo -e "${RED}  ✗ mmcv 编译失败${NC}"
    echo -e "${YELLOW}  查看日志: /tmp/mmcv_build.log${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ mmcv 编译完成${NC}"
echo ""

# ============================================
# Step 7: 安装其他后端依赖
# ============================================
echo -e "${YELLOW}[7/8] 安装其他后端依赖...${NC}"
cd "$BACKEND_DIR"

# 先安装其他依赖，但排除 numpy 和 opencv (稍后单独处理)
pip install -r requirements.txt --quiet 2>/dev/null || true
echo -e "${GREEN}  ✓ 后端依赖安装完成${NC}"
echo ""

# ============================================
# Step 8: 强制锁定关键版本 (最重要的步骤!)
# ============================================
echo -e "${YELLOW}[8/8] 强制锁定关键版本...${NC}"

# 卸载当前的 numpy 和 opencv
pip uninstall -y numpy opencv-python opencv-python-headless 2>/dev/null || true

# 强制安装 NumPy 1.x (使用 --no-deps 防止被其他包覆盖)
pip install "numpy==1.24.4" --force-reinstall --no-deps
NUMPY_VER=$(python -c "import numpy; print(numpy.__version__)" 2>/dev/null)
if [[ "$NUMPY_VER" != "1.24.4" ]]; then
    echo -e "${RED}  NumPy 版本不正确: $NUMPY_VER，重试...${NC}"
    pip uninstall -y numpy -y
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

# ============================================
# 验证安装
# ============================================
echo -e "${BLUE}======================================${NC}"
echo -e "${YELLOW}验证安装${NC}"
echo -e "${BLUE}======================================${NC}"

python << 'VERIFY_SCRIPT'
import sys
import warnings
warnings.filterwarnings('ignore')

def check(name, test_func):
    try:
        result = test_func()
        print(f"  ✓ {name}: {result}")
        return True
    except Exception as e:
        print(f"  ✗ {name}: {e}")
        return False

all_ok = True

# NumPy
all_ok &= check("NumPy", lambda: __import__('numpy').__version__)

# PyTorch
def check_torch():
    import torch
    cuda_status = "CUDA OK" if torch.cuda.is_available() else "CPU only"
    if torch.cuda.is_available():
        cap = torch.cuda.get_device_capability(0)
        gpu = f"{torch.cuda.get_device_name(0)} (sm_{cap[0]}{cap[1]})"
    else:
        gpu = "N/A"
    return f"{torch.__version__} ({cuda_status}, {gpu})"
all_ok &= check("PyTorch", check_torch)

# mmcv
def check_mmcv():
    import mmcv
    try:
        from mmcv.ops import MultiScaleDeformableAttention
        return f"{mmcv.__version__} (CUDA ops: OK)"
    except:
        return f"{mmcv.__version__} (CUDA ops: N/A)"
all_ok &= check("mmcv", check_mmcv)

# mmdet
all_ok &= check("mmdet", lambda: __import__('mmdet').__version__)

# mmpose
all_ok &= check("mmpose", lambda: __import__('mmpose').__version__)

# MMPoseInferencer
def check_inferencer():
    from mmpose.apis import MMPoseInferencer
    return "OK"
all_ok &= check("MMPoseInferencer", check_inferencer)

# OpenCV
all_ok &= check("OpenCV", lambda: __import__('cv2').__version__)

print()
if all_ok:
    print("  ========================================")
    print("  所有依赖安装成功!")
    print("  ========================================")
else:
    print("  ========================================")
    print("  部分依赖安装失败，请检查上方错误信息")
    print("  ========================================")
    sys.exit(1)
VERIFY_SCRIPT

echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}   安装完成!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "下一步:"
echo -e "  1. 下载模型: ${CYAN}./scripts/download_models.sh${NC}"
echo -e "  2. 运行测试: ${CYAN}cd backend && pytest tests/test_pose_detector.py -v${NC}"
echo -e "  3. 启动服务: ${CYAN}./scripts/start_dev.sh${NC}"
echo ""
echo -e "${YELLOW}提示: 每次激活环境后需要设置 CUDA 路径。${NC}"
echo -e "建议将以下函数添加到 ~/.bashrc:"
echo -e ""
echo -e '  ccsop_activate() {'
echo -e '      conda activate cc-sop'
echo -e '      export CUDA_HOME=$CONDA_PREFIX'
echo -e '      export PATH=$CONDA_PREFIX/bin:$PATH'
echo -e '      export CPLUS_INCLUDE_PATH=$CONDA_PREFIX/include:$CPLUS_INCLUDE_PATH'
echo -e '  }'
echo ""

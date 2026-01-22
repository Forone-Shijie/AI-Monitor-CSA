#!/bin/bash
#
# CC-SOP Monitor 依赖安装脚本
# 自动处理版本冲突，按正确顺序安装所有依赖
#
# 使用方法:
#   conda create -n cc-sop python=3.10 -y
#   conda activate cc-sop
#   ./scripts/install_deps.sh
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   CC-SOP Monitor 依赖安装${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# ============================================
# 前置检查
# ============================================

# 检查 conda 环境
CONDA_ENV="cc-sop"
if [[ "$CONDA_DEFAULT_ENV" != "$CONDA_ENV" ]]; then
    echo -e "${RED}请先激活 conda 环境:${NC}"
    echo -e "  conda create -n $CONDA_ENV python=3.10 -y"
    echo -e "  conda activate $CONDA_ENV"
    exit 1
fi
echo -e "${GREEN}✓ Conda 环境: $CONDA_ENV${NC}"

# 检查编译工具
if ! command -v gcc &> /dev/null; then
    echo -e "${RED}缺少 gcc 编译器，请先安装:${NC}"
    echo -e "  sudo apt update && sudo apt install -y build-essential"
    exit 1
fi
echo -e "${GREEN}✓ GCC: $(gcc --version | head -n1)${NC}"

# 检查 Python 版本
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ "$PYTHON_VERSION" != "3.10" ]]; then
    echo -e "${YELLOW}警告: 推荐使用 Python 3.10，当前版本: $PYTHON_VERSION${NC}"
fi
echo -e "${GREEN}✓ Python: $PYTHON_VERSION${NC}"
echo ""

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

# ============================================
# Step 1: 安装 CUDA Toolkit (通过 conda)
# ============================================
echo -e "${YELLOW}[1/9] 安装 CUDA Toolkit...${NC}"

# 检查是否已有 CUDA
if command -v nvcc &> /dev/null; then
    NVCC_VERSION=$(nvcc --version | grep "release" | sed 's/.*release \([0-9]*\.[0-9]*\).*/\1/')
    echo -e "  ${GREEN}检测到系统 nvcc ${NVCC_VERSION}${NC}"
else
    echo -e "  ${CYAN}通过 conda 安装 CUDA Toolkit 12.1...${NC}"
    conda install -y -c nvidia/label/cuda-12.1.0 cuda-toolkit cuda-nvcc 2>/dev/null || \
    conda install -y -c nvidia cuda-toolkit=12.1 cuda-nvcc=12.1 2>/dev/null || \
    conda install -y -c conda-forge cudatoolkit=12.1 2>/dev/null || {
        echo -e "${RED}CUDA Toolkit 安装失败，尝试备选方案...${NC}"
        conda install -y cuda-nvcc -c nvidia
    }
fi

# 设置 CUDA 环境变量 (conda 安装的 CUDA)
CONDA_PREFIX_CUDA="$CONDA_PREFIX"
if [ -d "$CONDA_PREFIX/lib" ]; then
    export CUDA_HOME="$CONDA_PREFIX"
    export PATH="$CONDA_PREFIX/bin:$PATH"
    export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$LD_LIBRARY_PATH"
fi

# 再次验证 nvcc
if command -v nvcc &> /dev/null; then
    NVCC_VERSION=$(nvcc --version | grep "release" | sed 's/.*release \([0-9]*\.[0-9]*\).*/\1/')
    echo -e "${GREEN}  ✓ CUDA Toolkit ${NVCC_VERSION} 已就绪${NC}"
else
    echo -e "${YELLOW}  ⚠ nvcc 未找到，mmcv 将使用 CPU 版本${NC}"
fi
echo ""

# ============================================
# Step 2: 清理旧包
# ============================================
echo -e "${YELLOW}[2/9] 卸载可能冲突的旧包...${NC}"
pip uninstall -y torch torchvision torchaudio mediapipe 2>/dev/null || true
pip uninstall -y mmcv mmcv-full mmcv-lite mmdet mmpose mmengine openmim 2>/dev/null || true
pip uninstall -y xtcocotools pycocotools 2>/dev/null || true
pip uninstall -y numpy 2>/dev/null || true
echo -e "${GREEN}  ✓ 旧包已清理${NC}"
echo ""

# ============================================
# Step 3: 安装 NumPy 1.x (必须在 PyTorch 之前)
# ============================================
echo -e "${YELLOW}[3/9] 安装 NumPy 1.x (PyTorch 兼容版本)...${NC}"
# NumPy 2.x 与 PyTorch/mmcv 的 C 扩展不兼容
pip install "numpy>=1.24.0,<2.0.0"
NUMPY_VERSION=$(python -c "import numpy; print(numpy.__version__)")
echo -e "${GREEN}  ✓ NumPy ${NUMPY_VERSION}${NC}"
echo ""

# ============================================
# Step 4: 安装 PyTorch with CUDA 12.1
# ============================================
echo -e "${YELLOW}[4/9] 安装 PyTorch 2.1.0 + CUDA 12.1...${NC}"
pip install torch==2.1.0+cu121 torchvision==0.16.0+cu121 \
    --index-url https://download.pytorch.org/whl/cu121

# 验证 PyTorch
python -c "
import torch
print(f'  PyTorch: {torch.__version__}')
print(f'  CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'  GPU: {torch.cuda.get_device_name(0)}')
"
echo -e "${GREEN}  ✓ PyTorch 安装完成${NC}"
echo ""

# ============================================
# Step 5: 安装 mmcv (带 CUDA ops)
# ============================================
echo -e "${YELLOW}[5/9] 安装 mmcv (带 CUDA 扩展)...${NC}"

# 安装 mmengine 和 openmim
pip install openmim==0.3.9 mmengine==0.10.2

# 获取 PyTorch 和 CUDA 版本
TORCH_VERSION=$(python -c "import torch; print(torch.__version__.split('+')[0])")
CUDA_VERSION=$(python -c "import torch; print(torch.version.cuda.replace('.', '')[:3] if torch.version.cuda else 'cpu')")
echo -e "  ${CYAN}PyTorch ${TORCH_VERSION}, CUDA ${CUDA_VERSION}${NC}"

MMCV_INSTALLED=false

# 方法1: 使用 mim 安装 (推荐，自动匹配 PyTorch/CUDA 版本)
echo -e "  ${CYAN}使用 mim 安装预编译 mmcv...${NC}"
if mim install mmcv==2.1.0 2>&1 | tee /tmp/mmcv_install.log; then
    # 检查是否安装了完整版本 (带 _ext 模块)
    if python -c "import mmcv._ext; from mmcv.ops import MultiScaleDeformableAttention" 2>/dev/null; then
        MMCV_INSTALLED=true
        echo -e "${GREEN}  ✓ mmcv 预编译版本 (带 CUDA ops) 安装成功${NC}"
    else
        echo -e "${YELLOW}  mim 安装的版本缺少 CUDA ops，尝试其他方法...${NC}"
        pip uninstall -y mmcv 2>/dev/null || true
    fi
fi

# 方法2: 直接从 OpenMMLab 下载预编译 wheel
if [ "$MMCV_INSTALLED" = false ]; then
    echo -e "  ${CYAN}从 OpenMMLab 下载预编译 wheel...${NC}"
    MMCV_URL="https://download.openmmlab.com/mmcv/dist/cu${CUDA_VERSION}/torch${TORCH_VERSION}/index.html"

    for attempt in 1 2 3; do
        if pip install mmcv==2.1.0 -f "$MMCV_URL" --timeout 300 2>&1 | tee /tmp/mmcv_install.log; then
            if python -c "import mmcv._ext; from mmcv.ops import MultiScaleDeformableAttention" 2>/dev/null; then
                MMCV_INSTALLED=true
                echo -e "${GREEN}  ✓ mmcv 预编译版本 (带 CUDA ops) 安装成功${NC}"
                break
            else
                echo -e "${YELLOW}  预编译版本缺少 CUDA ops，重试...${NC}"
                pip uninstall -y mmcv 2>/dev/null || true
            fi
        else
            echo -e "${YELLOW}  下载失败 (尝试 $attempt/3)${NC}"
            sleep 3
        fi
    done
fi

# 方法3: 从源码编译 (需要 nvcc)
if [ "$MMCV_INSTALLED" = false ]; then
    if command -v nvcc &> /dev/null; then
        echo -e "${YELLOW}  预编译版本不可用，从源码编译 mmcv...${NC}"
        echo -e "${YELLOW}  (这可能需要 10-30 分钟，请耐心等待)${NC}"

        # 安装编译依赖
        pip install ninja

        # 设置编译环境变量
        export MMCV_WITH_OPS=1
        export FORCE_CUDA=1

        # 确保 CUDA 路径正确
        if [ -n "$CUDA_HOME" ]; then
            export PATH="$CUDA_HOME/bin:$PATH"
        fi

        # 从 PyPI 源码编译
        if pip install mmcv==2.1.0 --no-binary mmcv -v 2>&1 | tee /tmp/mmcv_build.log; then
            if python -c "import mmcv._ext; from mmcv.ops import MultiScaleDeformableAttention" 2>/dev/null; then
                MMCV_INSTALLED=true
                echo -e "${GREEN}  ✓ mmcv 源码编译成功 (带 CUDA ops)${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}  nvcc 未找到，跳过源码编译${NC}"
    fi
fi

# 方法4: 最后手段 - 安装基础版本并给出详细错误信息
if [ "$MMCV_INSTALLED" = false ]; then
    echo -e "${RED}  ✗ 无法安装带 CUDA ops 的 mmcv${NC}"
    echo -e "${RED}    可能原因:${NC}"
    echo -e "${RED}    1. 网络无法访问 download.openmmlab.com${NC}"
    echo -e "${RED}    2. 没有匹配 PyTorch ${TORCH_VERSION} + CUDA ${CUDA_VERSION} 的预编译包${NC}"
    echo -e "${RED}    3. 缺少 nvcc 编译器无法从源码编译${NC}"
    echo ""
    echo -e "${YELLOW}  安装基础版本 (MMPose 将使用 CPU 推理)...${NC}"
    pip install mmcv==2.1.0
    echo -e "${YELLOW}  ⚠ 警告: mmcv 缺少 CUDA 扩展，RTMPose 推理速度会较慢${NC}"
fi
echo ""

# ============================================
# Step 6: 安装 mmdet 和 mmpose
# ============================================
echo -e "${YELLOW}[6/9] 安装 mmdet 和 mmpose...${NC}"

pip install mmdet==3.2.0

# mmpose 依赖
pip install munkres scipy matplotlib json-tricks

# mmpose (跳过依赖避免冲突)
pip install mmpose==1.3.1 --no-deps

echo -e "${GREEN}  ✓ MMPose 生态安装完成${NC}"
echo ""

# ============================================
# Step 7: 安装其他后端依赖
# ============================================
echo -e "${YELLOW}[7/9] 安装其他后端依赖...${NC}"
cd "$BACKEND_DIR"
pip install -r requirements.txt --quiet
echo -e "${GREEN}  ✓ 后端依赖安装完成${NC}"
echo ""

# ============================================
# Step 8: 锁定关键版本 + 编译 xtcocotools
# ============================================
echo -e "${YELLOW}[8/9] 锁定关键版本并编译 xtcocotools...${NC}"

# 确保关键依赖版本正确
pip install opencv-python==4.8.1.78 --force-reinstall --quiet
pip install numpy==1.24.4 --force-reinstall --quiet

# 锁定 setuptools 版本 (新版 setuptools>=70 的 pkg_resources 与 mmengine 不兼容)
pip install "setuptools==69.5.1" --force-reinstall --quiet

# 编译 xtcocotools (需要 numpy 1.x)
pip install cython --quiet
pip install xtcocotools --no-cache-dir --no-binary xtcocotools --no-build-isolation --force-reinstall --quiet 2>/dev/null || {
    echo -e "${YELLOW}  xtcocotools 编译失败，尝试替代方案...${NC}"
    pip install pycocotools --quiet
}

# 再次确保 numpy 版本 (xtcocotools 可能升级它)
pip install numpy==1.24.4 --force-reinstall --quiet

echo -e "${GREEN}  ✓ 关键依赖已锁定${NC}"
echo ""

# ============================================
# Step 9: 最终验证
# ============================================
echo -e "${YELLOW}[9/9] 验证安装...${NC}"
echo ""

python << 'VERIFY_SCRIPT'
import sys

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
    gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A"
    return f"{torch.__version__} ({cuda_status}, GPU: {gpu})"
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
echo -e "${BLUE}======================================${NC}"
echo -e "${GREEN}   安装完成!${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "下一步:"
echo -e "  1. 运行测试: ${CYAN}cd backend && pytest tests/test_pose_detector.py -v${NC}"
echo -e "  2. 启动服务: ${CYAN}./scripts/start_dev.sh${NC}"
echo ""
echo -e "${YELLOW}提示: 如果 CUDA 未生效，请重新激活 conda 环境:${NC}"
echo -e "  ${CYAN}conda deactivate && conda activate cc-sop${NC}"
echo ""

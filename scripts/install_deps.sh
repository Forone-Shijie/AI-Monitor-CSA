#!/bin/bash
#
# CC-SOP Monitor 依赖安装脚本
# 自动处理版本冲突，按正确顺序安装所有依赖
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

# 检查 conda 环境
CONDA_ENV="cc-sop"
if [[ "$CONDA_DEFAULT_ENV" != "$CONDA_ENV" ]]; then
    echo -e "${YELLOW}请先激活 conda 环境:${NC}"
    echo -e "  conda activate $CONDA_ENV"
    exit 1
fi

# 检查编译工具
if ! command -v gcc &> /dev/null; then
    echo -e "${RED}缺少 gcc 编译器，请先安装:${NC}"
    echo -e "  sudo apt update && sudo apt install -y build-essential"
    exit 1
fi

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo -e "${YELLOW}[1/7] 卸载可能冲突的旧包...${NC}"
pip uninstall -y torch torchvision torchaudio mediapipe 2>/dev/null || true
pip uninstall -y mmcv mmcv-full mmdet mmpose mmengine openmim 2>/dev/null || true
pip uninstall -y xtcocotools pycocotools 2>/dev/null || true
pip uninstall -y numpy 2>/dev/null || true
echo -e "${GREEN}  ✓ 旧包已清理${NC}"
echo ""

echo -e "${YELLOW}[2/7] 安装 PyTorch with CUDA 12.1...${NC}"
pip install torch==2.1.0+cu121 torchvision==0.16.0+cu121 \
    --index-url https://download.pytorch.org/whl/cu121
echo -e "${GREEN}  ✓ PyTorch 安装完成${NC}"
echo ""

echo -e "${YELLOW}[3/7] 安装 MMPose 生态 (不含 xtcocotools)...${NC}"
pip install openmim==0.3.9
mim install mmengine==0.10.2
# 从 OpenMMLab 安装预编译的 mmcv (带 CUDA 扩展)
pip install mmcv==2.1.0 -f https://download.openmmlab.com/mmcv/dist/cu121/torch2.1/index.html
mim install mmdet==3.2.0

# 安装 mmpose 必需依赖 (不含 xtcocotools)
pip install munkres scipy matplotlib json-tricks

# 安装 mmpose (跳过所有依赖)
pip install mmpose==1.3.1 --no-deps

echo -e "${GREEN}  ✓ MMPose 生态安装完成${NC}"
echo ""

echo -e "${YELLOW}[4/7] 安装其他后端依赖...${NC}"
cd "$BACKEND_DIR"
pip install -r requirements.txt
echo -e "${GREEN}  ✓ 后端依赖安装完成${NC}"
echo ""

echo -e "${YELLOW}[5/7] 锁定关键依赖版本...${NC}"
# 降级 opencv-python 和 numpy 到兼容版本
pip install opencv-python==4.8.1.78 --force-reinstall
pip install numpy==1.24.4 --force-reinstall
echo -e "${GREEN}  ✓ 关键依赖版本已锁定${NC}"
echo ""

echo -e "${YELLOW}[6/7] 编译安装 xtcocotools...${NC}"
# 安装 cython (编译 xtcocotools 需要)
pip install cython
# 从源码编译 xtcocotools (使用当前 numpy 1.24.4)
pip install xtcocotools --no-cache-dir --no-binary xtcocotools --no-build-isolation --force-reinstall
# 再次确保 numpy 版本正确 (xtcocotools 可能会升级它)
pip install numpy==1.24.4 --force-reinstall
echo -e "${GREEN}  ✓ xtcocotools 安装完成${NC}"
echo ""

echo -e "${YELLOW}[7/7] 验证安装...${NC}"
python -c "
import torch
print(f'  PyTorch: {torch.__version__}')
print(f'  CUDA: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'  GPU: {torch.cuda.get_device_name(0)}')

import numpy as np
print(f'  NumPy: {np.__version__}')

from mmpose.apis import init_model
from mmdet.apis import init_detector
print('  MMPose/MMDet: OK')
"

echo ""
echo -e "${BLUE}======================================${NC}"
echo -e "${GREEN}   所有依赖安装完成!${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "下一步:"
echo -e "  1. 运行测试: ${CYAN}./scripts/test_all.sh${NC}"
echo -e "  2. 启动服务: ${CYAN}./scripts/start_dev.sh${NC}"
echo ""

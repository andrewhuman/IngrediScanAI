#!/bin/bash
# 启动后端服务的脚本

# 激活 conda 环境
source ~/miniconda3/etc/profile.d/conda.sh
conda activate p312

# 检查环境
echo "Python 路径: $(which python)"
echo "Python 版本: $(python --version)"

# 检查依赖
echo "检查依赖..."
python -c "import rapidocr_onnxruntime; print('✓ RapidOCR 已安装')" || echo "✗ RapidOCR 未安装"
python -c "import openai; print('✓ OpenAI SDK 已安装（用于 OpenRouter）')" || echo "✗ OpenAI SDK 未安装"

# 设置 API Key（如果未设置）
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "警告: OPENROUTER_API_KEY 未设置，请设置环境变量"
    echo "例如: export OPENROUTER_API_KEY='your-api-key-here'"
fi

# 进入后端目录
cd "$(dirname "$0")"

# 使用 python -m uvicorn 确保使用正确的 Python 环境
echo "启动服务..."
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

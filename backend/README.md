# IngrediScan AI Backend

FastAPI 后端服务，集成 RapidOCR 和 OpenRouter 多模态模型进行食品成分分析。

## 环境要求

- **Python**: 3.12（RapidOCR 不支持 Python 3.13）
- 本地建议使用 `p312` conda 环境

## 安装依赖

```bash
# 激活 p312 环境
conda activate p312

# 安装依赖
pip install -r requirements.txt
```

## 启动服务

### 方法 1：使用启动脚本（推荐）

```bash
cd backend
export OPENROUTER_API_KEY="your-api-key-here"
./start.sh
```

### 方法 2：手动启动

```bash
# 激活 conda 环境
conda activate p312

# 设置 API Key
export OPENROUTER_API_KEY="your-api-key-here"

# 使用 python -m uvicorn（重要！）
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**重要提示**：
- 必须使用 `python -m uvicorn` 而不是直接使用 `uvicorn` 命令
- 这样可以确保使用 conda 环境中的 Python 和依赖
- 如果使用 `uvicorn` 命令，可能会使用系统级别的 uvicorn，导致找不到依赖

## 环境变量

- `OPENROUTER_API_KEY`: OpenRouter API Key（必需）
- `OPENROUTER_MODEL`: 模型名（默认 `nvidia/nemotron-nano-12b-v2-vl:free`）
- `OPENROUTER_SITE_URL`: 可选，OpenRouter 统计来源站点
- `OPENROUTER_APP_NAME`: 可选，OpenRouter 展示应用名
- `CORS_ALLOWED_ORIGINS`: 允许跨域来源（逗号分隔）
- `CORS_ALLOWED_ORIGIN_REGEX`: 允许跨域来源正则（可选）
- `PORT`: 服务端口（默认 8000）

示例（见 `backend/.env.example`）：

```bash
OPENROUTER_API_KEY=your-api-key-here
OPENROUTER_MODEL=nvidia/nemotron-nano-12b-v2-vl:free
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app
# 可选：需要放行 Vercel Preview 时再开启
# CORS_ALLOWED_ORIGIN_REGEX=^https://.*\.vercel\.app$
```

## Render 部署

仓库根目录已提供 `render.yaml`，用于 Blueprint 一键部署。

关键配置：

- `rootDir`: `backend`
- `buildCommand`: `pip install -r requirements.txt`
- `startCommand`: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
- `healthCheckPath`: `/health`

## API 文档

服务启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 故障排除

### 问题：显示 "RapidOCR 未安装" 或 "OpenAI SDK 未安装"

**原因**：使用了系统级别的 `uvicorn` 命令，而不是 conda 环境中的。

**解决**：
1. 使用 `python -m uvicorn` 代替 `uvicorn` 命令
2. 或使用提供的 `start.sh` 脚本

### 问题：依赖安装失败

**检查**：
```bash
conda activate p312
python --version  # 应该显示 Python 3.12.x
pip list | grep rapidocr
pip list | grep openai
```

**重新安装**：
```bash
conda activate p312
pip install -r requirements.txt
```
# IngrediScanAI

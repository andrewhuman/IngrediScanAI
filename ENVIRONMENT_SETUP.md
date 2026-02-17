# 环境配置说明

## ✅ 当前配置状态

### 前端（Next.js）
- **Node.js**: 已升级（支持 Next.js 16）
- **构建状态**: ✅ 成功
- **环境**: 系统 Node.js（不依赖 conda）

### 后端（FastAPI）
- **Python 环境**: `p312` (Python 3.12.11)
- **依赖状态**: ✅ 已安装
- **关键依赖**:
  - FastAPI 0.115.0
  - RapidOCR 1.4.4 (支持 Python 3.12)
  - OpenAI 2.8.1（用于 OpenRouter）
  - Uvicorn 0.32.0

## 🚀 启动项目

### 1. 启动后端服务

**方法 1：使用启动脚本（推荐）**

```bash
cd backend
export OPENROUTER_API_KEY="your-api-key-here"
./start.sh
```

**方法 2：手动启动**

```bash
# 切换到 p312 环境
conda activate p312

# 进入后端目录
cd backend

# 设置 OpenRouter API Key（必需）
export OPENROUTER_API_KEY="your-api-key-here"

# 使用 python -m uvicorn 确保使用正确的 Python 环境
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 或直接运行
python main.py
```

**重要提示**：如果使用 `uvicorn` 命令启动时显示依赖未安装，请使用 `python -m uvicorn` 代替，这样可以确保使用 conda 环境中的 Python 和依赖。

**后端服务地址**: http://localhost:8000
**API 文档**: http://localhost:8000/docs

### 2. 启动前端服务

```bash
# 在项目根目录（不需要 conda 环境）
cd /home/xyd_hc/下载/IngrediScanAI

# 开发模式
npm run dev

# 生产模式
npm run build
npm start
```

**前端服务地址**: http://localhost:3000

## 📝 重要提示

### Conda 环境使用

1. **后端必须使用 `p312` 环境**：
   - RapidOCR 不支持 Python 3.13
   - 当前配置已针对 Python 3.12 优化

2. **前端不需要 conda 环境**：
   - Next.js 使用系统 Node.js
   - 确保 Node.js 版本 >= 20.9.0

### 环境切换示例

```bash
# 启动后端时
conda activate p312
cd backend
uvicorn main:app --reload

# 启动前端时（新终端窗口）
cd /home/xyd_hc/下载/IngrediScanAI
npm run dev
```

## 🔧 故障排除

### 后端问题

**问题**: `rapidocr-onnxruntime` 安装失败
**解决**: 确保使用 `p312` 环境（Python 3.12）

```bash
conda activate p312
python --version  # 应该显示 Python 3.12.x
pip install -r backend/requirements.txt
```

### 前端问题

**问题**: 构建失败，提示 Turbopack/webpack 冲突
**解决**: 已在 `next.config.mjs` 中添加 `turbopack: {}` 配置

**问题**: Node.js 版本过低
**解决**: 升级 Node.js 到 20.x LTS

## 📦 依赖版本

### 后端 (backend/requirements.txt)
```
fastapi==0.115.0
uvicorn[standard]==0.32.0
python-multipart==0.0.12
pillow==11.0.0
numpy==2.1.0
rapidocr-onnxruntime>=1.3.19  # 支持 Python 3.12
openai==2.8.1
pydantic==2.9.0
```

### 前端 (package.json)
- Next.js 16.0.10
- React 19.2.0
- TypeScript 5.x

## ✅ 验证清单

- [x] 后端依赖安装成功（p312 环境）
- [x] 前端构建成功
- [x] Next.js Turbopack 配置已修复
- [ ] OpenRouter API Key 已配置（需要你设置）
- [ ] 后端服务可启动
- [ ] 前端服务可启动
- [ ] 前后端可正常通信

## 🎯 下一步

1. **配置 OpenRouter API Key**：
   ```bash
   export OPENROUTER_API_KEY="your-api-key-here"
   ```

2. **启动后端服务**（在 p312 环境下）

3. **启动前端服务**（不需要 conda）

4. **测试完整流程**：
   - 访问 http://localhost:3000
   - 拍照/选择图片
   - 查看分析结果

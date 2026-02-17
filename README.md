# IngrediScan AI

一个智能的食品成分分析 PWA 应用，使用 AI 技术帮助用户快速了解产品成分和健康风险。

## 功能特性

- 📸 **拍照/相册选择**：支持调用系统相机或从相册选择图片
- 🗜️ **智能压缩**：前端自动压缩图片至 1024px（长边），优化上传速度
- 🔍 **OCR 文字提取**：使用 RapidOCR 快速提取包装上的文字信息
- 🤖 **AI 成分分析**：集成 OpenRouter 多模态模型进行深度成分分析
- 📊 **健康评分**：提供 A-E 等级的健康评分
- ⚠️ **风险识别**：自动识别高风险、中等风险成分
- 💡 **替代建议**：推荐更健康的替代产品
- 📱 **PWA 支持**：可安装到手机，支持离线访问
- 📱 **移动优化**：完美适配 iOS/Android，支持 Safe Area

## 技术栈

### 前端
- **Next.js 16** (App Router)
- **TypeScript**
- **Tailwind CSS**
- **Shadcn UI**
- **Lucide React**
- **browser-image-compression**
- **next-pwa**

### 后端
- **FastAPI** (Python)
- **RapidOCR** (ONNX 优化版，CPU 快速推理)
- **OpenRouter** (`nvidia/nemotron-nano-12b-v2-vl:free`)
- **Pillow** (图片处理)

## 项目结构

```
IngrediScanAI/
├── app/                    # Next.js App Router
│   ├── page.tsx           # 主页面
│   ├── layout.tsx         # 根布局
│   └── globals.css        # 全局样式
├── components/            # React 组件
│   └── ui/               # Shadcn UI 组件
├── lib/                   # 工具函数
│   ├── image-compression.ts  # 图片压缩
│   └── api.ts            # API 客户端
├── backend/               # Python 后端服务
│   ├── main.py           # FastAPI 主应用
│   ├── services/         # 服务模块
│   │   ├── ocr_service.py    # OCR 服务
│   │   └── vlm_service.py    # VLM 服务
│   └── requirements.txt  # Python 依赖
├── vercel.json            # Vercel 前端部署配置
├── render.yaml            # Render 后端部署配置
├── .env.example           # 前端环境变量示例
├── backend/.env.example   # 后端环境变量示例
└── public/               # 静态资源
    └── manifest.json     # PWA 清单
```

## 快速开始

### 1. 安装前端依赖

```bash
npm install
# 或
pnpm install
```

### 2. 配置环境变量

创建 `.env.local` 文件（可直接复制 `.env.example`）：

```bash
# 后端服务 URL
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

### 3. 启动前端开发服务器

```bash
npm run dev
```

访问 http://localhost:3000

### 4. 设置后端服务

#### 安装 Python 依赖

```bash
cd backend
pip install -r requirements.txt
```

#### 配置 OpenRouter API Key

```bash
export OPENROUTER_API_KEY="your-api-key-here"
```

获取 API Key：
1. 访问 [OpenRouter 控制台](https://openrouter.ai/)
2. 注册/登录账号
3. 创建 API Key
4. 设置环境变量

#### 启动后端服务

```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

或直接运行：

```bash
python main.py
```

## 使用流程

1. **拍照/选择图片**：点击相机按钮或选择相册图片
2. **自动压缩**：前端自动压缩图片（最大 1024px，质量 0.8）
3. **上传分析**：图片上传到后端，进行 OCR + VLM 分析
4. **查看结果**：
   - 健康评分（A-E）
   - 风险成分列表（高风险/中等风险）
   - 完整成分列表
   - 健康替代品建议

## 核心逻辑

### 图片处理流程

```
用户选择图片
    ↓
前端压缩（1024px, 0.8 质量）
    ↓
转换为 Base64
    ↓
发送到 NEXT_PUBLIC_BACKEND_URL/api/v1/analyze
    ↓
后端接收并解码图片
    ↓
RapidOCR 提取文字
    ↓
OpenRouter VLM 分析成分
    ↓
返回结构化 JSON
    ↓
前端展示结果
```

### OCR + VLM 策略

- **OCR 辅助**：提取细小、模糊的配料表文字
- **VLM 主导**：通过视觉理解进行深度分析
- **容错机制**：OCR 失败时，VLM 仅通过视觉分析

### 健康评分算法

- **A**: ≥80% 健康成分
- **B**: 50-79% 健康成分
- **C**: 30-49% 健康成分
- **D**: 10-29% 健康成分
- **E**: <10% 健康成分

## 开发说明

### 前端开发

```bash
# 开发模式
npm run dev

# 构建生产版本
npm run build

# 启动生产服务器
npm start
```

### 后端开发

```bash
# 开发模式（自动重载）
python -m uvicorn main:app --reload

# 生产模式
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## 部署方案（推荐）

前后端分离部署：

1. 前端（Next.js）部署到 **Vercel**
2. 后端（FastAPI）部署到 **Render**
3. 前端通过 `NEXT_PUBLIC_BACKEND_URL` 直接调用 Render API（不走 Next.js Serverless 中转）

> 完整可执行部署SOP（含账号/密钥清单、OpenClaw执行步骤、验收命令）请查看：`OPENCLAW_DEPLOYMENT.md`

### 1. 部署后端到 Render

仓库已提供 `render.yaml`，可直接创建 Blueprint Web Service。

关键环境变量（Render Dashboard）：

```bash
OPENROUTER_API_KEY=your-api-key
OPENROUTER_MODEL=nvidia/nemotron-nano-12b-v2-vl:free
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
# 可选：需要放行 Vercel Preview 时再开启
# CORS_ALLOWED_ORIGIN_REGEX=^https://.*\.vercel\.app$
```

后端健康检查：

- `GET /health`

### 2. 部署前端到 Vercel

仓库已提供 `vercel.json`。

关键环境变量（Vercel Dashboard）：

```bash
NEXT_PUBLIC_BACKEND_URL=https://your-backend.onrender.com
```

发布后前端将直接请求：

- `POST https://your-backend.onrender.com/api/v1/analyze`

### PWA 配置

PWA 功能通过 `next-pwa` 自动配置：
- Service Worker 自动生成
- 离线缓存策略已配置
- Manifest.json 已配置

## 环境变量

### 前端 (.env.local)

```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

### 后端

```bash
OPENROUTER_API_KEY=your-api-key-here
OPENROUTER_MODEL=nvidia/nemotron-nano-12b-v2-vl:free
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app
# 可选：需要放行 Vercel Preview 时再开启
# CORS_ALLOWED_ORIGIN_REGEX=^https://.*\.vercel\.app$
PORT=8000
```

## API 文档

后端服务启动后，访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 注意事项

1. **相机权限**：首次使用需要授予相机权限，如果拒绝，可改用相册选择
2. **网络要求**：需要网络连接以调用后端 API
3. **API 限流**：注意 OpenRouter API 的调用频率限制
4. **图片质量**：建议拍摄清晰的包装图片以获得最佳分析结果
5. **OCR 失败**：如果图片模糊导致 OCR 失败，VLM 会尝试仅通过视觉分析

## 故障排除

### 前端问题

- **PWA 不工作**：确保在 HTTPS 或 localhost 环境下运行
- **图片上传失败**：检查后端服务是否运行，网络连接是否正常

### 后端问题

- **OCR 失败**：检查 RapidOCR 是否正确安装
- **VLM API 错误**：检查 OpenRouter API Key 是否正确设置
- **端口冲突**：修改 `PORT` 环境变量或 `main.py` 中的端口号

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

# Sentry & LangSmith 配置指南

## Sentry（错误监控）

### 注册步骤
1. 打开 https://sentry.io/ 用 Google 登录
2. 创建新组织（如果还没有）：
   - 点击 "Create Organization"
   - 名称：IngrediScan AI
   - 团队：Personal
3. 创建项目：
   - **前端（Next.js）**:
     - 选择 "Next.js"
     - 名称：ingrediscanai-frontend
   - **后端（Python/FastAPI）**:
     - 选择 "Python"
     - 名称：ingrediscanai-backend
4. 获取 DSN：
   - 进入项目 → Settings → Client Keys (DSN)
   - 复制 DSN（以 `https://<key>@o...` 开头）

### 配置
**Vercel 环境变量**：
```
NEXT_PUBLIC_SENTRY_DSN=https://your-dsn-here
NEXT_PUBLIC_SENTRY_ENVIRONMENT=production
NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_AUTH_TOKEN=your-auth-token  # 可选，用于 sourcemap
SENTRY_ORG=your-org-slug
SENTRY_PROJECT=ingrediscanai-frontend
```

**Render 环境变量**：
```
SENTRY_DSN=https://your-dsn-here
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

## LangSmith（LLM 链路追踪）

### 注册步骤
1. 打开 https://smith.langchain.com/ 用 Google 登录
2. Settings → API Keys → Create API Key
3. 复制显示的一次性 key

### 配置
**Render 环境变量**：
```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=ingrediscanai-production  # 或自定义名称
```

## 部署验证
1. 更新环境变量后，Render 和 Vercel 会自动部署
2. 访问 https://workspace-phi-fawn-46.vercel.app
3. 使用商品标签图片测试
4. 查看监控面板：
   - Sentry Issues 是否新增错误
   - LangSmith Traces 是否有新记录

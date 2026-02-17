# IngrediScanAI 部署SOP（OpenClaw可执行版）

适用架构：前端 `Next.js` 部署到 `Vercel`，后端 `FastAPI` 部署到 `Render`。  
目标：让 OpenClaw 按固定步骤完成部署、验收、回归发布。

## 1. 必备资产与权限清单

先准备下列账号和密钥，再开始部署。

| 类型 | 名称 | 用途 | 必须 |
|---|---|---|---|
| 平台账号 | Vercel 管理员账号 | 创建/管理前端项目、配置环境变量 | 是 |
| 平台账号 | Render 管理员账号 | 创建/管理后端服务、配置环境变量 | 是 |
| 云API账号 | OpenRouter 账号 + API Key | 后端调用多模态模型 | 是 |
| 代码仓库 | GitHub/GitLab 仓库管理员权限 | 连接 Vercel/Render 自动部署 | 是 |
| 自动化令牌 | `VERCEL_TOKEN` | OpenClaw 非交互触发 Vercel 部署（可选） | 否 |
| 自动化令牌 | `RENDER_API_KEY` | OpenClaw 调用 Render API（可选） | 否 |
| 代码令牌 | Git PAT/Deploy Key | OpenClaw 推送代码触发自动部署（可选） | 否 |

注意：
- 自动化优先使用 Token，不建议把主账号密码交给自动化进程。
- 若必须使用密码登录，只用于首次平台绑定，后续改为 Token。

## 2. 环境变量总表（按平台）

### 2.1 Render（后端）

必须设置：

```bash
OPENROUTER_API_KEY=<你的OpenRouter Key>
OPENROUTER_MODEL=nvidia/nemotron-nano-12b-v2-vl:free
CORS_ALLOWED_ORIGINS=https://<你的Vercel生产域名>,http://localhost:3000
# 可选：需要放行 Vercel Preview 时再设置
# CORS_ALLOWED_ORIGIN_REGEX=^https://.*\.vercel\.app$
```

说明：
- `OPENROUTER_API_KEY`：后端调用 OpenRouter 必需。
- `OPENROUTER_MODEL`：当前固定模型 `nvidia/nemotron-nano-12b-v2-vl:free`。
- `CORS_ALLOWED_ORIGINS`：至少包含正式前端域名；建议保留 `http://localhost:3000` 便于本地调试。
- `CORS_ALLOWED_ORIGIN_REGEX`：可选，留空表示仅用 `CORS_ALLOWED_ORIGINS` 精确白名单。

### 2.2 Vercel（前端）

必须设置：

```bash
NEXT_PUBLIC_BACKEND_URL=https://<你的Render后端域名>
```

说明：
- 前端直接请求 `${NEXT_PUBLIC_BACKEND_URL}/api/v1/analyze`。

## 3. 首次部署流程（一次性）

建议顺序：先后端，再前端，最后回填 CORS。

### 步骤 1：Render 部署后端

1. 进入 Render Dashboard。
2. `New +` -> `Blueprint` -> 选择当前仓库。
3. 使用仓库根目录 `render.yaml` 创建服务。
4. 在服务环境变量中填写第 2.1 节的变量值。
5. 等待部署完成，记录后端地址（示例）：`https://ingrediscanai-backend.onrender.com`。
6. 验收健康检查：

```bash
curl -sS https://<你的Render后端域名>/health
```

期望返回：

```json
{"status":"healthy"}
```

### 步骤 2：Vercel 部署前端

1. 进入 Vercel Dashboard。
2. `Add New...` -> `Project` -> 导入当前仓库。
3. 使用仓库内已有 `vercel.json`（Framework: Next.js）。
4. 配置环境变量 `NEXT_PUBLIC_BACKEND_URL=https://<你的Render后端域名>`。
5. 发起生产部署，记录前端生产地址（示例）：`https://xxx.vercel.app`。

### 步骤 3：回填 Render CORS

前端生产地址确定后，回到 Render 更新：

```bash
CORS_ALLOWED_ORIGINS=https://<你的Vercel生产域名>,http://localhost:3000
```

保存并触发一次重新部署。

## 4. OpenClaw 持续部署流程（推荐）

首次部署完成后，后续建议使用“代码推送触发自动部署”：

1. OpenClaw 拉取/修改代码。
2. OpenClaw 推送到目标分支（通常 `main`）。
3. Vercel 与 Render 自动检测新提交并部署（当前 `render.yaml` 已 `autoDeploy: true`）。
4. OpenClaw执行部署后验收（第 5 节命令）。

## 5. 部署后验收命令（OpenClaw可直接执行）

把下列变量替换为真实地址：

```bash
export BACKEND_URL="https://<your-backend>.onrender.com"
export FRONTEND_URL="https://<your-frontend>.vercel.app"
```

1) 后端健康检查：

```bash
curl -sS "$BACKEND_URL/health"
```

2) 前端可达性检查：

```bash
curl -I "$FRONTEND_URL"
```

3) 端到端分析接口检查（使用仓库示例图）：

```bash
IMG_B64=$(base64 -w 0 public/food-product-nutrition-label.jpg)
curl -sS -X POST "$BACKEND_URL/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d "{\"image_base64\":\"$IMG_B64\",\"image_type\":\"image/jpeg\"}"
```

预期：
- HTTP 200
- 返回 JSON，包含 `health_score` 或 `error/error_type` 字段（都表示接口正常返回）。

## 6. 常见失败点与处理

1. Render 冷启动较慢：  
免费实例休眠后首次请求慢，属于预期。可升级实例或增加保活策略。

2. CORS 报错：  
优先检查 `CORS_ALLOWED_ORIGINS` 是否包含生产域名；Preview 依赖 `CORS_ALLOWED_ORIGIN_REGEX`。

3. OpenRouter 调用失败：  
检查 `OPENROUTER_API_KEY` 是否有效、是否有额度、是否被误填空格。

4. 前端请求地址错误：  
检查 Vercel 的 `NEXT_PUBLIC_BACKEND_URL` 是否指向 Render 正式 URL，并重新部署前端。

## 7. 最小化交付给 OpenClaw 的敏感信息

建议仅提供以下信息（不提供主账号密码）：

```bash
# 必须
OPENROUTER_API_KEY=
RENDER_BACKEND_URL=
VERCEL_FRONTEND_URL=

# 可选（仅当要做全自动平台操作）
VERCEL_TOKEN=
RENDER_API_KEY=
GIT_PAT=
```

如果你希望，我可以下一步再补一版“纯命令行自动部署脚本”（使用 `vercel` CLI + Render API）以便 OpenClaw 一键执行。

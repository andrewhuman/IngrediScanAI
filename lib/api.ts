/**
 * API 客户端函数
 */

export interface IngredientDetail {
  name: string
  description?: string
}

export interface AnalyzeResponse {
  health_score: string
  summary: string
  risks: Array<{
    level: 'High' | 'Moderate' | 'Low'
    name: string
    desc: string
  }>
  full_ingredients: string[]
  ingredients_detail?: IngredientDetail[]
  alternatives: string[]
  confidence?: number
  error?: string
  error_type?: 'invalid_image' | 'api_error' | 'parse_error' | 'server_error' | 'unknown_error'
}

interface BackendAnalyzeRequest {
  image_base64: string
  image_type: string
}

function normalizeBaseUrl(url: string): string {
  return url.replace(/\/+$/, "")
}

function isPrivateIpv4(hostname: string): boolean {
  const parts = hostname.split(".")
  if (parts.length !== 4 || parts.some((p) => p === "" || Number.isNaN(Number(p)))) {
    return false
  }

  const nums = parts.map((p) => Number(p))
  if (nums.some((n) => n < 0 || n > 255)) {
    return false
  }

  if (nums[0] === 10) return true
  if (nums[0] === 192 && nums[1] === 168) return true
  if (nums[0] === 172 && nums[1] >= 16 && nums[1] <= 31) return true
  if (nums[0] === 127) return true
  return false
}

function getBackendBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_BACKEND_URL
  if (envUrl) {
    return normalizeBaseUrl(envUrl)
  }

  // 本地开发兜底：支持 localhost / 局域网 IP / *.local
  if (typeof window !== "undefined") {
    const { hostname } = window.location
    const isLocalHost =
      hostname === "localhost" ||
      hostname === "127.0.0.1" ||
      hostname === "::1" ||
      hostname.endsWith(".local") ||
      isPrivateIpv4(hostname)

    if (isLocalHost) {
      return `http://${hostname}:8000`
    }
  }

  throw new Error("未配置 NEXT_PUBLIC_BACKEND_URL，请先设置后端服务地址")
}

/**
 * 上传图片并获取分析结果
 */
export async function analyzeImage(
  imageBase64: string,
  imageType: string
): Promise<AnalyzeResponse> {
  const backendBaseUrl = getBackendBaseUrl()
  const response = await fetch(`${backendBaseUrl}/api/v1/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      image_base64: imageBase64,
      image_type: imageType,
    } as BackendAnalyzeRequest),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: "请求失败" }))
    const message =
      error.error ||
      error.detail ||
      error.message ||
      `HTTP ${response.status}: ${response.statusText}`
    throw new Error(message)
  }

  return response.json()
}

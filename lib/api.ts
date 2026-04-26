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

function createRequestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

/**
 * 上传图片并获取分析结果
 */
export async function analyzeImage(
  imageBase64: string,
  imageType: string
): Promise<AnalyzeResponse> {
  const backendBaseUrl = getBackendBaseUrl()
  const requestId = createRequestId()
  let response: Response
  try {
    console.info("[analyze] request_start", {
      requestId,
      backendBaseUrl,
      imageType,
      imageBase64Length: imageBase64.length,
    })
    response = await fetch(`${backendBaseUrl}/api/v1/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Request-ID': requestId,
      },
      body: JSON.stringify({
        image_base64: imageBase64,
        image_type: imageType,
      } as BackendAnalyzeRequest),
    })
  } catch (err) {
    const reason = err instanceof Error ? err.message : String(err)
    console.error("[analyze] request_network_failed", { requestId, reason })
    throw new Error(`网络请求失败（可能是 CORS 或后端不可达，requestId=${requestId}）: ${reason}`)
  }

  const responseRequestId = response.headers.get("x-request-id") || requestId
  console.info("[analyze] request_done", {
    requestId: responseRequestId,
    status: response.status,
    ok: response.ok,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: "请求失败" }))
    const message =
      error.error ||
      error.detail ||
      error.message ||
      `HTTP ${response.status}: ${response.statusText}`
    throw new Error(`${message} (requestId=${responseRequestId})`)
  }

  const result = await response.json()
  if (result?.error) {
    console.warn("[analyze] backend_returned_error", {
      requestId: responseRequestId,
      errorType: result.error_type,
      error: result.error,
    })
  }
  return result
}

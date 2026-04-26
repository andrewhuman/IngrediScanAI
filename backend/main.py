"""
IngrediScan AI Backend Service
FastAPI 后端服务，集成 RapidOCR 和 OpenRouter 多模态模型
"""

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import io
from PIL import Image
import os
import uuid
from typing import Optional
import logging
import threading
from starlette.datastructures import Headers

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

# 导入 OCR 和 VLM 模块
from services.ocr_service import OCRService
from services.vlm_service import VLMService
from services.runtime_logging import elapsed_ms, memory_snapshot, now_ms, text_preview

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _read_float_env(env_name: str, default: float) -> float:
    raw_value = os.getenv(env_name, "").strip()
    if not raw_value:
        return default
    try:
        return float(raw_value)
    except ValueError:
        logger.warning("环境变量 %s=%r 不是有效浮点数，使用默认值 %s", env_name, raw_value, default)
        return default


def init_sentry() -> None:
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        logger.info("Sentry 未启用：SENTRY_DSN 未设置")
        return
    if not SENTRY_AVAILABLE:
        logger.error("检测到 SENTRY_DSN，但 sentry-sdk 未安装")
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "production")),
        traces_sample_rate=_read_float_env("SENTRY_TRACES_SAMPLE_RATE", 0.1),
        profiles_sample_rate=_read_float_env("SENTRY_PROFILES_SAMPLE_RATE", 0.0),
        integrations=[
            FastApiIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        send_default_pii=False,
    )
    logger.info("Sentry 已启用")


class LoggingCORSMiddleware(CORSMiddleware):
    """在 CORS 预检失败时输出详细上下文，便于定位 Render 上的 400 OPTIONS。"""

    def preflight_response(self, request_headers: Headers):
        response = super().preflight_response(request_headers)
        if response.status_code >= 400:
            origin = request_headers.get("origin", "")
            req_method = request_headers.get("access-control-request-method", "")
            req_headers = request_headers.get("access-control-request-headers", "")
            allow_regex = self.allow_origin_regex.pattern if self.allow_origin_regex else ""
            logger.warning(
                "CORS preflight blocked: origin=%s method=%s req_headers=%s allow_origins=%s allow_origin_regex=%s",
                origin,
                req_method,
                req_headers,
                list(self.allow_origins),
                allow_regex,
            )
        return response


init_sentry()

app = FastAPI(
    title="IngrediScan AI API",
    description="食品成分分析 API，集成 OCR 和 VLM 模型",
    version="1.0.0"
)

def _load_cors_allowed_origins() -> list[str]:
    raw_origins = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    normalized: list[str] = []
    for origin in raw_origins.split(","):
        candidate = origin.strip()
        if not candidate:
            continue
        # Origin 头本身不包含路径，去掉末尾 / 避免配置误差导致不匹配。
        candidate = candidate.rstrip("/")
        if candidate:
            normalized.append(candidate)
    return normalized


cors_allowed_origins = _load_cors_allowed_origins()
cors_allowed_origin_regex = os.getenv(
    "CORS_ALLOWED_ORIGIN_REGEX",
    (
        r"^https://.*\.vercel\.app$"
        r"|^http://localhost(:\d+)?$"
        r"|^http://127\.0\.0\.1(:\d+)?$"
        r"|^http://192\.168\.\d{1,3}\.\d{1,3}(:\d+)?$"
        r"|^http://10\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?$"
        r"|^http://172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}(:\d+)?$"
        r"|^http://.*\.local(:\d+)?$"
    ),
)

logger.info("CORS allowed origins: %s", cors_allowed_origins)
if cors_allowed_origin_regex:
    logger.info("CORS allowed origin regex: %s", cors_allowed_origin_regex)
if any("your-frontend" in origin for origin in cors_allowed_origins):
    logger.warning("CORS_ALLOWED_ORIGINS 仍包含占位符，请替换为真实前端域名")
if cors_allowed_origins and all(
    origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1")
    for origin in cors_allowed_origins
):
    logger.warning("CORS_ALLOWED_ORIGINS 当前仅包含本地域名，线上前端请求会被拦截")

# CORS 配置（前端直连后端）
app.add_middleware(
    LoggingCORSMiddleware,
    allow_origins=cors_allowed_origins,
    allow_origin_regex=cors_allowed_origin_regex or None,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# 初始化服务
vlm_service = VLMService()
_ocr_service: OCRService | None = None
_ocr_service_lock = threading.Lock()


def get_ocr_service() -> OCRService:
    """延迟初始化 OCR，降低服务启动耗时和冷启动内存压力。"""
    global _ocr_service
    if _ocr_service is None:
        with _ocr_service_lock:
            if _ocr_service is None:
                start_ms = now_ms()
                logger.info("ocr_lazy_init_start %s", memory_snapshot())
                _ocr_service = OCRService()
                logger.info(
                    "ocr_lazy_init_done elapsed_ms=%s %s",
                    elapsed_ms(start_ms),
                    memory_snapshot(),
                )
    return _ocr_service


class AnalyzeRequest(BaseModel):
    image_base64: str
    image_type: str = "image/jpeg"


class RiskItem(BaseModel):
    level: str  # "High", "Moderate", "Low"
    name: str
    desc: str


class IngredientDetail(BaseModel):
    name: str
    description: Optional[str] = None


class AnalyzeResponse(BaseModel):
    health_score: str  # "A", "B", "C", "D", "E"
    summary: str
    risks: list[RiskItem]
    full_ingredients: list[str]
    ingredients_detail: Optional[list[IngredientDetail]] = None  # 详细描述（如果 API 返回）
    alternatives: list[str]
    confidence: Optional[float] = None
    error: Optional[str] = None  # 错误信息（如果分析失败）
    error_type: Optional[str] = None  # 错误类型：invalid_image, api_error, parse_error 等


def decode_base64_image(image_base64: str, request_id: str = "-") -> Image.Image:
    """将 Base64 字符串解码为 PIL Image"""
    try:
        # 移除 data URL 前缀（如果存在）
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        logger.info(
            "analyze_image_decoded request_id=%s image_bytes=%s size=%s mode=%s format=%s %s",
            request_id,
            len(image_data),
            image.size,
            image.mode,
            image.format,
            memory_snapshot(),
        )
        return image
    except Exception as e:
        logger.error(
            "analyze_image_decode_failed request_id=%s error=%s payload_base64_len=%s %s",
            request_id,
            e,
            len(image_base64 or ""),
            memory_snapshot(),
        )
        raise HTTPException(status_code=400, detail=f"无效的图片数据: {str(e)}")


@app.get("/")
async def root():
    return {"message": "IngrediScan AI Backend Service", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze_product(request: Request, response: Response, payload: AnalyzeRequest):
    """
    分析产品图片的主接口
    
    流程：
    1. 解码 Base64 图片
    2. OCR 提取文字
    3. VLM 分析成分和健康风险
    4. 返回结构化结果
    """
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    response.headers["X-Request-ID"] = request_id
    total_start_ms = now_ms()
    origin = request.headers.get("origin", "-")
    user_agent = text_preview(request.headers.get("user-agent", "-"), 180)

    try:
        logger.info(
            "analyze_start request_id=%s origin=%s image_type=%s payload_base64_len=%s user_agent=%s %s",
            request_id,
            origin,
            payload.image_type,
            len(payload.image_base64 or ""),
            user_agent,
            memory_snapshot(),
        )
        
        # Step 1: 解码图片
        step_ms = now_ms()
        image = decode_base64_image(payload.image_base64, request_id=request_id)
        logger.info(
            "analyze_decode_done request_id=%s elapsed_ms=%s size=%s %s",
            request_id,
            elapsed_ms(step_ms),
            image.size,
            memory_snapshot(),
        )
        
        # Step 2: 跳过 OCR，Render 免费实例上 RapidOCR 耗时和内存压力过高。
        step_ms = now_ms()
        ocr_text = ""
        logger.info(
            "analyze_ocr_skipped request_id=%s elapsed_ms=%s reason=disabled_for_render_free_tier %s",
            request_id,
            elapsed_ms(step_ms),
            memory_snapshot(),
        )
        
        # Step 3: VLM 分析
        step_ms = now_ms()
        logger.info("analyze_vlm_start request_id=%s %s", request_id, memory_snapshot())
        analysis_result = await vlm_service.analyze_ingredients(
            image=image,
            ocr_text=ocr_text,
            request_id=request_id,
        )
        logger.info(
            "analyze_vlm_done request_id=%s elapsed_ms=%s error_type=%s has_error=%s %s",
            request_id,
            elapsed_ms(step_ms),
            analysis_result.error_type,
            bool(analysis_result.error),
            memory_snapshot(),
        )
        
        # Step 4: 返回结果
        logger.info(
            "analyze_done request_id=%s total_elapsed_ms=%s result_error_type=%s result_score=%s %s",
            request_id,
            elapsed_ms(total_start_ms),
            analysis_result.error_type,
            analysis_result.health_score,
            memory_snapshot(),
        )
        return analysis_result
        
    except HTTPException:
        logger.warning(
            "analyze_http_exception request_id=%s total_elapsed_ms=%s %s",
            request_id,
            elapsed_ms(total_start_ms),
            memory_snapshot(),
            exc_info=True,
        )
        raise
    except Exception as e:
        logger.error(
            "analyze_unhandled_exception request_id=%s total_elapsed_ms=%s error=%s %s",
            request_id,
            elapsed_ms(total_start_ms),
            e,
            memory_snapshot(),
            exc_info=True,
        )
        
        # 根据错误类型返回不同的错误信息
        error_message = str(e)
        if "图片" in error_message or "image" in error_message.lower() or "decode" in error_message.lower():
            error_type = "invalid_image"
            user_message = "图片格式错误或无法解析，请上传清晰的商品标签图片"
        elif "OCR" in error_message or "ocr" in error_message.lower():
            error_type = "parse_error"
            user_message = "图片文字识别失败，请上传更清晰的商品标签图片"
        elif "网络" in error_message or "network" in error_message.lower() or "连接" in error_message:
            error_type = "api_error"
            user_message = "网络连接问题，请检查网络后重试"
        else:
            error_type = "server_error"
            user_message = f"服务器处理出错：{error_message}"
        
        # 返回错误信息而不是抛出异常，让前端可以显示错误
        result = AnalyzeResponse(
            health_score="",
            summary="",
            risks=[],
            full_ingredients=[],
            alternatives=[],
            error=user_message,
            error_type=error_type
        )
        logger.info(
            "analyze_done request_id=%s total_elapsed_ms=%s result_error_type=%s result_score=%s %s",
            request_id,
            elapsed_ms(total_start_ms),
            result.error_type,
            result.health_score,
            memory_snapshot(),
        )
        return result


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    # 使用当前 Python 环境运行，确保使用正确的依赖
    uvicorn.run(app, host="0.0.0.0", port=port)

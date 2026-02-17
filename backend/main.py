"""
IngrediScan AI Backend Service
FastAPI 后端服务，集成 RapidOCR 和 OpenRouter 多模态模型
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import io
from PIL import Image
import os
from typing import Optional
import logging
import threading

# 导入 OCR 和 VLM 模块
from services.ocr_service import OCRService
from services.vlm_service import VLMService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


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

# CORS 配置（前端直连后端）
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins,
    allow_origin_regex=cors_allowed_origin_regex or None,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
                logger.info("初始化 OCR 引擎（lazy load）...")
                _ocr_service = OCRService()
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


def decode_base64_image(image_base64: str) -> Image.Image:
    """将 Base64 字符串解码为 PIL Image"""
    try:
        # 移除 data URL 前缀（如果存在）
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        return image
    except Exception as e:
        logger.error(f"图片解码失败: {e}")
        raise HTTPException(status_code=400, detail=f"无效的图片数据: {str(e)}")


@app.get("/")
async def root():
    return {"message": "IngrediScan AI Backend Service", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze_product(request: AnalyzeRequest):
    """
    分析产品图片的主接口
    
    流程：
    1. 解码 Base64 图片
    2. OCR 提取文字
    3. VLM 分析成分和健康风险
    4. 返回结构化结果
    """
    try:
        logger.info("开始分析产品图片...")
        
        # Step 1: 解码图片
        image = decode_base64_image(request.image_base64)
        logger.info(f"图片解码成功，尺寸: {image.size}")
        
        # Step 2: OCR 提取文字
        logger.info("开始 OCR 文字提取...")
        ocr_service = get_ocr_service()
        ocr_text = await ocr_service.extract_text(image)
        logger.info(f"OCR 提取完成，文字长度: {len(ocr_text)}")
        
        # Step 3: VLM 分析
        logger.info("开始 VLM 分析...")
        analysis_result = await vlm_service.analyze_ingredients(
            image=image,
            ocr_text=ocr_text
        )
        logger.info("VLM 分析完成")
        
        # Step 4: 返回结果
        return analysis_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析过程出错: {e}", exc_info=True)
        
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
        return AnalyzeResponse(
            health_score="",
            summary="",
            risks=[],
            full_ingredients=[],
            alternatives=[],
            error=user_message,
            error_type=error_type
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    # 使用当前 Python 环境运行，确保使用正确的依赖
    uvicorn.run(app, host="0.0.0.0", port=port)

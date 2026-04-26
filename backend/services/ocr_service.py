"""
OCR 服务 - 使用 RapidOCR 进行文字提取
"""

import logging
from PIL import Image
from typing import Optional
import numpy as np
from services.runtime_logging import elapsed_ms, memory_snapshot, now_ms

logger = logging.getLogger(__name__)

try:
    from rapidocr_onnxruntime import RapidOCR
    RAPIDOCR_AVAILABLE = True
except ImportError:
    RAPIDOCR_AVAILABLE = False
    logger.warning("RapidOCR 未安装，OCR 功能将不可用。请运行: pip install rapidocr-onnxruntime")


class OCRService:
    """OCR 服务类，使用 RapidOCR 提取图片中的文字"""
    
    def __init__(self):
        self.ocr_engine = None
        if RAPIDOCR_AVAILABLE:
            try:
                # 初始化 RapidOCR（CPU 版本）
                start_ms = now_ms()
                logger.info("ocr_engine_init_start %s", memory_snapshot())
                self.ocr_engine = RapidOCR()
                logger.info(
                    "ocr_engine_init_done elapsed_ms=%s %s",
                    elapsed_ms(start_ms),
                    memory_snapshot(),
                )
            except Exception as e:
                logger.error("ocr_engine_init_failed error=%s %s", e, memory_snapshot(), exc_info=True)
                self.ocr_engine = None
        else:
            logger.warning("RapidOCR 不可用，将返回空字符串")
    
    async def extract_text(self, image: Image.Image, request_id: str = "-") -> str:
        """
        从图片中提取文字
        
        Args:
            image: PIL Image 对象
            
        Returns:
            提取的文字字符串，如果 OCR 失败则返回空字符串
        """
        if not self.ocr_engine:
            logger.warning("ocr_unavailable request_id=%s %s", request_id, memory_snapshot())
            return ""
        
        try:
            start_ms = now_ms()
            logger.info(
                "ocr_extract_start request_id=%s image_size=%s image_mode=%s %s",
                request_id,
                image.size,
                image.mode,
                memory_snapshot(),
            )
            # 将 PIL Image 转换为 numpy array
            img_array = np.array(image)
            logger.info(
                "ocr_numpy_ready request_id=%s elapsed_ms=%s array_shape=%s array_dtype=%s array_bytes=%s %s",
                request_id,
                elapsed_ms(start_ms),
                img_array.shape,
                img_array.dtype,
                img_array.nbytes,
                memory_snapshot(),
            )
            
            # 执行 OCR
            result, _ = self.ocr_engine(img_array)
            
            if not result:
                logger.warning(
                    "ocr_no_text request_id=%s elapsed_ms=%s %s",
                    request_id,
                    elapsed_ms(start_ms),
                    memory_snapshot(),
                )
                return ""
            
            # 合并所有检测到的文字
            text_lines = [item[1] for item in result if len(item) > 1]
            full_text = "\n".join(text_lines)
            
            logger.info(
                "ocr_extract_done request_id=%s elapsed_ms=%s line_count=%s text_len=%s %s",
                request_id,
                elapsed_ms(start_ms),
                len(text_lines),
                len(full_text),
                memory_snapshot(),
            )
            return full_text
            
        except Exception as e:
            logger.error(
                "ocr_extract_failed request_id=%s error=%s %s",
                request_id,
                e,
                memory_snapshot(),
                exc_info=True,
            )
            # OCR 失败时返回空字符串，让 VLM 仅通过视觉分析
            return ""

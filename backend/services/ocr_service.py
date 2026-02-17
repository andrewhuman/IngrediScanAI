"""
OCR 服务 - 使用 RapidOCR 进行文字提取
"""

import logging
from PIL import Image
from typing import Optional
import numpy as np

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
                self.ocr_engine = RapidOCR()
                logger.info("RapidOCR 初始化成功")
            except Exception as e:
                logger.error(f"RapidOCR 初始化失败: {e}")
                self.ocr_engine = None
        else:
            logger.warning("RapidOCR 不可用，将返回空字符串")
    
    async def extract_text(self, image: Image.Image) -> str:
        """
        从图片中提取文字
        
        Args:
            image: PIL Image 对象
            
        Returns:
            提取的文字字符串，如果 OCR 失败则返回空字符串
        """
        if not self.ocr_engine:
            logger.warning("OCR 引擎未初始化，返回空字符串")
            return ""
        
        try:
            # 将 PIL Image 转换为 numpy array
            img_array = np.array(image)
            
            # 执行 OCR
            result, _ = self.ocr_engine(img_array)
            
            if not result:
                logger.warning("OCR 未检测到文字")
                return ""
            
            # 合并所有检测到的文字
            text_lines = [item[1] for item in result if len(item) > 1]
            full_text = "\n".join(text_lines)
            
            logger.info(f"OCR 提取到 {len(text_lines)} 行文字")
            return full_text
            
        except Exception as e:
            logger.error(f"OCR 提取失败: {e}", exc_info=True)
            # OCR 失败时返回空字符串，让 VLM 仅通过视觉分析
            return ""

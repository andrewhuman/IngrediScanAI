"""
VLM 服务 - 使用 OpenRouter 多模态模型进行成分分析
"""

import os
import logging
import base64
import io
import httpx
from PIL import Image
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 尝试导入 OpenAI SDK（用于调用 OpenRouter OpenAI-Compatible API）
try:
    from openai import OpenAI
    OPENROUTER_SDK_AVAILABLE = True
except ImportError:
    OPENROUTER_SDK_AVAILABLE = False
    logger.warning("OpenAI SDK 未安装，请运行: pip install openai")


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
    full_ingredients: list[str]  # 保持向后兼容，存储名称列表
    ingredients_detail: Optional[list[IngredientDetail]] = None  # 详细描述（如果 API 返回）
    alternatives: list[str]
    confidence: Optional[float] = None
    error: Optional[str] = None  # 错误信息（如果分析失败）
    error_type: Optional[str] = None  # 错误类型：invalid_image, api_error, parse_error 等


class VLMService:
    """VLM 服务类，使用 OpenRouter 多模态模型进行成分分析"""
    
    def __init__(self):
        self.api_key = None
        self.client = None
        self.model_name = os.getenv(
            "OPENROUTER_MODEL",
            "nvidia/nemotron-nano-12b-v2-vl:free",
        )
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        
        if OPENROUTER_SDK_AVAILABLE:
            # 从环境变量获取 API Key
            self.api_key = os.getenv("OPENROUTER_API_KEY")
            if self.api_key:
                default_headers = {}
                site_url = os.getenv("OPENROUTER_SITE_URL", "").strip()
                app_name = os.getenv("OPENROUTER_APP_NAME", "IngrediScan AI").strip()
                if site_url:
                    default_headers["HTTP-Referer"] = site_url
                if app_name:
                    default_headers["X-Title"] = app_name

                client_kwargs = {
                    "base_url": self.base_url,
                    "api_key": self.api_key,
                }
                if default_headers:
                    client_kwargs["default_headers"] = default_headers

                try:
                    self.client = OpenAI(**client_kwargs)
                    logger.info("OpenRouter API Key 已配置，模型: %s", self.model_name)
                except Exception as e:
                    # 某些环境下 ALL_PROXY=socks://... 会导致 httpx 抛 Unknown scheme 错误
                    if "Unknown scheme for proxy URL" in str(e):
                        logger.warning(
                            "检测到代理配置不兼容，已改为忽略系统代理变量并重试 OpenRouter 客户端初始化"
                        )
                        try:
                            self.client = OpenAI(
                                **client_kwargs,
                                http_client=httpx.Client(trust_env=False),
                            )
                            logger.info(
                                "OpenRouter 客户端已在禁用环境代理模式下初始化成功，模型: %s",
                                self.model_name,
                            )
                        except Exception as e2:
                            self.client = None
                            logger.error("OpenRouter 客户端初始化失败: %s", e2)
                    else:
                        self.client = None
                        logger.error("OpenRouter 客户端初始化失败: %s", e)
            else:
                logger.warning("未设置 OPENROUTER_API_KEY 环境变量")
        else:
            logger.warning("OpenRouter SDK 不可用")
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """将 PIL Image 转换为 Base64 字符串"""
        # 确保图片为 RGB 模式（JPEG 不支持 RGBA）
        if image.mode != "RGB":
            image = image.convert("RGB")
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return img_base64
    
    def _parse_json_response(self, text: str) -> dict:
        """
        健壮的 JSON 解析器，具有高容错率
        
        处理以下情况：
        1. JSON 被 markdown 代码块包裹 (```json ... ```)
        2. JSON 中包含单引号而非双引号
        3. JSON 中包含尾随逗号
        4. JSON 中包含注释
        5. JSON 格式不完整但可修复
        """
        import json
        import re
        
        # 1. 移除 markdown 代码块标记
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*$', '', text)
        text = text.strip()
        
        # 2. 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 3. 提取 JSON 对象（匹配最外层的大括号）
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = text
        
        # 4. 修复常见的 JSON 问题
        # 4.1 移除单行注释
        json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
        # 4.2 移除多行注释
        json_str = re.sub(r'/\*[\s\S]*?\*/', '', json_str)
        # 4.3 移除尾随逗号（在对象和数组的最后一个元素后）
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # 4.4 尝试解析修复后的 JSON
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # 5. 更激进的修复：将单引号替换为双引号（但要小心处理字符串内容）
        # 使用正则表达式匹配字符串内容，避免破坏字符串内的单引号
        def fix_quotes(match):
            content = match.group(1)
            # 如果内容包含双引号，需要转义
            content = content.replace('"', '\\"')
            return f'"{content}"'
        
        # 匹配单引号字符串
        json_str = re.sub(r"'([^']*)'", fix_quotes, json_str)
        # 再次移除尾随逗号
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败，尝试最后一种方法: {e}")
            # 6. 最后尝试：使用 ast.literal_eval（仅当 JSON 格式接近 Python 字典时）
            try:
                import ast
                # 将单引号字典转换为双引号 JSON
                safe_str = text.replace("'", '"')
                # 尝试解析为 Python 字面量
                if safe_str.strip().startswith('{'):
                    # 使用 eval 作为最后手段（仅限受控环境）
                    # 注意：在生产环境中应该避免使用 eval
                    # 这里仅作为容错手段
                    try:
                        result = ast.literal_eval(text.replace('true', 'True').replace('false', 'False').replace('null', 'None'))
                        # 转换回标准 JSON 格式
                        return json.loads(json.dumps(result))
                    except:
                        pass
            except Exception as e2:
                logger.error(f"所有 JSON 解析方法都失败: {e2}")
            
            # 如果所有方法都失败，记录错误并返回包含错误信息的字典
            logger.error(f"JSON 解析失败，原始文本前500字符: {text[:500]}")
            logger.error(f"JSON 解析错误详情: {e}")
            # 返回错误信息，而不是空字典
            return {
                "error": "数据解析失败，可能是图片类型不正确或 API 返回格式异常，请重新上传清晰的商品标签图片",
                "error_type": "parse_error"
            }
    
    def _build_prompt(self, ocr_text: str) -> str:
        """构建发送给 VLM 的提示词"""
        prompt = """你是一位专业的食品营养学家。请根据提供的商品包装图片和 OCR 文字，识别所有成分。

**重要：图片类型判断（宽松标准）**
在开始分析之前，请先简单判断上传的图片是否可能是商品包装标签图。

**判断原则（宽松标准，只要可能是就进行分析）：**
- ✅ 应该分析：任何包含商品包装、标签、文字信息的图片（食品、化妆品、药品、日用品等），即使图片不完整或模糊，只要可能是商品标签图就进行分析
- ❌ 不应该分析：明显不是商品相关的图片，如纯风景照、纯人物照、纯动物照、纯自拍、纯截图、纯文字文档等

**只有在图片明显不是商品标签图时（如纯风景、纯人物、纯动物照片），才返回以下 JSON：**
{
  "error": "上传的图片不是商品标签图，请上传包含成分信息的商品包装图片",
  "error_type": "invalid_image"
}

**注意：如果图片可能是商品标签图（即使不完整、模糊或角度不佳），都应该继续进行分析，不要返回错误。**

请按照以下要求分析：

1. **识别所有成分**：列出产品包装上的所有成分（包括添加剂、防腐剂等）

2. **计算健康评分 (Health Score)**：
   - A: 非常健康（≥80% 健康成分）
   - B: 较健康（50-79% 健康成分）
   - C: 一般（30-49% 健康成分）
   - D: 不健康（10-29% 健康成分）
   - E: 非常不健康（<10% 健康成分）

3. **风险分类**：
   - **High Risk**: 高风险成分（如人工甜味剂、反式脂肪、高钠、过敏源等）
   - **Moderate Risk**: 中等风险成分（如高糖、防腐剂、人工色素等）
   - **Low Risk**: 低风险成分（天然成分，适量食用安全）

4. **为每个风险成分提供**：
   - 成分名称（如果包含 E 编号，请保留）
   - 简短的科学解释
   - 适用人群建议

5. **完整成分列表 (full_ingredients)**：
   - 必须列出产品中的所有成分
   - 每个成分应包含：
     * name: 成分名称
     * description: 详细的科学解释、健康影响、适用人群建议
   - 即使是安全成分，也要提供简要说明

6. **提供 1-2 个更健康的替代品建议**

请以 JSON 格式返回结果，严格遵循以下结构：

**如果图片是商品标签图，返回：**
{
  "health_score": "B",
  "summary": "Fair - 50% Healthy",
  "risks": [
    {
      "level": "High",
      "name": "Aspartame (E951)",
      "desc": "人工甜味剂，可能引起头痛或消化不适。孕妇和苯丙酮尿症患者应避免。"
    },
    {
      "level": "Moderate",
      "name": "Honey",
      "desc": "天然甜味剂，但含糖量高。糖尿病患者应监控摄入量。"
    }
  ],
  "full_ingredients": [
    {
      "name": "Organic Oats",
      "description": "有机燕麦，富含膳食纤维和复合碳水化合物，有助于维持血糖稳定。适合大多数人群，是优质的全谷物来源。"
    },
    {
      "name": "Honey",
      "description": "天然甜味剂，含有抗氧化物质和微量矿物质。虽然天然，但仍为糖类，糖尿病患者应控制摄入量。"
    }
  ],
  "alternatives": ["Natural Stevia Oats", "Unsweetened Granola"]
}

**如果图片不是商品标签图，返回：**
{
  "error": "上传的图片不是商品标签图，请上传包含成分信息的商品包装图片",
  "error_type": "invalid_image"
}

如果 OCR 文字为空或模糊，请仅通过视觉分析图片中的成分信息。"""
        
        if ocr_text and ocr_text.strip():
            logger.debug(f"OCR 提取的文字内容: {ocr_text[:200]}...")
            prompt += f"\n\nOCR 提取的文字内容：\n{ocr_text}"
        else:
            prompt += "\n\n注意：OCR 未能提取到文字，请仅通过视觉分析图片。"
        
        return prompt

    def _extract_response_text(self, content: object) -> str:
        """从 OpenRouter Chat Completions 响应中提取文本"""
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text" and item.get("text"):
                        parts.append(str(item["text"]))
                    elif "text" in item:
                        parts.append(str(item["text"]))
                    else:
                        parts.append(str(item))
                else:
                    text = getattr(item, "text", None)
                    if text:
                        parts.append(str(text))
                    else:
                        parts.append(str(item))
            return "".join(parts).strip()

        if content is None:
            return ""

        return str(content)
    
    async def analyze_ingredients(
        self,
        image: Image.Image,
        ocr_text: str = ""
    ) -> AnalyzeResponse:
        """
        分析产品成分
        
        Args:
            image: PIL Image 对象
            ocr_text: OCR 提取的文字
            
        Returns:
            AnalyzeResponse 对象
        """
        if not OPENROUTER_SDK_AVAILABLE or not self.api_key or not self.client:
            logger.error("OpenRouter API 不可用：缺少可用客户端或 API Key")
            return AnalyzeResponse(
                health_score="",
                summary="",
                risks=[],
                full_ingredients=[],
                alternatives=[],
                error="VLM 服务不可用：请检查 OPENROUTER_API_KEY 和 OpenRouter 客户端配置",
                error_type="api_error",
            )
        
        try:
            # 转换图片为 Base64
            img_base64 = self._image_to_base64(image)
            logger.info(f"ocr_text: {ocr_text}")
            # 构建提示词
            prompt = self._build_prompt(ocr_text)
            
            # 调用 OpenRouter API（OpenAI-compatible Chat Completions）
            logger.info("调用 OpenRouter VLM API...")
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}"
                            },
                        }
                    ]
                }
            ]
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=2000
            )

            if not response.choices:
                raise Exception("API 响应为空，未返回候选结果")

            # 获取响应内容（可能是字符串或内容块列表）
            content = response.choices[0].message.content
            result_text = self._extract_response_text(content)
            
            if not result_text:
                logger.error(f"无法从响应中提取文本，响应内容: {content}")
                raise Exception("API 响应格式异常，无法提取文本内容")
            
            logger.info(f"API 返回文本长度: {result_text}")
            
            # 提取并解析 JSON（使用健壮的解析器）
            result_data = self._parse_json_response(result_text)
            
            # 检查解析结果是否为空（解析失败）
            if not result_data:
                logger.error("JSON 解析失败，无法提取数据")
                return AnalyzeResponse(
                    health_score="",
                    summary="",
                    risks=[],
                    full_ingredients=[],
                    alternatives=[],
                    error="数据解析失败，请尝试重新上传图片或检查图片是否为商品标签图",
                    error_type="parse_error"
                )
            
            # 检查是否有错误信息（图片类型错误等）- 优先检查
            if result_data.get("error"):
                error_msg = result_data.get("error", "分析失败")
                error_type = result_data.get("error_type", "unknown_error")
                logger.info(f"检测到错误: {error_type} - {error_msg}")
                return AnalyzeResponse(
                    health_score="",
                    summary="",
                    risks=[],
                    full_ingredients=[],
                    alternatives=[],
                    error=error_msg,
                    error_type=error_type
                )
            
            # 如果解析结果为空字典，说明解析失败
            if result_data == {}:
                logger.error("JSON 解析返回空字典")
                return AnalyzeResponse(
                    health_score="",
                    summary="",
                    risks=[],
                    full_ingredients=[],
                    alternatives=[],
                    error="数据解析失败，可能是图片类型不正确，请上传清晰的商品标签图片",
                    error_type="parse_error"
                )
            
            # 处理 full_ingredients：可能是字符串列表或对象列表
            full_ingredients_raw = result_data.get("full_ingredients", [])
            full_ingredients = []
            ingredients_detail = []
            
            for item in full_ingredients_raw:
                if isinstance(item, dict):
                    # 如果是对象，提取名称和描述
                    name = item.get("name", str(item))
                    description = item.get("description", item.get("desc", ""))
                    full_ingredients.append(name)
                    if description:
                        ingredients_detail.append(IngredientDetail(name=name, description=description))
                elif isinstance(item, str):
                    # 如果是字符串，直接使用
                    full_ingredients.append(item)
                else:
                    name = str(item)
                    full_ingredients.append(name)
            
            # 转换为响应模型
            return AnalyzeResponse(
                health_score=result_data.get("health_score", "C"),
                summary=result_data.get("summary", "Unknown"),
                risks=[
                    RiskItem(**risk) if isinstance(risk, dict) else RiskItem(
                        level=risk.get("level", "Low") if isinstance(risk, dict) else "Low",
                        name=risk.get("name", str(risk)) if isinstance(risk, dict) else str(risk),
                        desc=risk.get("desc", "") if isinstance(risk, dict) else ""
                    ) for risk in result_data.get("risks", [])
                ],
                full_ingredients=full_ingredients,
                ingredients_detail=ingredients_detail if ingredients_detail else None,
                alternatives=result_data.get("alternatives", []),
                confidence=result_data.get("confidence", 0.8),
                error=None,
                error_type=None
            )
            
        except Exception as e:
            logger.error(f"VLM 分析失败: {e}", exc_info=True)
            # 失败时返回错误信息，而不是模拟数据
            error_message = str(e)
            lowered = error_message.lower()
            if "api" in lowered or "openrouter" in lowered or "status code" in lowered:
                error_type = "api_error"
            elif "JSON 解析" in error_message or "解析" in error_message:
                error_type = "parse_error"
            else:
                error_type = "unknown_error"
            
            return AnalyzeResponse(
                health_score="",
                summary="",
                risks=[],
                full_ingredients=[],
                alternatives=[],
                error=f"分析失败：{error_message}",
                error_type=error_type
            )

"""
PDF Parser - 使用 marker-pdf v1.10+ 进行高精度 PDF 转 Markdown
"""
import os
import asyncio
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

# 全局缓存 converter 实例（模型加载很慢，只做一次）
_converter = None


def get_converter():
    global _converter
    if _converter is None:
        print("[PDF Parser] 正在加载 Marker 模型，首次加载可能需要数分钟...")
        _converter = PdfConverter(
            artifact_dict=create_model_dict(),
        )
        print("[PDF Parser] Marker 模型加载完毕")
    return _converter


def _sync_parse(file_path: str) -> str:
    """同步执行 PDF 解析（marker 是阻塞操作）"""
    converter = get_converter()
    rendered = converter(file_path)
    text, _, images = text_from_rendered(rendered)
    return text


async def parse_pdf(file_path: str) -> str:
    """
    将 PDF 文件转换为 Markdown 文本（包含 LaTeX 公式）
    使用 asyncio.to_thread 避免阻塞事件循环
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF 文件未找到: {file_path}")

    # 在线程池中运行同步阻塞操作，不阻塞事件循环
    text = await asyncio.to_thread(_sync_parse, file_path)
    return text

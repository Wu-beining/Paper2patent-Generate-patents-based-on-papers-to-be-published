"""
PDF Parser - 使用 PyMuPDF (fitz) 进行快速文本提取
学术论文通常是电子版 PDF（非扫描件），不需要 OCR，PyMuPDF 速度极快（秒级）。
"""
import os
import asyncio

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

# marker 作为 OCR 回退（扫描件 PDF）
try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import text_from_rendered
    HAS_MARKER = True
except ImportError:
    HAS_MARKER = False

# 全局缓存 marker converter
_converter = None


def _get_marker_converter():
    global _converter
    if _converter is None:
        print("[PDF Parser] 正在加载 Marker OCR 模型...")
        _converter = PdfConverter(artifact_dict=create_model_dict())
        print("[PDF Parser] Marker 模型加载完毕")
    return _converter


def _parse_with_pymupdf(file_path: str) -> str:
    """使用 PyMuPDF 快速提取文本（适用于电子版 PDF）"""
    doc = fitz.open(file_path)
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            pages.append(text)
    doc.close()

    full_text = "\n\n".join(pages)

    # 判断是否提取到了有意义的文本
    # 如果文本太少（可能是扫描件），回退到 marker
    if len(full_text.strip()) < 200:
        return ""  # 信号：需要 OCR 回退
    return full_text


def _parse_with_marker(file_path: str) -> str:
    """使用 Marker 进行 OCR 级解析（适用于扫描件）"""
    converter = _get_marker_converter()
    rendered = converter(file_path)
    text, _, images = text_from_rendered(rendered)
    return text


async def parse_pdf(file_path: str) -> str:
    """
    将 PDF 文件转换为文本。
    优先使用 PyMuPDF（秒级速度），若提取文本不足则回退到 Marker（OCR）。
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF 文件未找到: {file_path}")

    # 方案1: PyMuPDF 快速提取（99% 学术论文适用）
    if HAS_PYMUPDF:
        print(f"[PDF Parser] 使用 PyMuPDF 快速提取: {file_path}")
        text = await asyncio.to_thread(_parse_with_pymupdf, file_path)
        if text:
            print(f"[PDF Parser] PyMuPDF 提取成功，{len(text)} 字符")
            return text
        print("[PDF Parser] PyMuPDF 提取文本不足，尝试 Marker OCR 回退...")

    # 方案2: Marker OCR 回退（扫描件）
    if HAS_MARKER:
        print(f"[PDF Parser] 使用 Marker OCR 解析: {file_path}")
        text = await asyncio.to_thread(_parse_with_marker, file_path)
        print(f"[PDF Parser] Marker OCR 完成，{len(text)} 字符")
        return text

    raise RuntimeError("无可用的 PDF 解析器。请安装 PyMuPDF (pip install pymupdf) 或 marker-pdf。")

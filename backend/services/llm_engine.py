"""
LLM Engine - OpenRouter API 封装
支持运行时动态注入 API Key
"""
import os
import re
import base64
from typing import AsyncGenerator, Dict, List, Optional, Tuple
from openai import AsyncOpenAI

# Default config from env
DEFAULT_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
SITE_URL = os.getenv("SITE_URL", "http://localhost:3000")
SITE_NAME = os.getenv("SITE_NAME", "Auto-Patent Architect")

# Model IDs
MODEL_GEMINI_PRO = "google/gemini-3-pro-preview"
MODEL_GPT = "openai/gpt-5.2"
MODEL_IMAGE_GEN = "google/gemini-3-pro-image-preview"

# 全局输出格式约束（加在每个 prompt 末尾）
OUTPUT_CONSTRAINT = """

【重要输出要求】
1. 请直接输出最终成果正文，不要输出你的思考过程、分析步骤或任何解释性说明。
2. 不要使用 Markdown 格式标记（如 **加粗**、# 标题、- 列表符号、```代码块```），请用纯文本输出。
3. 章节标题请直接写文字，不要加任何标记符号。
4. 输出内容应可直接粘贴到 Word 文档中使用。"""


def get_client(api_key: Optional[str] = None) -> AsyncOpenAI:
    """获取 OpenAI 客户端，支持运行时注入 API Key"""
    key = api_key or DEFAULT_API_KEY
    if not key:
        raise ValueError("OpenRouter API Key 未配置。请在前端输入您的 API Key。")
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=key,
        default_headers={
            "HTTP-Referer": SITE_URL,
            "X-Title": SITE_NAME,
        },
    )


async def stream_completion(
    model: str,
    messages: List[Dict],
    api_key: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """流式调用 LLM 并逐 chunk 返回内容"""
    client = get_client(api_key)
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
    )
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


async def collect_completion(
    model: str,
    messages: List[Dict],
    api_key: Optional[str] = None,
) -> str:
    """非流式调用，收集完整响应"""
    result = []
    async for chunk in stream_completion(model, messages, api_key):
        result.append(chunk)
    return "".join(result)


# ==================== Step Functions ====================

async def step_1_basic_structure(
    paper_md: str, patent_sample: str, api_key: Optional[str] = None
) -> AsyncGenerator[str, None]:
    prompt = f"""我希望你完成以下任务：
1.详细阅读理解这篇文章
2.我会给你个发明专利说明书的范本，请你仔细阅读模仿他的语言风格、段落安排，为我撰写我们论文的发明专利名称（25个字以内）、说明书技术领域、背景技术、发明内容、有益效果部分、说明书附图说明（尽量是可以用框线图展示的流程）（不需要撰写具体实施例）。所有公式都要讲清楚里面包含的字母，不能有解释不清或者凭空出现的未知量。

请从"发明名称"开始输出，不要输出任何前言、分析或思考过程。

【论文内容】
{paper_md}

【范本】
{patent_sample}{OUTPUT_CONSTRAINT}"""
    messages = [{"role": "user", "content": prompt}]
    async for chunk in stream_completion(MODEL_GEMINI_PRO, messages, api_key):
        yield chunk


async def step_2_embodiments(
    doc_part_1: str, terms: str, sample: str, api_key: Optional[str] = None
) -> AsyncGenerator[str, None]:
    prompt = f"""请根据说明书范本和"说明书前半部分"帮我思考编写我们"说明书前半部分"专利详细的具体实施例。

请直接输出"具体实施方式"正文内容，不要输出任何前言、分析或思考过程。

【说明书前半部分】
{doc_part_1}

【术语表】
{terms}

【范本】
{sample}{OUTPUT_CONSTRAINT}"""
    messages = [{"role": "user", "content": prompt}]
    async for chunk in stream_completion(MODEL_GEMINI_PRO, messages, api_key):
        yield chunk


async def step_3_claims(
    spec_full: str, claims_sample: str, api_key: Optional[str] = None
) -> AsyncGenerator[str, None]:
    prompt = f"""请根据我给你的权利要求书范本帮我编写我们"说明书"专利的权利要求书。

请直接从"1."开始输出权利要求条目，不要输出任何前言、标题、分析或思考过程。

【说明书】
{spec_full}

【权利要求书范本】
{claims_sample}{OUTPUT_CONSTRAINT}"""
    messages = [{"role": "user", "content": prompt}]
    async for chunk in stream_completion(MODEL_GEMINI_PRO, messages, api_key):
        yield chunk


async def step_4_abstract(
    spec_full: str, abstract_sample: str, api_key: Optional[str] = None
) -> AsyncGenerator[str, None]:
    prompt = f"""请根据我给你的说明书摘要范本帮我编写我们"说明书"专利的说明书摘要。

请直接输出摘要正文（一段话，300字以内），不要输出任何前言、标题、分析或思考过程。

【说明书】
{spec_full}

【说明书摘要范本】
{abstract_sample}{OUTPUT_CONSTRAINT}"""
    messages = [{"role": "user", "content": prompt}]
    async for chunk in stream_completion(MODEL_GEMINI_PRO, messages, api_key):
        yield chunk


async def step_5_visual_prompts(
    spec_full: str, num_figures: int, api_key: Optional[str] = None
) -> AsyncGenerator[str, None]:
    prompt = f"""现在我需要你仔细阅读理解我的专利，并帮我生成绘制专利 {num_figures} 张附图的提示词，都需要中文图片，简洁高级的黑白流程图即可，4K 高清，16：9。帮我详细生成 {num_figures} 幅图的绘图提示词。

请直接输出每幅图的提示词，格式为"图1：xxx"，不要输出任何前言或分析。

【说明书】
{spec_full}{OUTPUT_CONSTRAINT}"""
    messages = [{"role": "user", "content": prompt}]
    async for chunk in stream_completion(MODEL_GPT, messages, api_key):
        yield chunk


def parse_figure_prompts(prompts_text: str) -> List[str]:
    """将附图提示词文本解析为单独的 prompt 列表"""
    # 按 "图N：" 或 "图N:" 分割
    pattern = r'图\s*\d+\s*[：:]'
    splits = re.split(pattern, prompts_text)
    # 第一段通常是空的或前言
    prompts = [s.strip() for s in splits if s.strip()]
    return prompts


async def step_6_generate_figure(
    prompt: str, figure_index: int, api_key: Optional[str] = None
) -> Optional[bytes]:
    """
    调用 gemini-3-pro-image-preview 生成单张附图。
    OpenRouter 返回的图片在 msg["images"] 字段中，格式为:
    [{"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}]
    """
    client = get_client(api_key)

    full_prompt = f"""请根据以下描述生成一张专利附图。
要求：黑白流程图风格，简洁高级，中文标注，4K高清，16:9比例。

图{figure_index + 1}的内容描述：
{prompt}"""

    try:
        response = await client.chat.completions.create(
            model=MODEL_IMAGE_GEN,
            messages=[{"role": "user", "content": full_prompt}],
            extra_body={
                "modalities": ["image", "text"],
            },
        )

        raw = response.model_dump()
        msg_data = raw.get("choices", [{}])[0].get("message", {})

        # 方式1: 从 images 字段提取（OpenRouter 主要格式）
        images = msg_data.get("images", [])
        if images:
            for img_item in images:
                if isinstance(img_item, dict):
                    url = img_item.get("image_url", {}).get("url", "")
                    if not url and isinstance(img_item.get("image_url"), str):
                        url = img_item["image_url"]
                    m = re.search(r'base64,([A-Za-z0-9+/=\s]+)', url, re.DOTALL)
                    if m:
                        raw_b64 = m.group(1).replace("\n", "").replace(" ", "").replace("\r", "")
                        return base64.b64decode(raw_b64)
                elif isinstance(img_item, str):
                    # 可能是纯 base64 或 data URI
                    m = re.search(r'base64,(.+)', img_item, re.DOTALL)
                    if m:
                        return base64.b64decode(m.group(1).strip())
                    if len(img_item) > 500:
                        try:
                            return base64.b64decode(img_item)
                        except Exception:
                            pass

        # 方式2: 从 content 提取（兼容其他模型）
        content = msg_data.get("content", "")
        if isinstance(content, str) and content:
            b64_match = re.search(
                r'data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=\s]+)',
                content, re.DOTALL
            )
            if b64_match:
                raw_b64 = b64_match.group(2).replace("\n", "").replace(" ", "")
                return base64.b64decode(raw_b64)

        # 方式3: content 为 list 形式
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    url = part.get("image_url", {}).get("url", "")
                    m = re.search(r'base64,(.+)', url, re.DOTALL)
                    if m:
                        return base64.b64decode(m.group(1).strip())

        print(f"[Image Gen] 图{figure_index + 1}: 未能提取图片数据")
        return None

    except Exception as e:
        print(f"[Image Gen] 图{figure_index + 1} 生成失败: {e}")
        return None


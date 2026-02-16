"""
LLM Engine - OpenRouter API 封装
支持运行时动态注入 API Key
"""
import os
from typing import AsyncGenerator, Dict, List, Optional
from openai import AsyncOpenAI

# Default config from env
DEFAULT_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
SITE_URL = os.getenv("SITE_URL", "http://localhost:3000")
SITE_NAME = os.getenv("SITE_NAME", "Auto-Patent Architect")

# Model IDs
MODEL_GEMINI_PRO = "google/gemini-2.5-pro-preview-06-05"
MODEL_GPT = "openai/gpt-4o"
MODEL_IMAGE_GEN = "google/gemini-2.0-flash-exp:free"

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
    messages: List[Dict[str, str]],
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
    messages: List[Dict[str, str]],
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
    prompt = f"""现在我需要你帮我生成绘制专利 {num_figures} 张附图的提示词，都需要中文图片，简洁高级的黑白流程图即可，4K 高清，16：9。帮我详细生成 {num_figures} 幅图的绘图提示词。

请直接输出每幅图的提示词，格式为"图1：xxx"，不要输出任何前言或分析。

【说明书】
{spec_full}{OUTPUT_CONSTRAINT}"""
    messages = [{"role": "user", "content": prompt}]
    async for chunk in stream_completion(MODEL_GPT, messages, api_key):
        yield chunk

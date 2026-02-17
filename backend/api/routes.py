"""
Auto-Patent Architect - API Routes
完整的专利生成管道、SSE 流式端点、文件下载
"""
import asyncio
import json
import os
import shutil
import uuid
import traceback
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, Response
from pydantic import BaseModel

from services.pdf_parser import parse_pdf
from services.llm_engine import (
    step_1_basic_structure,
    step_2_embodiments,
    step_3_claims,
    step_4_abstract,
    step_5_visual_prompts,
    step_6_generate_figure,
    parse_figure_prompts,
    collect_completion,
    MODEL_GEMINI_PRO,
)
from services.doc_generator import generator

router = APIRouter()

# ==================== In-Memory State ====================
# task_id -> { status, step, step_label, content, error, files, api_key, ... }
tasks: dict = {}


# ==================== Models ====================
class ConfigPayload(BaseModel):
    api_key: str


# ==================== Endpoints ====================

@router.post("/config")
async def set_config(payload: ConfigPayload):
    """前端传入 OpenRouter API Key（仅存内存，不持久化）"""
    global _current_api_key
    _current_api_key = payload.api_key
    return {"message": "API Key 已配置"}

_current_api_key: str = ""


@router.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    spec_sample: Optional[UploadFile] = File(None),
    claims_sample: Optional[UploadFile] = File(None),
    abstract_sample: Optional[UploadFile] = File(None),
):
    """
    上传论文 PDF 和可选范本文件，启动后台专利生成管道
    """
    task_id = str(uuid.uuid4())
    task_dir = os.path.join("output", task_id)
    os.makedirs(task_dir, exist_ok=True)

    # Save uploaded PDF
    pdf_path = os.path.join("temp", f"{task_id}.pdf")
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Save sample files if provided
    samples = {}
    for name, upload in [
        ("spec_sample", spec_sample),
        ("claims_sample", claims_sample),
        ("abstract_sample", abstract_sample),
    ]:
        if upload:
            ext = os.path.splitext(upload.filename or ".txt")[1]
            sample_path = os.path.join("samples", f"{task_id}_{name}{ext}")
            content = await upload.read()
            with open(sample_path, "wb") as f:
                f.write(content)
            samples[name] = sample_path

    # Initialize task state
    tasks[task_id] = {
        "status": "queued",
        "step": "0",
        "step_label": "排队中",
        "content": "",
        "error": "",
        "pdf_path": pdf_path,
        "task_dir": task_dir,
        "samples": samples,
        "api_key": _current_api_key,
        "files": {},
        "figures": [],       # 附图路径列表
        "stream_chunks": [],  # SSE chunks buffer
    }

    background_tasks.add_task(process_patent_pipeline, task_id)
    return {"task_id": task_id}


@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """获取任务状态"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    t = tasks[task_id]
    return {
        "task_id": task_id,
        "status": t["status"],
        "step": t["step"],
        "step_label": t["step_label"],
        "error": t["error"],
        "files": t["files"],
        "figures": len(t.get("figures", [])),
    }


@router.get("/stream/{task_id}")
async def stream_output(task_id: str):
    """SSE 流式端点 - 实时推送内容生成进度"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def event_generator():
        last_index = 0
        heartbeat_interval = 10
        last_heartbeat = asyncio.get_event_loop().time()

        while True:
            t = tasks.get(task_id)
            if not t:
                break

            # Send new chunks
            chunks = t["stream_chunks"]
            if last_index < len(chunks):
                for i in range(last_index, len(chunks)):
                    data = json.dumps(chunks[i], ensure_ascii=False)
                    yield f"data: {data}\n\n"
                last_index = len(chunks)
                last_heartbeat = asyncio.get_event_loop().time()

            # Check if done
            if t["status"] in ("completed", "failed"):
                final = {
                    "type": "done",
                    "status": t["status"],
                    "files": t["files"],
                    "figures": len(t.get("figures", [])),
                    "error": t["error"],
                }
                yield f"data: {json.dumps(final, ensure_ascii=False)}\n\n"
                break

            # 心跳保活
            now = asyncio.get_event_loop().time()
            if now - last_heartbeat >= heartbeat_interval:
                yield ": heartbeat\n\n"
                last_heartbeat = now

            await asyncio.sleep(0.3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/download/{task_id}/{doc_type}")
async def download_doc(task_id: str, doc_type: str):
    """下载生成的文档"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    t = tasks[task_id]
    file_path = t["files"].get(doc_type)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"文件 {doc_type} 尚未生成")

    filename_map = {
        "specification": "说明书.docx",
        "claims": "权利要求书.docx",
        "abstract": "说明书摘要.docx",
    }
    return FileResponse(
        path=file_path,
        filename=filename_map.get(doc_type, f"{doc_type}.docx"),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.get("/image/{task_id}/{index}")
async def get_figure_image(task_id: str, index: int):
    """获取生成的附图"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    figures = tasks[task_id].get("figures", [])
    if index < 0 or index >= len(figures):
        raise HTTPException(status_code=404, detail=f"附图 {index} 不存在")

    fig_path = figures[index]
    if not os.path.exists(fig_path):
        raise HTTPException(status_code=404, detail="附图文件不存在")

    return FileResponse(
        path=fig_path,
        media_type="image/png",
        filename=f"图{index + 1}.png",
    )


# ==================== Pipeline ====================

def _push_chunk(task_id: str, chunk_type: str, **kwargs):
    """向 SSE 缓冲区推送一条消息"""
    if task_id in tasks:
        msg = {"type": chunk_type, **kwargs}
        tasks[task_id]["stream_chunks"].append(msg)


def _push_log(task_id: str, message: str):
    """推送日志消息到 SSE"""
    _push_chunk(task_id, "log", message=message)


def _update_step(task_id: str, step: str, label: str):
    """更新任务步骤"""
    if task_id in tasks:
        tasks[task_id]["step"] = step
        tasks[task_id]["step_label"] = label
        _push_chunk(task_id, "step", step=step, label=label)
        _push_log(task_id, f">>> 进入步骤 {step}: {label}")


async def _collect_stream(task_id: str, gen, step_id: str):
    """从异步生成器收集内容，同时推送 SSE"""
    full_text = []
    async for chunk in gen:
        full_text.append(chunk)
        _push_chunk(task_id, "content", step=step_id, text=chunk)
    return "".join(full_text)


async def process_patent_pipeline(task_id: str):
    """完整的专利生成管道"""
    t = tasks[task_id]
    api_key = t["api_key"]
    task_dir = t["task_dir"]
    samples = t["samples"]

    try:
        t["status"] = "processing"
        _push_log(task_id, "管道启动")

        # ===== Step 0: PDF 解析 =====
        _update_step(task_id, "0", "PDF 预处理")
        _push_log(task_id, f"开始解析 PDF: {t['pdf_path']}")
        pdf_text = await parse_pdf(t["pdf_path"])
        _push_chunk(task_id, "content", step="0", text=f"PDF 解析完成，共 {len(pdf_text)} 字符\n")
        _push_log(task_id, f"PDF 解析完成，提取 {len(pdf_text)} 字符")

        # 读取范本（如有）
        def _read_sample(path: str) -> str:
            """读取范本文件，支持 .docx 和纯文本"""
            if path.endswith((".docx", ".doc")):
                from docx import Document as DocxDocument
                doc = DocxDocument(path)
                return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            else:
                for enc in ["utf-8", "gbk", "gb2312", "latin-1"]:
                    try:
                        with open(path, "r", encoding=enc) as f:
                            return f.read()
                    except (UnicodeDecodeError, LookupError):
                        continue
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()

        spec_sample_text = ""
        claims_sample_text = ""
        abstract_sample_text = ""

        if "spec_sample" in samples:
            spec_sample_text = _read_sample(samples["spec_sample"])
            _push_log(task_id, f"已读取说明书范本: {len(spec_sample_text)} 字符")
        if "claims_sample" in samples:
            claims_sample_text = _read_sample(samples["claims_sample"])
            _push_log(task_id, f"已读取权利要求书范本: {len(claims_sample_text)} 字符")
        if "abstract_sample" in samples:
            abstract_sample_text = _read_sample(samples["abstract_sample"])
            _push_log(task_id, f"已读取说明书摘要范本: {len(abstract_sample_text)} 字符")

        if not spec_sample_text:
            spec_sample_text = "（无范本提供，请按照标准专利说明书格式撰写）"
        if not claims_sample_text:
            claims_sample_text = "（无范本提供，请按照标准权利要求书格式撰写）"
        if not abstract_sample_text:
            abstract_sample_text = "（无范本提供，请按照标准说明书摘要格式撰写）"

        # ===== Step 1: 基础构建 =====
        _update_step(task_id, "1", "基础构建与术语锁定")
        _push_log(task_id, f"调用模型: google/gemini-3-pro-preview")
        doc_part_1 = await _collect_stream(
            task_id,
            step_1_basic_structure(pdf_text, spec_sample_text, api_key),
            "1",
        )
        _push_log(task_id, f"Step 1 完成，生成 {len(doc_part_1)} 字符")

        terms = doc_part_1[:500]

        # ===== Step 2: 具体实施例 =====
        _update_step(task_id, "2", "实施例深度撰写")
        _push_log(task_id, f"调用模型: google/gemini-3-pro-preview")
        doc_part_2 = await _collect_stream(
            task_id,
            step_2_embodiments(doc_part_1, terms, spec_sample_text, api_key),
            "2",
        )
        _push_log(task_id, f"Step 2 完成，生成 {len(doc_part_2)} 字符")

        full_spec = doc_part_1 + "\n\n具体实施方式\n\n" + doc_part_2

        # 生成说明书 .docx
        spec_title = full_spec.split("\n")[0][:25] if full_spec else "发明专利说明书"
        spec_path = os.path.join(task_dir, "说明书.docx")
        generator.generate_specification(spec_title, full_spec, spec_path)
        t["files"]["specification"] = spec_path
        _push_chunk(task_id, "file_ready", doc_type="specification")
        _push_log(task_id, f"说明书已保存: {spec_path}")

        # ===== Step 3: 权利要求书 =====
        _update_step(task_id, "3", "权利要求书生成")
        _push_log(task_id, f"调用模型: google/gemini-3-pro-preview")
        claims_text = await _collect_stream(
            task_id,
            step_3_claims(full_spec, claims_sample_text, api_key),
            "3",
        )
        _push_log(task_id, f"Step 3 完成，生成 {len(claims_text)} 字符")

        claims_path = os.path.join(task_dir, "权利要求书.docx")
        generator.generate_claims(claims_text, claims_path)
        t["files"]["claims"] = claims_path
        _push_chunk(task_id, "file_ready", doc_type="claims")
        _push_log(task_id, f"权利要求书已保存: {claims_path}")

        # ===== Step 4: 说明书摘要 =====
        _update_step(task_id, "4", "说明书摘要生成")
        _push_log(task_id, f"调用模型: google/gemini-3-pro-preview")
        abstract_text = await _collect_stream(
            task_id,
            step_4_abstract(full_spec, abstract_sample_text, api_key),
            "4",
        )
        _push_log(task_id, f"Step 4 完成，生成 {len(abstract_text)} 字符")

        abstract_path = os.path.join(task_dir, "说明书摘要.docx")
        generator.generate_abstract(abstract_text, abstract_path)
        t["files"]["abstract"] = abstract_path
        _push_chunk(task_id, "file_ready", doc_type="abstract")
        _push_log(task_id, f"说明书摘要已保存: {abstract_path}")

        # ===== Step 5: 附图提示词 =====
        _update_step(task_id, "5", "附图提示词生成")
        _push_log(task_id, f"调用模型: openai/gpt-5.2")
        visual_prompts = await _collect_stream(
            task_id,
            step_5_visual_prompts(full_spec, 5, api_key),
            "5",
        )
        _push_log(task_id, f"Step 5 完成，生成 {len(visual_prompts)} 字符")

        # Save prompts as text file
        prompts_path = os.path.join(task_dir, "附图提示词.txt")
        with open(prompts_path, "w", encoding="utf-8") as f:
            f.write(visual_prompts)
        t["files"]["visual_prompts"] = prompts_path

        # ===== Step 6: 附图生成 =====
        _update_step(task_id, "6", "附图生成")
        _push_log(task_id, f"调用模型: google/gemini-3-pro-image-preview")

        figure_prompts = parse_figure_prompts(visual_prompts)
        _push_log(task_id, f"解析出 {len(figure_prompts)} 张附图提示词")

        for i, fig_prompt in enumerate(figure_prompts):
            _push_log(task_id, f"正在生成图 {i + 1}/{len(figure_prompts)}...")
            _push_chunk(task_id, "content", step="6",
                        text=f"\n正在生成 图{i + 1}/{len(figure_prompts)}...\n")

            img_data = await step_6_generate_figure(fig_prompt, i, api_key)

            if img_data:
                fig_path = os.path.join(task_dir, f"图{i + 1}.png")
                with open(fig_path, "wb") as f:
                    f.write(img_data)
                t["figures"].append(fig_path)
                _push_chunk(task_id, "figure_ready", index=i, total=len(figure_prompts))
                _push_log(task_id, f"图 {i + 1} 生成成功，保存至 {fig_path}")
            else:
                _push_log(task_id, f"图 {i + 1} 生成失败，跳过")
                _push_chunk(task_id, "content", step="6",
                            text=f"  ⚠ 图{i + 1} 生成失败\n")

        _push_log(task_id, f"附图生成完毕，共 {len(t['figures'])} 张")

        # ===== Done =====
        t["status"] = "completed"
        t["step_label"] = "全部完成"
        _push_log(task_id, "管道执行完毕")

    except Exception as e:
        t["status"] = "failed"
        t["error"] = str(e)
        _push_chunk(task_id, "error", message=str(e))
        _push_log(task_id, f"管道异常: {str(e)}")
        traceback.print_exc()

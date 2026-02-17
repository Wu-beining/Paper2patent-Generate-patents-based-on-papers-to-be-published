"""测试 images 字段格式"""
import asyncio
import os
import json

api_key = os.environ.get("OPENROUTER_API_KEY", "")
if not api_key:
    print("请先设置 OPENROUTER_API_KEY 环境变量")
    exit(1)
os.environ["OPENROUTER_API_KEY"] = api_key

from services.llm_engine import get_client, MODEL_IMAGE_GEN

async def test():
    client = get_client()
    try:
        response = await client.chat.completions.create(
            model=MODEL_IMAGE_GEN,
            messages=[{"role": "user", "content": "Draw a simple flowchart: Input -> Process -> Output. Black and white."}],
            extra_body={"modalities": ["image", "text"]},
        )
        raw = response.model_dump()
        msg = raw["choices"][0]["message"]
        images = msg.get("images", [])
        print(f"images count: {len(images)}")
        
        if images:
            for i, img in enumerate(images):
                if isinstance(img, str):
                    print(f"  img[{i}] type=str, len={len(img)}, prefix: {img[:80]}")
                elif isinstance(img, dict):
                    print(f"  img[{i}] type=dict, keys={list(img.keys())}")
                    for k, v in img.items():
                        if isinstance(v, str) and len(v) > 100:
                            print(f"    {k}: len={len(v)}, prefix={v[:80]}")
                        else:
                            print(f"    {k}: {str(v)[:100]}")
                else:
                    print(f"  img[{i}] type={type(img).__name__}")
        
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

asyncio.run(test())

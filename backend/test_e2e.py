"""端到端测试脚本 - 自动配置 API Key、上传文件并监控输出"""
import requests
import json
import time
import sys
import os

API_BASE = "http://localhost:8000/api"
API_KEY = os.environ.get("OPENROUTER_API_KEY", "YOUR_API_KEY_HERE")

# Step 1: 配置 API Key
print("[1/3] 配置 API Key...")
r = requests.post(f"{API_BASE}/config", json={"api_key": API_KEY})
print(f"  响应: {r.status_code} {r.json()}")

# Step 2: 上传文件
print("[2/3] 上传 PDF 和范本文件...")
files = {
    "file": ("paper.pdf", open(r"d:\desktop\AutoPatent\Note2Narr__APIN_.pdf", "rb"), "application/pdf"),
    "spec_sample": ("说明书范本.docx", open(r"d:\desktop\AutoPatent\说明书范本.docx", "rb"), "application/octet-stream"),
    "claims_sample": ("权利要求书范本.docx", open(r"d:\desktop\AutoPatent\权利要求书范本.docx", "rb"), "application/octet-stream"),
    "abstract_sample": ("说明书摘要范本.docx", open(r"d:\desktop\AutoPatent\说明书摘要范本.docx", "rb"), "application/octet-stream"),
}
r = requests.post(f"{API_BASE}/upload", files=files)
data = r.json()
task_id = data["task_id"]
print(f"  任务 ID: {task_id}")

# Step 3: 监控 SSE 流
print("[3/3] 监控 SSE 流式输出...")
print("=" * 60)

try:
    response = requests.get(f"{API_BASE}/stream/{task_id}", stream=True, timeout=1200)
    for line in response.iter_lines(decode_unicode=True):
        if line and line.startswith("data: "):
            raw = line[6:]
            try:
                msg = json.loads(raw)
                if msg["type"] == "step":
                    print(f"\n\n{'='*60}")
                    print(f">>> 进入步骤 {msg['step']}: {msg['label']}")
                    print(f"{'='*60}")
                elif msg["type"] == "content":
                    sys.stdout.write(msg["text"])
                    sys.stdout.flush()
                elif msg["type"] == "file_ready":
                    print(f"\n  [✅ 文件就绪: {msg['doc_type']}]")
                elif msg["type"] == "error":
                    print(f"\n  [❌ 错误: {msg['message']}]")
                elif msg["type"] == "done":
                    print(f"\n\n{'='*60}")
                    print(f">>> 完成! 状态: {msg['status']}")
                    if msg.get("files"):
                        print(f"  生成文件: {list(msg['files'].keys())}")
                    if msg.get("error"):
                        print(f"  错误: {msg['error']}")
                    break
            except json.JSONDecodeError:
                pass
except KeyboardInterrupt:
    print("\n用户中断")
except Exception as e:
    print(f"\n连接错误: {e}")

print("\n测试完毕!")

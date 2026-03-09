from __future__ import annotations

import uuid
from io import BytesIO

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

from app.config import settings
from app.schemas import OptimizeResponse
from app.services.docx_exporter import markdown_to_docx
from app.services.job_fetcher import JobFetcher
from app.services.job_ocr_fetcher import JobOCRFetcher
from app.services.optimizer import ResumeOptimizer
from app.services.resume_parser import ResumeParser

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_result_cache: dict[str, str] = {}


@app.get("/", response_class=HTMLResponse)
async def playground() -> HTMLResponse:
    html = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>JD Master 体验页</title>
  <style>
    body { font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; max-width: 900px; margin: 24px auto; padding: 0 12px; background: #f5f7fb; }
    .card { background: white; border-radius: 12px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,.08); margin-bottom: 14px; }
    .label { margin-top: 10px; font-weight: 600; display: block; }
    input[type='url'], input[type='file'], button, textarea { width: 100%; box-sizing: border-box; margin-top: 6px; padding: 10px; border-radius: 8px; border: 1px solid #d7dbe8; }
    button { background: #2563eb; color: #fff; border: none; cursor: pointer; }
    button:disabled { opacity: .6; cursor: not-allowed; }
    textarea { min-height: 300px; font-family: ui-monospace,SFMono-Regular,Menlo,monospace; }
    .row { display: flex; gap: 12px; }
    .row > * { flex: 1; }
    .msg { color: #dc2626; }
  </style>
</head>
<body>
  <h1>JD Master 智能简历定向优化（后端直连体验）</h1>
  <div class="card">
    <label class="label">上传简历（docx/pdf）</label>
    <input id="resume" type="file" accept=".docx,.pdf" />

    <label class="label">岗位链接（Boss直聘）</label>
    <input id="jobUrl" type="url" placeholder="https://www.zhipin.com/job_detail/..." />

    <label class="label">AI 模式</label>
    <select id="aiProvider" style="width:100%;padding:10px;border-radius:8px;border:1px solid #d7dbe8;">
      <option value="mock">mock（不需要 API Key）</option>
      <option value="doubao">doubao（需要 API Key）</option>
    </select>

    <label class="label">AI API Key（可选，当前请求生效，不存储）</label>
    <input id="aiApiKey" type="password" placeholder="输入豆包 API Key" />

    <label class="label">AI 模型（可选）</label>
    <input id="aiModel" type="text" placeholder="doubao-seed-1-6-250615" />

    <div class="row" style="margin-top:10px;">
      <button id="optimizeBtn">开始优化</button>
      <button id="downloadBtn" disabled>下载 DOCX</button>
    </div>
    <p id="msg" class="msg"></p>
  </div>

  <div class="card">
    <h3>结果预览</h3>
    <textarea id="result" placeholder="点击开始优化后将在这里展示结果"></textarea>
  </div>

<script>
  const optimizeBtn = document.getElementById('optimizeBtn');
  const downloadBtn = document.getElementById('downloadBtn');
  const msg = document.getElementById('msg');
  const result = document.getElementById('result');

  optimizeBtn.onclick = async () => {
    msg.textContent = '';
    const file = document.getElementById('resume').files[0];
    const jobUrl = document.getElementById('jobUrl').value.trim();
    if (!file || !jobUrl) {
      msg.textContent = '请先上传简历并填写岗位链接';
      return;
    }

    const form = new FormData();
    form.append('resume', file);
    form.append('job_url', jobUrl);
    form.append('ai_provider', document.getElementById('aiProvider').value);
    form.append('ai_api_key', document.getElementById('aiApiKey').value);
    form.append('ai_model', document.getElementById('aiModel').value);

    optimizeBtn.disabled = true;
    optimizeBtn.textContent = '处理中...';

    try {
      const resp = await fetch('/api/optimize', { method: 'POST', body: form });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || '优化失败');
      result.value = data.optimized_resume_markdown || '';
      downloadBtn.disabled = !result.value;
    } catch (e) {
      msg.textContent = e.message || '优化失败';
    } finally {
      optimizeBtn.disabled = false;
      optimizeBtn.textContent = '开始优化';
    }
  }

  downloadBtn.onclick = async () => {
    if (!result.value.trim()) return;
    const form = new FormData();
    form.append('content', result.value);
    const resp = await fetch('/api/export', { method: 'POST', body: form });
    if (!resp.ok) {
      msg.textContent = '导出失败';
      return;
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'optimized_resume.docx';
    a.click();
    URL.revokeObjectURL(url);
  }
</script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/optimize", response_model=OptimizeResponse)
async def optimize_resume(
    resume: UploadFile = File(...),
    job_url: str = Form(...),
    ai_provider: str | None = Form(default=None),
    ai_api_key: str | None = Form(default=None),
    ai_model: str | None = Form(default=None),
) -> OptimizeResponse:
    suffix = resume.filename.lower().split(".")[-1] if resume.filename else ""
    if suffix not in {"docx", "pdf"}:
        raise HTTPException(status_code=400, detail="仅支持 docx / pdf 文件")

    file_bytes = await resume.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大，请控制在10MB以内")

    try:
        parsed_resume = ResumeParser.parse(resume.filename or "resume.docx", file_bytes)
        if settings.jd_fetch_mode == "ocr_browser":
            try:
                job_info = await JobOCRFetcher.fetch(job_url)
            except Exception:
                job_info = await JobFetcher.fetch(job_url)
        else:
            job_info = await JobFetcher.fetch(job_url)
        optimized_resume_markdown = await ResumeOptimizer.optimize(
            parsed_resume,
            job_info,
            ai_provider=ai_provider,
            ai_api_key=ai_api_key,
            ai_model=ai_model,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"处理失败: {exc}") from exc

    cache_key = str(uuid.uuid4())
    _result_cache[cache_key] = optimized_resume_markdown

    return OptimizeResponse(
        optimized_resume_markdown=f"<!--cache:{cache_key}-->\n" + optimized_resume_markdown,
        parsed_resume=parsed_resume,
        job_info=job_info,
    )


@app.post("/api/export")
async def export_docx(content: str = Form(...)) -> StreamingResponse:
    cleaned = content
    if content.startswith("<!--cache:"):
        marker = content.split("-->", 1)[0]
        key = marker.replace("<!--cache:", "")
        cleaned = _result_cache.get(key, content.split("-->", 1)[-1].strip())

    docx_bytes = markdown_to_docx(cleaned)
    filename = "optimized_resume.docx"
    return StreamingResponse(
        BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

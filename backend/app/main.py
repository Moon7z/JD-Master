from __future__ import annotations

import uuid
from io import BytesIO

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import settings
from app.schemas import OptimizeResponse
from app.services.docx_exporter import markdown_to_docx
from app.services.job_fetcher import JobFetcher
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/optimize", response_model=OptimizeResponse)
async def optimize_resume(
    resume: UploadFile = File(...),
    job_url: str = Form(...),
) -> OptimizeResponse:
    suffix = resume.filename.lower().split(".")[-1] if resume.filename else ""
    if suffix not in {"docx", "pdf"}:
        raise HTTPException(status_code=400, detail="仅支持 docx / pdf 文件")

    file_bytes = await resume.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大，请控制在10MB以内")

    try:
        parsed_resume = ResumeParser.parse(resume.filename or "resume.docx", file_bytes)
        job_info = await JobFetcher.fetch(job_url)
        optimized_resume_markdown = await ResumeOptimizer.optimize(parsed_resume, job_info)
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

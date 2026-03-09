from __future__ import annotations

import json

import httpx

from app.config import settings
from app.schemas import JobInfo, ParsedResume


class ResumeOptimizer:
    @staticmethod
    async def optimize(
        parsed_resume: ParsedResume,
        job_info: JobInfo,
        ai_provider: str | None = None,
        ai_api_key: str | None = None,
        ai_model: str | None = None,
    ) -> str:
        provider = (ai_provider or settings.ai_provider or "mock").lower().strip()
        api_key = (ai_api_key or settings.doubao_api_key or "").strip()
        model = (ai_model or settings.doubao_model).strip()

        if provider == "doubao" and api_key:
            return await ResumeOptimizer._optimize_with_doubao(parsed_resume, job_info, api_key=api_key, model=model)
        return ResumeOptimizer._mock_optimize(parsed_resume, job_info)

    @staticmethod
    def _build_prompt(parsed_resume: ParsedResume, job_info: JobInfo) -> str:
        return (
            "你是资深HR与职业咨询顾问，请基于以下信息重写简历。"
            "要求：真实、突出匹配度、包含岗位关键词、结构清晰、中文输出。\n\n"
            f"岗位信息:\n{job_info.model_dump_json(indent=2, ensure_ascii=False)}\n\n"
            f"原始简历:\n{parsed_resume.model_dump_json(indent=2, ensure_ascii=False)}\n"
        )

    @staticmethod
    async def _optimize_with_doubao(parsed_resume: ParsedResume, job_info: JobInfo, api_key: str, model: str) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是一位专业中文简历优化助手"},
                {"role": "user", "content": ResumeOptimizer._build_prompt(parsed_resume, job_info)},
            ],
            "temperature": 0.3,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.post(
                f"{settings.doubao_base_url}/chat/completions", headers=headers, content=json.dumps(payload)
            )
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def _mock_optimize(parsed_resume: ParsedResume, job_info: JobInfo) -> str:
        highlights = parsed_resume.work_experience[:3] or ["请补充可量化项目成果"]
        skills = parsed_resume.skills[:8]
        req_keywords = "、".join(job_info.requirements[:6]) if job_info.requirements else "岗位关键词待补充"
        return f"""# 定向优化简历（{job_info.title}）

## 个人优势摘要
- 具备与 **{job_info.title}** 相关的核心经验，能够快速对齐业务目标。
- 有结构化问题拆解与跨团队协作能力，能够在高节奏环境持续交付。
- 针对岗位需求重点覆盖：{req_keywords}。

## 重点经历（按匹配度排序）
""" + "\n".join([f"- {item}" for item in highlights]) + f"""

## 技能矩阵
- 核心技能：{"、".join(skills) if skills else "Python、数据分析、沟通协作"}
- 通用能力：需求分析、项目推进、结果复盘

## 教育背景
""" + "\n".join([f"- {edu}" for edu in parsed_resume.education[:3]]) + """

## 求职意向
- 目标岗位：{job_info.title}
- 期望城市：{job_info.location or '可协商'}
"""

from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.schemas import JobInfo


class JobFetcher:
    @staticmethod
    async def fetch(url: str) -> JobInfo:
        headers = {"User-Agent": settings.user_agent}
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()

        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        title = (
            soup.select_one("h1")
            or soup.select_one(".job-name")
            or soup.select_one("title")
        )
        title_text = title.get_text(strip=True) if title else "未知职位"

        company = soup.select_one(".company-name")
        salary = soup.select_one(".salary")
        location = soup.select_one(".job-area")

        text_block = soup.get_text("\n", strip=True)
        responsibilities = JobFetcher._extract_bullets(text_block, ["岗位职责", "职位描述", "你将负责"])
        requirements = JobFetcher._extract_bullets(text_block, ["任职要求", "职位要求", "我们希望你"])

        return JobInfo(
            source_url=url,
            title=title_text,
            company=company.get_text(strip=True) if company else None,
            salary=salary.get_text(strip=True) if salary else None,
            location=location.get_text(strip=True) if location else None,
            responsibilities=responsibilities,
            requirements=requirements,
            original_text=text_block,
        )

    @staticmethod
    def _extract_bullets(text: str, markers: list[str]) -> list[str]:
        for marker in markers:
            pattern = rf"{re.escape(marker)}[：:]?\s*(.+?)(?:\n\n|任职要求|职位要求|$)"
            match = re.search(pattern, text, flags=re.S)
            if not match:
                continue
            block = match.group(1)
            lines = [re.sub(r"^[\d\-•.\s]+", "", ln).strip() for ln in block.split("\n")]
            return [ln for ln in lines if len(ln) > 2][:8]
        return []

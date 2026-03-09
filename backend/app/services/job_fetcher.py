from __future__ import annotations

import json
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.schemas import JobInfo


PLACEHOLDER_VALUES = {
    "职位名称",
    "公司名称",
    "薪资范围",
    "工作地点",
    "职位描述",
    "岗位描述",
    "暂无",
    "无",
    "",
}


class JobFetcher:
    @staticmethod
    async def fetch(url: str) -> JobInfo:
        headers = {"User-Agent": settings.user_agent}
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, headers=headers) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

        return JobFetcher.parse_html(url, response.text)

    @staticmethod
    def parse_html(url: str, html: str) -> JobInfo:
        soup = BeautifulSoup(html, "html.parser")

        title_text = JobFetcher._clean(JobFetcher._pick_first_text(soup, ["h1", ".job-name", "meta[property='og:title']"]))
        company = JobFetcher._clean(JobFetcher._pick_first_text(soup, [".company-name", ".company-info .name", "meta[name='company']"]))
        salary = JobFetcher._clean(JobFetcher._pick_first_text(soup, [".salary", ".job-salary"]))
        location = JobFetcher._clean(JobFetcher._pick_first_text(soup, [".job-area", ".city"]))

        if not title_text or title_text in PLACEHOLDER_VALUES:
            title_text = JobFetcher._extract_title_from_title_tag(soup.title.string if soup.title else "")

        if not company or company in PLACEHOLDER_VALUES:
            company = JobFetcher._extract_company_from_title(soup.title.string if soup.title else "")

        jsonld = JobFetcher._extract_json_ld(soup)
        title_text = title_text or jsonld.get("title")
        company = company or jsonld.get("company")
        salary = salary or jsonld.get("salary")
        location = location or jsonld.get("location")

        text_block = soup.get_text("\n", strip=True)
        responsibilities = JobFetcher._extract_bullets(text_block, ["岗位职责", "职位描述", "工作内容", "你将负责"])
        requirements = JobFetcher._extract_bullets(text_block, ["任职要求", "职位要求", "岗位要求", "我们希望你"])

        if not responsibilities:
            responsibilities = JobFetcher._fallback_sentences(text_block)

        if not title_text:
            title_text = f"待解析职位（{urlparse(url).netloc}）"

        return JobInfo(
            source_url=url,
            title=title_text,
            company=company,
            salary=salary,
            location=location,
            responsibilities=responsibilities,
            requirements=requirements,
            original_text=text_block,
        )

    @staticmethod
    def parse_text(url: str, text: str, page_title: str | None = None) -> JobInfo:
        clean_text = text or ""
        title_text = JobFetcher._extract_title_from_title_tag(page_title or "") or f"待解析职位（{urlparse(url).netloc}）"
        company = JobFetcher._extract_company_from_title(page_title or "")
        salary = JobFetcher._extract_salary(clean_text)
        location = JobFetcher._extract_location(clean_text)
        responsibilities = JobFetcher._extract_bullets(clean_text, ["岗位职责", "职位描述", "工作内容", "你将负责"])
        requirements = JobFetcher._extract_bullets(clean_text, ["任职要求", "职位要求", "岗位要求", "我们希望你"])

        if not responsibilities:
            responsibilities = JobFetcher._fallback_sentences(clean_text)

        return JobInfo(
            source_url=url,
            title=title_text,
            company=company,
            salary=salary,
            location=location,
            responsibilities=responsibilities,
            requirements=requirements,
            original_text=clean_text,
        )

    @staticmethod
    def _extract_salary(text: str) -> str | None:
        match = re.search(r"(\d{1,2}\s*[-~]\s*\d{1,2}\s*[kK万Ww])", text)
        return match.group(1).replace(" ", "") if match else None

    @staticmethod
    def _extract_location(text: str) -> str | None:
        match = re.search(r"工作地点[：:]?\s*([^\n]{2,20})", text)
        if not match:
            return None
        return JobFetcher._clean(match.group(1))

    @staticmethod
    def _pick_first_text(soup: BeautifulSoup, selectors: list[str]) -> str | None:
        for selector in selectors:
            node = soup.select_one(selector)
            if not node:
                continue
            if node.name == "meta":
                text = node.get("content", "").strip()
            else:
                text = node.get_text(strip=True)
            if text:
                return text
        return None

    @staticmethod
    def _extract_json_ld(soup: BeautifulSoup) -> dict[str, str | None]:
        result = {"title": None, "company": None, "salary": None, "location": None}
        for script in soup.select("script[type='application/ld+json']"):
            raw = script.string or script.get_text(strip=True)
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            objects = data if isinstance(data, list) else [data]
            for obj in objects:
                if not isinstance(obj, dict):
                    continue
                result["title"] = result["title"] or obj.get("title")
                result["salary"] = result["salary"] or obj.get("baseSalary")
                hiring_org = obj.get("hiringOrganization")
                if isinstance(hiring_org, dict):
                    result["company"] = result["company"] or hiring_org.get("name")
                job_location = obj.get("jobLocation")
                if isinstance(job_location, dict):
                    address = job_location.get("address")
                    if isinstance(address, dict):
                        loc = " ".join(
                            str(x)
                            for x in [
                                address.get("addressRegion"),
                                address.get("addressLocality"),
                                address.get("streetAddress"),
                            ]
                            if x
                        ).strip()
                        result["location"] = result["location"] or loc
        return {k: JobFetcher._clean(v) for k, v in result.items()}

    @staticmethod
    def _extract_title_from_title_tag(title_tag: str) -> str | None:
        if not title_tag:
            return None
        title_tag = title_tag.strip()
        for sep in ["_", "-", "|", "招聘"]:
            if sep in title_tag:
                candidate = title_tag.split(sep)[0].strip()
                cleaned = JobFetcher._clean(candidate)
                if cleaned and cleaned not in PLACEHOLDER_VALUES:
                    return cleaned
        cleaned = JobFetcher._clean(title_tag)
        return cleaned if cleaned not in PLACEHOLDER_VALUES else None

    @staticmethod
    def _extract_company_from_title(title_tag: str) -> str | None:
        if not title_tag:
            return None
        parts = [p.strip() for p in re.split(r"[-_|]", title_tag) if p.strip()]
        if len(parts) >= 2:
            cand = JobFetcher._clean(parts[1])
            if cand and cand not in PLACEHOLDER_VALUES:
                return cand
        return None

    @staticmethod
    def _extract_bullets(text: str, markers: list[str]) -> list[str]:
        for marker in markers:
            pattern = rf"{re.escape(marker)}[：:]?\s*(.+?)(?:\n\n|任职要求|职位要求|岗位要求|$)"
            match = re.search(pattern, text, flags=re.S)
            if not match:
                continue
            block = match.group(1)
            lines = [re.sub(r"^[\d\-•.\s]+", "", ln).strip() for ln in block.split("\n")]
            cleaned = [JobFetcher._clean(ln) for ln in lines]
            return [ln for ln in cleaned if ln and len(ln) > 2 and ln not in PLACEHOLDER_VALUES][:8]
        return []

    @staticmethod
    def _fallback_sentences(text: str) -> list[str]:
        lines = [JobFetcher._clean(ln) for ln in text.split("\n")]
        candidates = [ln for ln in lines if ln and len(ln) > 8 and ln not in PLACEHOLDER_VALUES]
        return candidates[:6]

    @staticmethod
    def _clean(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = re.sub(r"\s+", " ", str(value)).strip()
        return cleaned or None

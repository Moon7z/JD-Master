from __future__ import annotations

import io
import re
from typing import Iterable

import pdfplumber
from docx import Document

from app.schemas import ParsedResume


SECTION_HINTS = {
    "work_experience": ["工作经历", "工作经验", "experience", "employment"],
    "education": ["教育", "学历", "education"],
    "skills": ["技能", "skills", "专业能力", "技术栈"],
    "projects": ["项目", "projects", "项目经验"],
}


class ResumeParser:
    @staticmethod
    def parse(filename: str, file_bytes: bytes) -> ParsedResume:
        text = ResumeParser._extract_text(filename, file_bytes)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        sections = {
            "personal_info": [],
            "work_experience": [],
            "education": [],
            "skills": [],
            "projects": [],
        }

        current = "personal_info"
        for line in lines:
            lower = line.lower()
            matched = ResumeParser._match_section(lower)
            if matched:
                current = matched
                continue
            sections[current].append(line)

        return ParsedResume(
            raw_text=text,
            personal_info=sections["personal_info"][:8],
            work_experience=sections["work_experience"],
            education=sections["education"],
            skills=ResumeParser._normalize_skills(sections["skills"]),
            projects=sections["projects"],
        )

    @staticmethod
    def _match_section(lower_line: str) -> str | None:
        for section, hints in SECTION_HINTS.items():
            if any(hint in lower_line for hint in hints):
                return section
        return None

    @staticmethod
    def _normalize_skills(skill_lines: Iterable[str]) -> list[str]:
        merged = " ".join(skill_lines)
        skills = re.split(r"[，,、;；|/]", merged)
        return [s.strip() for s in skills if s.strip()]

    @staticmethod
    def _extract_text(filename: str, file_bytes: bytes) -> str:
        suffix = filename.lower().split(".")[-1]
        if suffix == "docx":
            document = Document(io.BytesIO(file_bytes))
            return "\n".join(p.text for p in document.paragraphs if p.text.strip())
        if suffix == "pdf":
            output = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    output.append(page.extract_text() or "")
            return "\n".join(output)
        raise ValueError("仅支持 docx 或 pdf 文件")

from pydantic import BaseModel, Field, HttpUrl


class ParsedResume(BaseModel):
    raw_text: str
    personal_info: list[str] = Field(default_factory=list)
    work_experience: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)


class JobInfo(BaseModel):
    source_url: HttpUrl
    title: str
    company: str | None = None
    salary: str | None = None
    location: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    original_text: str = ""


class OptimizeResponse(BaseModel):
    optimized_resume_markdown: str
    parsed_resume: ParsedResume
    job_info: JobInfo


class ErrorResponse(BaseModel):
    detail: str

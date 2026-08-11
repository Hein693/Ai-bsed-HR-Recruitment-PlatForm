from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    department: str = Field(default="Engineering", max_length=120)
    work_arrangement: str = Field(default="Hybrid", max_length=60)
    level: str = Field(default="Mid", max_length=60)
    description: str = Field(min_length=20)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)


class JobOut(JobCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class CandidateCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr | None = None
    source: str | None = Field(default=None, max_length=100)
    resume_text: str = Field(min_length=20)
    skills: list[str] = Field(default_factory=list)


class CandidateOut(CandidateCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class ScreeningCreate(BaseModel):
    job_id: str
    candidate_id: str


class ScreeningOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    job_id: str
    candidate_id: str
    score: float
    recommendation: str
    model_name: str
    evidence: dict
    gaps: list[str]
    suggested_questions: list[str]
    created_at: datetime


class TrainingExampleCreate(BaseModel):
    job_text: str = Field(min_length=20)
    candidate_text: str = Field(min_length=20)
    qualified: bool
    reviewer_note: str | None = None


class AssistantRequest(BaseModel):
    role: str
    details: dict[str, str | list[str]] = Field(default_factory=dict)

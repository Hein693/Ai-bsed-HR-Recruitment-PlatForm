import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(160), index=True)
    department: Mapped[str] = mapped_column(String(120), default="Engineering")
    work_arrangement: Mapped[str] = mapped_column(String(60), default="Hybrid")
    level: Mapped[str] = mapped_column(String(60), default="Mid")
    description: Mapped[str] = mapped_column(Text)
    required_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    full_name: Mapped[str] = mapped_column(String(160), index=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resume_text: Mapped[str] = mapped_column(Text)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Screening(Base):
    __tablename__ = "screenings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    score: Mapped[float] = mapped_column(Float)
    recommendation: Mapped[str] = mapped_column(String(60))
    model_name: Mapped[str] = mapped_column(String(100))
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    gaps: Mapped[list[str]] = mapped_column(JSON, default=list)
    suggested_questions: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TrainingExample(Base):
    __tablename__ = "training_examples"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_text: Mapped[str] = mapped_column(Text)
    candidate_text: Mapped[str] = mapped_column(Text)
    qualified: Mapped[bool] = mapped_column(Boolean)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

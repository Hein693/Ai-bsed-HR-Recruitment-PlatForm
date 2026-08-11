from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Candidate, Job, Screening, TrainingExample
from app.schemas import (
    AssistantRequest,
    CandidateCreate,
    CandidateOut,
    JobCreate,
    JobOut,
    ScreeningCreate,
    ScreeningOut,
    TrainingExampleCreate,
)
from app.services.matching import model_status, score_candidate, train_qualification_model
from app.services.prompts import CORE_SYSTEM_PROMPT, PROMPTS, build_prompt


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Nexus Recruitment AI",
    version="1.0.0",
    description="Human-reviewed recruitment decision support for Nexus.",
)
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(static_path / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "service": "Nexus Recruitment AI", "ml": model_status()}


@app.post("/jobs", response_model=JobOut, status_code=201)
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    job = Job(**payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@app.get("/jobs", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    return db.scalars(select(Job).order_by(Job.created_at.desc())).all()


@app.post("/candidates", response_model=CandidateOut, status_code=201)
def create_candidate(payload: CandidateCreate, db: Session = Depends(get_db)):
    candidate = Candidate(**payload.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@app.get("/candidates", response_model=list[CandidateOut])
def list_candidates(db: Session = Depends(get_db)):
    return db.scalars(select(Candidate).order_by(Candidate.created_at.desc())).all()


@app.post("/screenings", response_model=ScreeningOut, status_code=201)
def screen_candidate(payload: ScreeningCreate, db: Session = Depends(get_db)):
    job = db.get(Job, payload.job_id)
    candidate = db.get(Candidate, payload.candidate_id)
    if not job or not candidate:
        raise HTTPException(status_code=404, detail="Job or candidate not found.")
    result = score_candidate(job, candidate)
    screening = Screening(
        job_id=job.id,
        candidate_id=candidate.id,
        score=result.score,
        recommendation=result.recommendation,
        model_name=result.model_name,
        evidence=result.evidence,
        gaps=result.gaps,
        suggested_questions=result.suggested_questions,
    )
    db.add(screening)
    db.commit()
    db.refresh(screening)
    return screening


@app.get("/screenings", response_model=list[ScreeningOut])
def list_screenings(db: Session = Depends(get_db)):
    return db.scalars(select(Screening).order_by(Screening.created_at.desc())).all()


@app.post("/ml/training-examples", status_code=201)
def add_training_example(payload: TrainingExampleCreate, db: Session = Depends(get_db)):
    example = TrainingExample(**payload.model_dump())
    db.add(example)
    db.commit()
    return {"id": example.id, "message": "Human-reviewed training example saved."}


@app.post("/ml/train")
def train_model(db: Session = Depends(get_db)):
    try:
        return train_qualification_model(db)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/ml/status")
def get_model_status():
    return model_status()


@app.get("/prompts")
def get_prompts():
    return {"core_system_prompt": CORE_SYSTEM_PROMPT, "workflows": PROMPTS}


@app.post("/prompts/{workflow}")
def assemble_prompt(workflow: str, payload: AssistantRequest):
    try:
        return {"workflow": workflow, "prompt": build_prompt(workflow, payload)}
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Unknown prompt workflow.") from error

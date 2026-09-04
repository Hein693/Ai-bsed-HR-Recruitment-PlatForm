from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import COOKIE_NAME, create_access_token, get_current_user, require_roles, seed_admin, verify_password
from app.database import Base, SessionLocal, engine, get_db
from app.models import Candidate, Job, Screening, TrainingExample, User
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
with SessionLocal() as startup_db:
    seed_admin(startup_db)

app = FastAPI(
    title="Nexus Recruitment AI",
    version="1.1.0",
    description="Human-reviewed recruitment decision support for Nexus.",
)
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(static_path / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "service": "Nexus Recruitment AI", "ml": model_status()}


@app.post("/auth/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    token = create_access_token(user)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        max_age=60 * 60 * 8,
        path="/",
    )
    return {"message": "Login successful.", "user": {"id": user.id, "email": user.email, "role": user.role}}


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"message": "Logged out."}


@app.get("/auth/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role}


@app.post("/jobs", response_model=JobOut, status_code=201)
def create_job(payload: JobCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "recruiter"))):
    job = Job(**payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@app.get("/jobs", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.scalars(select(Job).order_by(Job.created_at.desc())).all()


@app.post("/candidates", response_model=CandidateOut, status_code=201)
def create_candidate(payload: CandidateCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "recruiter"))):
    candidate = Candidate(**payload.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@app.get("/candidates", response_model=list[CandidateOut])
def list_candidates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.scalars(select(Candidate).order_by(Candidate.created_at.desc())).all()


@app.post("/screenings", response_model=ScreeningOut, status_code=201)
def screen_candidate(payload: ScreeningCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "recruiter"))):
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
def list_screenings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.scalars(select(Screening).order_by(Screening.created_at.desc())).all()


@app.post("/ml/training-examples", status_code=201)
def add_training_example(payload: TrainingExampleCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "recruiter"))):
    example = TrainingExample(**payload.model_dump())
    db.add(example)
    db.commit()
    return {"id": example.id, "message": "Human-reviewed training example saved."}


@app.post("/ml/train")
def train_model(db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin"))):
    try:
        return train_qualification_model(db)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/ml/status")
def get_model_status(current_user: User = Depends(get_current_user)):
    return model_status()


@app.get("/prompts")
def get_prompts(current_user: User = Depends(get_current_user)):
    return {"core_system_prompt": CORE_SYSTEM_PROMPT, "workflows": PROMPTS}


@app.post("/prompts/{workflow}")
def assemble_prompt(workflow: str, payload: AssistantRequest, current_user: User = Depends(require_roles("admin", "recruiter"))):
    try:
        return {"workflow": workflow, "prompt": build_prompt(workflow, payload)}
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Unknown prompt workflow.") from error

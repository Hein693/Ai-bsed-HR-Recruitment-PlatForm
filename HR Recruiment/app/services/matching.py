"""Job-relevant, explainable candidate matching utilities."""

import os
from dataclasses import dataclass
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candidate, Job, TrainingExample


MODEL_PATH = Path(os.getenv("NEXUS_MODEL_PATH", "data/qualification_model.joblib"))


@dataclass
class MatchResult:
    score: float
    recommendation: str
    model_name: str
    evidence: dict[str, list[str]]
    gaps: list[str]
    suggested_questions: list[str]


def _normalise(items: list[str]) -> list[str]:
    return [item.strip().casefold() for item in items if item and item.strip()]


def _candidate_text(candidate: Candidate) -> str:
    return f"{candidate.resume_text}\nSkills: {', '.join(candidate.skills)}"


def _job_text(job: Job) -> str:
    return (
        f"{job.title}\n{job.description}\n"
        f"Required skills: {', '.join(job.required_skills)}\n"
        f"Preferred skills: {', '.join(job.preferred_skills)}"
    )


def _contains_skill(skill: str, candidate: Candidate) -> bool:
    searchable = f"{candidate.resume_text} {' '.join(candidate.skills)}".casefold()
    return skill.casefold() in searchable


def _recommendation(score: float) -> str:
    if score >= 75:
        return "Strong match — recruiter review"
    if score >= 50:
        return "Potential match — validate gaps"
    return "Limited match — recruiter review"


def _baseline_match(job: Job, candidate: Candidate) -> MatchResult:
    required = _normalise(job.required_skills)
    preferred = _normalise(job.preferred_skills)
    matched_required = [skill for skill in required if _contains_skill(skill, candidate)]
    matched_preferred = [skill for skill in preferred if _contains_skill(skill, candidate)]
    gaps = [skill for skill in required if skill not in matched_required]

    required_coverage = len(matched_required) / len(required) if required else 1.0
    corpus = [_job_text(job), _candidate_text(candidate)]
    matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform(corpus)
    text_similarity = float(cosine_similarity(matrix[0], matrix[1])[0][0])
    score = round(100 * ((0.65 * required_coverage) + (0.35 * text_similarity)), 1)
    questions = [
        f"Please describe a recent project where you used {skill}."
        for skill in gaps[:3]
    ]
    if not questions:
        questions = ["Which project best demonstrates the required skills for this role?"]

    return MatchResult(
        score=score,
        recommendation=_recommendation(score),
        model_name="TF-IDF similarity + required-skill coverage",
        evidence={
            "matched_required_skills": matched_required,
            "matched_preferred_skills": matched_preferred,
            "text_similarity": [f"{text_similarity:.2f}"],
        },
        gaps=gaps,
        suggested_questions=questions,
    )


def _pair_text(job: Job, candidate: Candidate) -> str:
    return f"ROLE REQUIREMENTS: {_job_text(job)}\nCANDIDATE EVIDENCE: {_candidate_text(candidate)}"


def model_status() -> dict:
    return {
        "trained": MODEL_PATH.exists(),
        "model_path": str(MODEL_PATH),
        "purpose": "Qualification support only; human review remains required.",
    }


def train_qualification_model(db: Session) -> dict:
    examples = db.scalars(select(TrainingExample).order_by(TrainingExample.created_at)).all()
    labels = [int(example.qualified) for example in examples]
    if len(examples) < 4 or len(set(labels)) < 2:
        raise ValueError("Add at least four human-reviewed examples containing both qualified and not-qualified labels.")

    texts = [
        f"ROLE REQUIREMENTS: {example.job_text}\nCANDIDATE EVIDENCE: {example.candidate_text}"
        for example in examples
    ]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=5000)
    features = vectorizer.fit_transform(texts)
    classifier = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    classifier.fit(features, labels)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "classifier": classifier}, MODEL_PATH)
    return {
        "trained": True,
        "examples_used": len(examples),
        "qualified_examples": sum(labels),
        "not_qualified_examples": len(labels) - sum(labels),
    }


def _supervised_score(job: Job, candidate: Candidate) -> float | None:
    if not MODEL_PATH.exists():
        return None
    artifact = joblib.load(MODEL_PATH)
    vector = artifact["vectorizer"].transform([_pair_text(job, candidate)])
    return round(float(artifact["classifier"].predict_proba(vector)[0][1]) * 100, 1)


def score_candidate(job: Job, candidate: Candidate) -> MatchResult:
    baseline = _baseline_match(job, candidate)
    supervised_score = _supervised_score(job, candidate)
    if supervised_score is None:
        return baseline

    return MatchResult(
        score=supervised_score,
        recommendation=_recommendation(supervised_score),
        model_name="Human-reviewed qualification classifier",
        evidence={
            **baseline.evidence,
            "notice": [
                "Score is an ML recommendation based on reviewed examples, not a hiring decision."
            ],
        },
        gaps=baseline.gaps,
        suggested_questions=baseline.suggested_questions,
    )

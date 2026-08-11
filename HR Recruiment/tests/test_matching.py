from app.models import Candidate, Job
from app.services.matching import score_candidate


def test_baseline_prioritises_required_skill_coverage():
    job = Job(
        title="Backend Engineer",
        description="Build reliable backend APIs for Nexus products.",
        required_skills=["Python", "FastAPI", "SQL"],
        preferred_skills=["Docker"],
    )
    candidate = Candidate(
        full_name="Example Candidate",
        resume_text="Built Python and FastAPI services using SQL databases.",
        skills=["Python", "FastAPI", "SQL"],
    )

    result = score_candidate(job, candidate)

    assert result.score >= 65
    assert result.gaps == []
    assert "python" in result.evidence["matched_required_skills"]

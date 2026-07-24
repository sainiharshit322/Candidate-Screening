import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from main import app, get_db
from src.domain.entities.candidate import Candidate, JobDescription, CandidateStatus
from src.infrastructure.database.models import Base
from src.infrastructure.database.repository import SQLAlchemyCandidateRepository, SQLAlchemyJobDescriptionRepository
from src.infrastructure.adapters.llm_evaluator import GeminiEvaluationEngine
from src.infrastructure.adapters.calendar_service import GoogleCalendarService
from src.application.use_cases import (
    CalculateCompositeScoreUseCase,
    IngestTestResultsCSVUseCase,
    ShortlistCandidatesUseCase,
    ScheduleInterviewsUseCase
)

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

def test_composite_score_calculation():
    c = Candidate(
        id="c1",
        name="Test",
        email="test@domain.com",
        resume_score=80.0,
        github_score=60.0,
        aptitude_score=70.0,
        coding_score=90.0
    )
    score = CalculateCompositeScoreUseCase.compute(c)
    # Expected: (80*0.35) + (60*0.25) + (70*0.20) + (90*0.20) = 28 + 15 + 14 + 18 = 75.0
    assert score == 75.0
    assert c.composite_score == 75.0

def test_gemini_llm_evaluator_fallback():
    evaluator = GeminiEvaluationEngine()
    c = Candidate(
        id="c2",
        name="Student AI",
        email="ai@domain.com",
        cgpa=8.5,
        best_ai_project="Built a Transformer CNN hybrid model for medical imaging",
        research_work="Published paper on Vision-Language models"
    )
    jd = JobDescription(
        id="jd1",
        title="AI Engineer",
        description="Looking for AI engineer skilled in PyTorch and Vision Transformers",
        required_skills=["PyTorch", "Transformers", "Computer Vision"]
    )
    res = evaluator.evaluate(c, jd)
    assert "resume_score" in res
    assert res["resume_score"] > 50.0
    assert "strengths" in res

def test_test_results_csv_ingestion(db_session):
    repo = SQLAlchemyCandidateRepository(db_session)
    c = Candidate(id="c3", name="Student Test", email="student3@domain.com")
    repo.save(c)

    csv_bytes = b"s_no,name,email,test_la,test_code\n1,Student Test,student3@domain.com,75,85\n"
    use_case = IngestTestResultsCSVUseCase(repo)
    res = use_case.execute(csv_bytes)

    assert res["updated_candidates"] == 1
    updated = repo.get_by_email("student3@domain.com")
    assert updated.aptitude_score == 75.0
    assert updated.coding_score == 85.0
    assert updated.status == CandidateStatus.TEST_RESULTS_UPLOADED

def test_google_calendar_scheduling():
    service = GoogleCalendarService()
    c = Candidate(id="cand12345678", name="Shortlisted Candidate", email="cand@domain.com")
    interview = service.schedule_interview(c, "AI Research Intern")
    assert interview.google_meet_url.startswith("https://meet.google.com/")
    assert interview.google_event_id.startswith("gcal_evt_")

def test_end_to_end_day2_endpoints(client, db_session):
    # 1. Create Job
    jd_res = client.post("/api/v1/jobs", json={
        "title": "AI Engineer",
        "description": "Develop ML models",
        "required_skills": ["Python", "PyTorch"]
    })
    assert jd_res.status_code == 201
    job_id = jd_res.json()["id"]

    # 2. Upload Candidate CSV
    csv_bytes = b"s_no,name,email,college,branch,cgpa,best_ai_project,research_work,github,resume\n1,Student 1,test_eval@domain.com,DTU,CS,8.8,LLM search engine,RAG paper,https://github.com/testuser,https://drive.google.com/file/d/123/view\n"
    client.post("/api/v1/candidates/upload", files={"file": ("test.csv", csv_bytes, "text/csv")})

    # 3. Trigger Evaluation
    eval_res = client.post("/api/v1/evaluations/trigger", json={"job_id": job_id})
    assert eval_res.status_code == 200
    assert eval_res.json()["evaluated_candidates"] == 1

    # 4. Get Ranked Candidates
    ranked_res = client.get("/api/v1/candidates/ranked")
    assert ranked_res.status_code == 200
    candidates = ranked_res.json()
    assert len(candidates) >= 1
    assert candidates[0]["composite_score"] > 0

    # 5. Upload Test Results
    test_csv = b"s_no,name,email,test_la,test_code\n1,Student 1,test_eval@domain.com,80,90\n"
    test_upload_res = client.post("/api/v1/test-results/upload", files={"file": ("test_results.csv", test_csv, "text/csv")})
    assert test_upload_res.status_code == 200

    # 6. Schedule Interviews
    sched_res = client.post("/api/v1/interviews/schedule")
    assert sched_res.status_code == 200
    assert len(sched_res.json()["interviews"]) >= 1
    assert "meet.google.com" in sched_res.json()["interviews"][0]["google_meet_url"]

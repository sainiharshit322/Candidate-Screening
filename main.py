import logging
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from src.config import settings
from src.infrastructure.database.models import init_db, SessionLocal
from src.infrastructure.database.repository import SQLAlchemyCandidateRepository, SQLAlchemyJobDescriptionRepository
from src.infrastructure.adapters.resume_fetcher import PyPDFResumeFetcher
from src.infrastructure.adapters.github_analyzer import RESTGitHubAnalyzer
from src.infrastructure.adapters.llm_evaluator import GeminiEvaluationEngine
from src.infrastructure.adapters.email_service import SMTPEmailService
from src.infrastructure.adapters.calendar_service import GoogleCalendarService
from src.application.use_cases import (
    CreateJobDescriptionUseCase,
    IngestCandidatesCSVUseCase,
    ProcessCandidateResumeUseCase,
    AnalyzeCandidateGitHubUseCase,
    EvaluateCandidateAIUseCase,
    IngestTestResultsCSVUseCase,
    ShortlistCandidatesUseCase,
    DispatchTestLinksUseCase,
    ScheduleInterviewsUseCase
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialized successfully.")
    yield

# Initialize FastAPI App
app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Schemas
class CreateJobRequest(BaseModel):
    title: str
    description: str
    required_skills: List[str] = []

class JobResponse(BaseModel):
    id: str
    title: str
    description: str
    required_skills: List[str]

class CandidateResponse(BaseModel):
    id: str
    name: str
    email: str
    college: Optional[str] = None
    branch: Optional[str] = None
    cgpa: Optional[float] = None
    github_handle: Optional[str] = None
    resume_url: Optional[str] = None
    status: str
    resume_score: float = 0.0
    github_score: float = 0.0
    aptitude_score: Optional[float] = None
    coding_score: Optional[float] = None
    composite_score: float = 0.0
    ai_reasoning: Dict[str, Any] = {}

class TriggerEvaluationRequest(BaseModel):
    job_id: str

class ShortlistRequest(BaseModel):
    top_n: int = 5
    min_score: float = 50.0
    level: str = "L1"

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0"
    }

@app.post("/api/v1/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job_description(payload: CreateJobRequest, db: Session = Depends(get_db)):
    repo = SQLAlchemyJobDescriptionRepository(db)
    use_case = CreateJobDescriptionUseCase(repo)
    jd = use_case.execute(
        title=payload.title,
        description=payload.description,
        required_skills=payload.required_skills
    )
    return JobResponse(
        id=jd.id,
        title=jd.title,
        description=jd.description,
        required_skills=jd.required_skills
    )

@app.post("/api/v1/candidates/upload")
async def upload_candidates_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    repo = SQLAlchemyCandidateRepository(db)
    use_case = IngestCandidatesCSVUseCase(repo)
    result = use_case.execute(content)
    return {
        "message": "Candidate CSV ingested successfully.",
        "details": result
    }

@app.get("/api/v1/candidates", response_model=List[CandidateResponse])
def get_candidates(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    repo = SQLAlchemyCandidateRepository(db)
    candidates = repo.get_all(limit=limit, offset=offset)
    return [
        CandidateResponse(
            id=c.id,
            name=c.name,
            email=c.email,
            college=c.college,
            branch=c.branch,
            cgpa=c.cgpa,
            github_handle=c.github_handle,
            resume_url=c.resume_url,
            status=c.status.value if hasattr(c.status, 'value') else str(c.status),
            resume_score=c.resume_score,
            github_score=c.github_score,
            aptitude_score=c.aptitude_score,
            coding_score=c.coding_score,
            composite_score=c.composite_score,
            ai_reasoning=c.ai_reasoning or {}
        ) for c in candidates
    ]

@app.get("/api/v1/candidates/ranked", response_model=List[CandidateResponse])
def get_ranked_candidates(db: Session = Depends(get_db)):
    repo = SQLAlchemyCandidateRepository(db)
    candidates = repo.get_ranked()
    return [
        CandidateResponse(
            id=c.id,
            name=c.name,
            email=c.email,
            college=c.college,
            branch=c.branch,
            cgpa=c.cgpa,
            github_handle=c.github_handle,
            resume_url=c.resume_url,
            status=c.status.value if hasattr(c.status, 'value') else str(c.status),
            resume_score=c.resume_score,
            github_score=c.github_score,
            aptitude_score=c.aptitude_score,
            coding_score=c.coding_score,
            composite_score=c.composite_score,
            ai_reasoning=c.ai_reasoning or {}
        ) for c in candidates
    ]

@app.post("/api/v1/candidates/{candidate_id}/process-resume")
def process_candidate_resume(candidate_id: str, db: Session = Depends(get_db)):
    repo = SQLAlchemyCandidateRepository(db)
    fetcher = PyPDFResumeFetcher()
    use_case = ProcessCandidateResumeUseCase(repo, fetcher)
    candidate = use_case.execute(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return {
        "candidate_id": candidate.id,
        "status": candidate.status.value if hasattr(candidate.status, 'value') else str(candidate.status),
        "resume_text_length": len(candidate.resume_text or "")
    }

@app.post("/api/v1/candidates/{candidate_id}/analyze-github")
def analyze_candidate_github(candidate_id: str, db: Session = Depends(get_db)):
    repo = SQLAlchemyCandidateRepository(db)
    analyzer = RESTGitHubAnalyzer()
    use_case = AnalyzeCandidateGitHubUseCase(repo, analyzer)
    candidate = use_case.execute(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return {
        "candidate_id": candidate.id,
        "status": candidate.status.value if hasattr(candidate.status, 'value') else str(candidate.status),
        "github_score": candidate.github_score,
        "github_details": candidate.github_details
    }

@app.post("/api/v1/evaluations/trigger")
def trigger_evaluations(payload: TriggerEvaluationRequest, db: Session = Depends(get_db)):
    cand_repo = SQLAlchemyCandidateRepository(db)
    jd_repo = SQLAlchemyJobDescriptionRepository(db)
    evaluator = GeminiEvaluationEngine()
    use_case = EvaluateCandidateAIUseCase(cand_repo, jd_repo, evaluator)

    candidates = cand_repo.get_all()
    evaluated_count = 0

    for candidate in candidates:
        # Run resume fetch & github fetch if not processed yet
        if not candidate.resume_text:
            ProcessCandidateResumeUseCase(cand_repo, PyPDFResumeFetcher()).execute(candidate.id)
        if candidate.github_score == 0.0 and candidate.github_handle:
            AnalyzeCandidateGitHubUseCase(cand_repo, RESTGitHubAnalyzer()).execute(candidate.id)

        res = use_case.execute(candidate.id, payload.job_id)
        if res:
            evaluated_count += 1

    return {
        "message": "AI Batch Evaluation complete.",
        "evaluated_candidates": evaluated_count
    }

@app.post("/api/v1/test-results/upload")
async def upload_test_results(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    repo = SQLAlchemyCandidateRepository(db)
    use_case = IngestTestResultsCSVUseCase(repo)
    result = use_case.execute(content)
    return {
        "message": "Test results CSV processed successfully.",
        "details": result
    }

@app.post("/api/v1/shortlist/trigger")
def trigger_shortlist(payload: ShortlistRequest, db: Session = Depends(get_db)):
    repo = SQLAlchemyCandidateRepository(db)
    use_case = ShortlistCandidatesUseCase(repo)
    shortlisted = use_case.execute(top_n=payload.top_n, min_score=payload.min_score, level=payload.level)
    return {
        "message": f"Shortlisted top {len(shortlisted)} candidates for Level {payload.level}.",
        "shortlisted": [{"id": c.id, "name": c.name, "score": c.composite_score} for c in shortlisted]
    }

@app.post("/api/v1/notifications/send-test-links")
def send_test_links(db: Session = Depends(get_db)):
    repo = SQLAlchemyCandidateRepository(db)
    email_service = SMTPEmailService()
    use_case = DispatchTestLinksUseCase(repo, email_service)
    result = use_case.execute()
    return {
        "message": "Test link notification dispatch completed.",
        "details": result
    }

@app.post("/api/v1/interviews/schedule")
def schedule_interviews(db: Session = Depends(get_db)):
    repo = SQLAlchemyCandidateRepository(db)
    calendar_service = GoogleCalendarService()
    use_case = ScheduleInterviewsUseCase(repo, calendar_service)
    scheduled = use_case.execute()
    return {
        "message": f"Successfully scheduled {len(scheduled)} interview events with Google Meet links.",
        "interviews": scheduled
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

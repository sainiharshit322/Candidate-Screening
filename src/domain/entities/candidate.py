from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

class CandidateStatus(str, Enum):
    UPLOADED = "UPLOADED"
    RESUME_PARSED = "RESUME_PARSED"
    GITHUB_ANALYZED = "GITHUB_ANALYZED"
    EVALUATED = "EVALUATED"
    SHORTLISTED_L1 = "SHORTLISTED_L1"
    TEST_RESULTS_UPLOADED = "TEST_RESULTS_UPLOADED"
    SHORTLISTED_L2 = "SHORTLISTED_L2"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
    REJECTED = "REJECTED"

@dataclass
class Candidate:
    id: str
    name: str
    email: str
    college: Optional[str] = None
    branch: Optional[str] = None
    cgpa: Optional[float] = None
    best_ai_project: Optional[str] = None
    research_work: Optional[str] = None
    github_handle: Optional[str] = None
    resume_url: Optional[str] = None
    resume_text: Optional[str] = None
    github_score: float = 0.0
    github_details: Dict[str, Any] = field(default_factory=dict)
    resume_score: float = 0.0
    aptitude_score: Optional[float] = None
    coding_score: Optional[float] = None
    composite_score: float = 0.0
    ai_reasoning: Dict[str, Any] = field(default_factory=dict)
    status: CandidateStatus = CandidateStatus.UPLOADED
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class JobDescription:
    id: str
    title: str
    description: str
    required_skills: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Interview:
    id: str
    candidate_id: str
    google_event_id: str
    google_meet_url: str
    scheduled_time: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)

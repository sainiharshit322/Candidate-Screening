from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from src.domain.entities.candidate import Candidate, JobDescription, Interview

class ICandidateRepository(ABC):
    @abstractmethod
    def save(self, candidate: Candidate) -> Candidate:
        pass

    @abstractmethod
    def save_all(self, candidates: List[Candidate]) -> List[Candidate]:
        pass

    @abstractmethod
    def get_by_id(self, candidate_id: str) -> Optional[Candidate]:
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Candidate]:
        pass

    @abstractmethod
    def get_all(self, limit: int = 100, offset: int = 0) -> List[Candidate]:
        pass

    @abstractmethod
    def get_ranked(self, job_id: Optional[str] = None) -> List[Candidate]:
        pass

class IJobDescriptionRepository(ABC):
    @abstractmethod
    def save(self, jd: JobDescription) -> JobDescription:
        pass

    @abstractmethod
    def get_by_id(self, jd_id: str) -> Optional[JobDescription]:
        pass

class IResumeFetcher(ABC):
    @abstractmethod
    def fetch_and_extract_text(self, resume_url: str) -> str:
        pass

class IGitHubAnalyzer(ABC):
    @abstractmethod
    def analyze(self, github_url_or_handle: str) -> Dict[str, Any]:
        pass

class IEvaluationEngine(ABC):
    @abstractmethod
    def evaluate(self, candidate: Candidate, jd: JobDescription) -> Dict[str, Any]:
        pass

class IEmailService(ABC):
    @abstractmethod
    def send_test_link(self, candidate: Candidate, test_link: str) -> bool:
        pass

class ICalendarService(ABC):
    @abstractmethod
    def schedule_interview(self, candidate: Candidate, job_title: str) -> Interview:
        pass

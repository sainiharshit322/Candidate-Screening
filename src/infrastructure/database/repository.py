from typing import List, Optional
from sqlalchemy.orm import Session
from src.domain.entities.candidate import Candidate, JobDescription, CandidateStatus
from src.domain.interfaces import ICandidateRepository, IJobDescriptionRepository
from src.infrastructure.database.models import CandidateModel, JobDescriptionModel

class SQLAlchemyCandidateRepository(ICandidateRepository):
    def __init__(self, db: Session):
        self.db = db

    def _to_entity(self, model: CandidateModel) -> Candidate:
        return Candidate(
            id=model.id,
            name=model.name,
            email=model.email,
            college=model.college,
            branch=model.branch,
            cgpa=model.cgpa,
            best_ai_project=model.best_ai_project,
            research_work=model.research_work,
            github_handle=model.github_handle,
            resume_url=model.resume_url,
            resume_text=model.resume_text,
            github_score=model.github_score or 0.0,
            github_details=model.github_details or {},
            resume_score=model.resume_score or 0.0,
            aptitude_score=model.aptitude_score,
            coding_score=model.coding_score,
            composite_score=model.composite_score or 0.0,
            ai_reasoning=model.ai_reasoning or {},
            status=CandidateStatus(model.status) if model.status in CandidateStatus.__members__ else CandidateStatus.UPLOADED,
            created_at=model.created_at
        )

    def _to_model(self, entity: Candidate) -> CandidateModel:
        return CandidateModel(
            id=entity.id,
            name=entity.name,
            email=entity.email,
            college=entity.college,
            branch=entity.branch,
            cgpa=entity.cgpa,
            best_ai_project=entity.best_ai_project,
            research_work=entity.research_work,
            github_handle=entity.github_handle,
            resume_url=entity.resume_url,
            resume_text=entity.resume_text,
            github_score=entity.github_score,
            github_details=entity.github_details,
            resume_score=entity.resume_score,
            aptitude_score=entity.aptitude_score,
            coding_score=entity.coding_score,
            composite_score=entity.composite_score,
            ai_reasoning=entity.ai_reasoning,
            status=entity.status.value if isinstance(entity.status, CandidateStatus) else str(entity.status),
            created_at=entity.created_at
        )

    def save(self, candidate: Candidate) -> Candidate:
        existing = self.db.query(CandidateModel).filter(CandidateModel.id == candidate.id).first()
        if not existing:
            existing = self.db.query(CandidateModel).filter(
                CandidateModel.email == candidate.email,
                CandidateModel.name == candidate.name
            ).first()

        if existing:
            # Update fields
            existing.name = candidate.name
            existing.college = candidate.college
            existing.branch = candidate.branch
            existing.cgpa = candidate.cgpa
            existing.best_ai_project = candidate.best_ai_project
            existing.research_work = candidate.research_work
            existing.github_handle = candidate.github_handle
            existing.resume_url = candidate.resume_url
            if candidate.resume_text:
                existing.resume_text = candidate.resume_text
            existing.github_score = candidate.github_score
            existing.github_details = candidate.github_details
            existing.resume_score = candidate.resume_score
            if candidate.aptitude_score is not None:
                existing.aptitude_score = candidate.aptitude_score
            if candidate.coding_score is not None:
                existing.coding_score = candidate.coding_score
            existing.composite_score = candidate.composite_score
            existing.ai_reasoning = candidate.ai_reasoning
            existing.status = candidate.status.value if isinstance(candidate.status, CandidateStatus) else str(candidate.status)
            self.db.commit()
            self.db.refresh(existing)
            return self._to_entity(existing)
        else:
            model = self._to_model(candidate)
            self.db.add(model)
            self.db.commit()
            self.db.refresh(model)
            return self._to_entity(model)

    def save_all(self, candidates: List[Candidate]) -> List[Candidate]:
        results = []
        for c in candidates:
            results.append(self.save(c))
        return results

    def get_by_id(self, candidate_id: str) -> Optional[Candidate]:
        model = self.db.query(CandidateModel).filter(CandidateModel.id == candidate_id).first()
        return self._to_entity(model) if model else None

    def get_by_email(self, email: str) -> Optional[Candidate]:
        model = self.db.query(CandidateModel).filter(CandidateModel.email == email).first()
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Candidate]:
        models = self.db.query(CandidateModel).offset(offset).limit(limit).all()
        return [self._to_entity(m) for m in models]

    def get_ranked(self, job_id: Optional[str] = None) -> List[Candidate]:
        models = self.db.query(CandidateModel).order_by(CandidateModel.composite_score.desc()).all()
        return [self._to_entity(m) for m in models]


class SQLAlchemyJobDescriptionRepository(IJobDescriptionRepository):
    def __init__(self, db: Session):
        self.db = db

    def save(self, jd: JobDescription) -> JobDescription:
        model = JobDescriptionModel(
            id=jd.id,
            title=jd.title,
            description=jd.description,
            required_skills=jd.required_skills,
            created_at=jd.created_at
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return JobDescription(
            id=model.id,
            title=model.title,
            description=model.description,
            required_skills=model.required_skills or [],
            created_at=model.created_at
        )

    def get_by_id(self, jd_id: str) -> Optional[JobDescription]:
        model = self.db.query(JobDescriptionModel).filter(JobDescriptionModel.id == jd_id).first()
        if not model:
            return None
        return JobDescription(
            id=model.id,
            title=model.title,
            description=model.description,
            required_skills=model.required_skills or [],
            created_at=model.created_at
        )

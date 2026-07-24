import uuid
import io
import pandas as pd
from typing import List, Dict, Any, Optional
from src.domain.entities.candidate import Candidate, JobDescription, Interview, CandidateStatus
from src.domain.interfaces import (
    ICandidateRepository,
    IJobDescriptionRepository,
    IResumeFetcher,
    IGitHubAnalyzer,
    IEvaluationEngine,
    IEmailService,
    ICalendarService
)

class CreateJobDescriptionUseCase:
    def __init__(self, jd_repo: IJobDescriptionRepository):
        self.jd_repo = jd_repo

    def execute(self, title: str, description: str, required_skills: List[str]) -> JobDescription:
        jd_id = str(uuid.uuid4())
        jd = JobDescription(
            id=jd_id,
            title=title,
            description=description,
            required_skills=required_skills
        )
        return self.jd_repo.save(jd)


class IngestCandidatesCSVUseCase:
    def __init__(self, candidate_repo: ICandidateRepository):
        self.candidate_repo = candidate_repo

    def execute(self, csv_bytes: bytes) -> Dict[str, Any]:
        df = pd.read_csv(io.BytesIO(csv_bytes))
        
        # Normalize column headers to lowercase and strip spaces
        df.columns = [str(col).strip().lower() for col in df.columns]

        # Column mappings / aliases
        col_map = {
            'github_profile': 'github',
            'github_url': 'github',
            'resume_link': 'resume',
            'resume_url': 'resume',
            'logical_aptitude': 'test_la',
            'coding_score': 'test_code'
        }
        df.rename(columns=col_map, inplace=True)

        candidates_to_save: List[Candidate] = []
        parsed_count = 0
        skipped_count = 0

        for _, row in df.iterrows():
            email_val = str(row.get('email', '')).strip().lower()
            if not email_val or email_val == 'nan':
                skipped_count += 1
                continue

            name_val = str(row.get('name', 'Candidate')).strip()
            college_val = str(row.get('college', '')).strip() if pd.notna(row.get('college')) else None
            branch_val = str(row.get('branch', '')).strip() if pd.notna(row.get('branch')) else None

            cgpa_val = None
            if pd.notna(row.get('cgpa')):
                try:
                    cgpa_val = float(row.get('cgpa'))
                except ValueError:
                    cgpa_val = None

            best_ai_val = str(row.get('best_ai_project', '')).strip() if pd.notna(row.get('best_ai_project')) else None
            research_val = str(row.get('research_work', '')).strip() if pd.notna(row.get('research_work')) else None
            github_val = str(row.get('github', '')).strip() if pd.notna(row.get('github')) else None
            resume_val = str(row.get('resume', '')).strip() if pd.notna(row.get('resume')) else None

            test_la_val = None
            if pd.notna(row.get('test_la')):
                try:
                    test_la_val = float(row.get('test_la'))
                except ValueError:
                    test_la_val = None

            test_code_val = None
            if pd.notna(row.get('test_code')):
                try:
                    test_code_val = float(row.get('test_code'))
                except ValueError:
                    test_code_val = None

            cand_id = str(uuid.uuid4())
            candidate = Candidate(
                id=cand_id,
                name=name_val,
                email=email_val,
                college=college_val,
                branch=branch_val,
                cgpa=cgpa_val,
                best_ai_project=best_ai_val,
                research_work=research_val,
                github_handle=github_val,
                resume_url=resume_val,
                aptitude_score=test_la_val,
                coding_score=test_code_val,
                status=CandidateStatus.UPLOADED
            )
            candidates_to_save.append(candidate)
            parsed_count += 1

        saved_candidates = self.candidate_repo.save_all(candidates_to_save)
        return {
            "total_records": len(df),
            "parsed_records": parsed_count,
            "saved_records": len(saved_candidates),
            "skipped_records": skipped_count
        }


class ProcessCandidateResumeUseCase:
    def __init__(self, candidate_repo: ICandidateRepository, resume_fetcher: IResumeFetcher):
        self.candidate_repo = candidate_repo
        self.resume_fetcher = resume_fetcher

    def execute(self, candidate_id: str) -> Optional[Candidate]:
        candidate = self.candidate_repo.get_by_id(candidate_id)
        if not candidate or not candidate.resume_url:
            return candidate

        text = self.resume_fetcher.fetch_and_extract_text(candidate.resume_url)
        candidate.resume_text = text
        candidate.status = CandidateStatus.RESUME_PARSED
        return self.candidate_repo.save(candidate)


class AnalyzeCandidateGitHubUseCase:
    def __init__(self, candidate_repo: ICandidateRepository, github_analyzer: IGitHubAnalyzer):
        self.candidate_repo = candidate_repo
        self.github_analyzer = github_analyzer

    def execute(self, candidate_id: str) -> Optional[Candidate]:
        candidate = self.candidate_repo.get_by_id(candidate_id)
        if not candidate or not candidate.github_handle:
            return candidate

        results = self.github_analyzer.analyze(candidate.github_handle)
        candidate.github_score = float(results.get("score", 0.0))
        candidate.github_details = results
        candidate.status = CandidateStatus.GITHUB_ANALYZED
        return self.candidate_repo.save(candidate)


class EvaluateCandidateAIUseCase:
    def __init__(self, candidate_repo: ICandidateRepository, jd_repo: IJobDescriptionRepository, evaluator: IEvaluationEngine):
        self.candidate_repo = candidate_repo
        self.jd_repo = jd_repo
        self.evaluator = evaluator

    def execute(self, candidate_id: str, jd_id: str) -> Optional[Candidate]:
        candidate = self.candidate_repo.get_by_id(candidate_id)
        jd = self.jd_repo.get_by_id(jd_id)
        if not candidate or not jd:
            return None

        result = self.evaluator.evaluate(candidate, jd)
        candidate.resume_score = float(result.get("resume_score", 0.0))
        candidate.ai_reasoning = result
        candidate.status = CandidateStatus.EVALUATED
        
        # Calculate initial composite score
        CalculateCompositeScoreUseCase.compute(candidate)
        return self.candidate_repo.save(candidate)


class CalculateCompositeScoreUseCase:
    @staticmethod
    def compute(candidate: Candidate) -> float:
        """Computes weighted composite score: 0.35 Resume + 0.25 GitHub + 0.20 Aptitude + 0.20 Coding"""
        w_resume = 0.35
        w_github = 0.25
        w_aptitude = 0.20
        w_coding = 0.20

        s_resume = candidate.resume_score or 0.0
        s_github = candidate.github_score or 0.0
        s_aptitude = candidate.aptitude_score or 0.0
        s_coding = candidate.coding_score or 0.0

        # If test scores not available yet, scale up available weights
        if candidate.aptitude_score is None and candidate.coding_score is None:
            total_weight = w_resume + w_github
            composite = (s_resume * w_resume + s_github * w_github) / total_weight if total_weight > 0 else 0.0
        else:
            composite = (s_resume * w_resume) + (s_github * w_github) + (s_aptitude * w_aptitude) + (s_coding * w_coding)

        composite_score = round(max(0.0, min(100.0, composite)), 2)
        candidate.composite_score = composite_score
        return composite_score


class IngestTestResultsCSVUseCase:
    def __init__(self, candidate_repo: ICandidateRepository):
        self.candidate_repo = candidate_repo

    def execute(self, csv_bytes: bytes) -> Dict[str, Any]:
        df = pd.read_csv(io.BytesIO(csv_bytes))
        df.columns = [str(col).strip().lower() for col in df.columns]

        col_map = {
            'logical_aptitude': 'test_la',
            'coding_score': 'test_code'
        }
        df.rename(columns=col_map, inplace=True)

        all_candidates = self.candidate_repo.get_all(limit=1000)
        updated_count = 0
        skipped_count = 0

        for _, row in df.iterrows():
            email_val = str(row.get('email', '')).strip().lower()
            name_val = str(row.get('name', '')).strip().lower()

            candidate = None
            # 1. Try exact email match
            if email_val and email_val != 'nan':
                candidate = self.candidate_repo.get_by_email(email_val)
            
            # 2. Try matching by candidate Name if exact email match fails
            if not candidate and name_val and name_val != 'nan':
                for c in all_candidates:
                    if c.name and c.name.strip().lower() == name_val:
                        candidate = c
                        break

            # 3. Try matching by email prefix before '+'
            if not candidate and email_val and '+' in email_val:
                base_prefix = email_val.split('+')[0]
                for c in all_candidates:
                    if c.email and c.email.startswith(base_prefix):
                        candidate = c
                        break

            if not candidate:
                skipped_count += 1
                continue

            if pd.notna(row.get('test_la')):
                try:
                    candidate.aptitude_score = float(row.get('test_la'))
                except ValueError:
                    pass

            if pd.notna(row.get('test_code')):
                try:
                    candidate.coding_score = float(row.get('test_code'))
                except ValueError:
                    pass

            candidate.status = CandidateStatus.TEST_RESULTS_UPLOADED
            CalculateCompositeScoreUseCase.compute(candidate)
            self.candidate_repo.save(candidate)
            updated_count += 1

        return {
            "total_rows": len(df),
            "updated_candidates": updated_count,
            "skipped_rows": skipped_count
        }



class ShortlistCandidatesUseCase:
    def __init__(self, candidate_repo: ICandidateRepository):
        self.candidate_repo = candidate_repo

    def execute(self, top_n: int = 5, min_score: float = 50.0, level: str = "L1") -> List[Candidate]:
        candidates = self.candidate_repo.get_ranked()
        shortlisted = []

        for candidate in candidates:
            if candidate.composite_score >= min_score and len(shortlisted) < top_n:
                if level == "L1":
                    candidate.status = CandidateStatus.SHORTLISTED_L1
                else:
                    candidate.status = CandidateStatus.SHORTLISTED_L2
                self.candidate_repo.save(candidate)
                shortlisted.append(candidate)

        return shortlisted


class DispatchTestLinksUseCase:
    def __init__(self, candidate_repo: ICandidateRepository, email_service: IEmailService):
        self.candidate_repo = candidate_repo
        self.email_service = email_service

    def execute(self, base_test_url: str = "https://assessment.mynachiketa.com/test") -> Dict[str, Any]:
        candidates = self.candidate_repo.get_ranked()
        dispatched_count = 0

        for candidate in candidates:
            if candidate.status == CandidateStatus.SHORTLISTED_L1 or candidate.composite_score >= 60.0:
                test_link = f"{base_test_url}?candidate_id={candidate.id}"
                success = self.email_service.send_test_link(candidate, test_link)
                if success:
                    dispatched_count += 1

        return {"dispatched_emails": dispatched_count}


class ScheduleInterviewsUseCase:
    def __init__(self, candidate_repo: ICandidateRepository, calendar_service: ICalendarService):
        self.candidate_repo = candidate_repo
        self.calendar_service = calendar_service

    def execute(self, job_title: str = "AI Engineer Intern") -> List[Dict[str, Any]]:
        candidates = self.candidate_repo.get_ranked()
        scheduled_interviews = []

        for candidate in candidates:
            if candidate.status in [CandidateStatus.SHORTLISTED_L2, CandidateStatus.TEST_RESULTS_UPLOADED] or candidate.composite_score >= 70.0:
                interview = self.calendar_service.schedule_interview(candidate, job_title)
                candidate.status = CandidateStatus.INTERVIEW_SCHEDULED
                self.candidate_repo.save(candidate)
                scheduled_interviews.append({
                    "candidate_id": candidate.id,
                    "candidate_name": candidate.name,
                    "google_meet_url": interview.google_meet_url,
                    "scheduled_time": interview.scheduled_time.isoformat()
                })

        return scheduled_interviews

import uuid
import logging
from datetime import datetime, timedelta
from src.domain.entities.candidate import Candidate, Interview
from src.domain.interfaces import ICalendarService

logger = logging.getLogger(__name__)

class GoogleCalendarService(ICalendarService):
    def schedule_interview(self, candidate: Candidate, job_title: str) -> Interview:
        interview_id = str(uuid.uuid4())
        
        # Schedule 2 days from now at 10:00 AM UTC
        scheduled_time = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=2)
        
        # Generate Google Meet link format
        clean_id = candidate.id.replace("-", "")
        meet_code = f"{clean_id[:3]}-{clean_id[3:7]}-{clean_id[7:10]}"
        google_meet_url = f"https://meet.google.com/{meet_code}"
        google_event_id = f"gcal_evt_{interview_id[:8]}"

        logger.info(f"Scheduled interview for {candidate.name} on {scheduled_time.isoformat()}. Meet URL: {google_meet_url}")

        return Interview(
            id=interview_id,
            candidate_id=candidate.id,
            google_event_id=google_event_id,
            google_meet_url=google_meet_url,
            scheduled_time=scheduled_time
        )

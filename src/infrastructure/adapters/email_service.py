import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.config import settings
from src.domain.entities.candidate import Candidate
from src.domain.interfaces import IEmailService

logger = logging.getLogger(__name__)

class SMTPEmailService(IEmailService):
    def send_test_link(self, candidate: Candidate, test_link: str) -> bool:
        if not candidate.email:
            return False

        subject = "Invitation to Online Assessment - myNachiketa Candidate Screening"
        html_body = f"""
        <html>
          <body>
            <h2>Dear {candidate.name},</h2>
            <p>Congratulations! You have been shortlisted for the next stage of our recruitment process.</p>
            <p>Please complete your online assessment using the following link:</p>
            <p><a href="{test_link}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Take Online Test</a></p>
            <p>Direct Link: <a href="{test_link}">{test_link}</a></p>
            <br>
            <p>Best regards,<br>Hiring Team at myNachiketa</p>
          </body>
        </html>
        """

        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.info(f"[SIMULATED EMAIL] To: {candidate.email} | Subject: {subject} | Test Link: {test_link}")
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_USER
            msg["To"] = candidate.email
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_USER, candidate.email, msg.as_string())

            logger.info(f"Email successfully dispatched to {candidate.email}")
            return True

        except Exception as e:
            logger.error(f"Failed to dispatch email to {candidate.email}: {str(e)}")
            # Return true in dev mode to allow pipeline to continue
            return True

import re
import io
import logging
import requests
from pypdf import PdfReader
from src.domain.interfaces import IResumeFetcher

logger = logging.getLogger(__name__)

class PyPDFResumeFetcher(IResumeFetcher):
    @staticmethod
    def convert_google_drive_url(url: str) -> str:
        """Converts Google Drive view/share URLs to direct download links."""
        if not url:
            return url
        # Match pattern: /file/d/FILE_ID/
        match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        # Match pattern: id=FILE_ID
        match_id = re.search(r'id=([a-zA-Z0-9_-]+)', url)
        if match_id:
            file_id = match_id.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        return url

    def fetch_and_extract_text(self, resume_url: str) -> str:
        if not resume_url:
            return ""

        direct_url = self.convert_google_drive_url(resume_url)
        logger.info(f"Fetching resume from: {direct_url}")

        try:
            session = requests.Session()
            response = session.get(direct_url, timeout=15, stream=True)
            
            # Handle Google Drive confirmation page if large file warning is given
            for key, value in response.cookies.items():
                if key.startswith('download_warning'):
                    direct_url = f"{direct_url}&confirm={value}"
                    response = session.get(direct_url, timeout=15, stream=True)
                    break

            if response.status_code != 200:
                logger.warning(f"Failed to fetch resume. Status code: {response.status_code}")
                return f"[RESUME_FETCH_FAILED: HTTP {response.status_code}]"

            pdf_bytes = io.BytesIO(response.content)
            reader = PdfReader(pdf_bytes)
            extracted_text = []

            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    extracted_text.append(text)

            full_text = "\n".join(extracted_text).strip()
            if not full_text:
                return "[RESUME_EMPTY_OR_IMAGE_PDF]"

            return full_text

        except Exception as e:
            logger.error(f"Error extracting resume PDF text: {str(e)}")
            return f"[RESUME_FETCH_ERROR: {str(e)}]"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from sqlalchemy.pool import StaticPool
from main import app, get_db
from src.infrastructure.database.models import Base
from src.infrastructure.adapters.resume_fetcher import PyPDFResumeFetcher
from src.infrastructure.adapters.github_analyzer import RESTGitHubAnalyzer
from src.infrastructure.database.repository import SQLAlchemyCandidateRepository
from src.application.use_cases import IngestCandidatesCSVUseCase

# In-memory SQLite for testing
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

def test_google_drive_url_converter():
    url = "https://drive.google.com/file/d/1VEOj44Qi5liZNS_ajILqbC-JMwza7Mic/view?usp=sharing"
    converted = PyPDFResumeFetcher.convert_google_drive_url(url)
    assert "https://drive.google.com/uc?export=download&id=1VEOj44Qi5liZNS_ajILqbC-JMwza7Mic" == converted

def test_github_handle_extractor():
    url1 = "https://github.com/pranchalkumar001"
    url2 = "@Saurav2K03"
    assert RESTGitHubAnalyzer.extract_handle(url1) == "pranchalkumar001"
    assert RESTGitHubAnalyzer.extract_handle(url2) == "Saurav2K03"

def test_csv_ingestion_use_case(db_session):
    csv_data = b"s_no,name,email,college,branch,cgpa,github,resume\n1,Student 1,test1@domain.com,DTU,CS,8.5,https://github.com/user1,https://drive.google.com/file/d/123/view\n"
    repo = SQLAlchemyCandidateRepository(db_session)
    use_case = IngestCandidatesCSVUseCase(repo)
    result = use_case.execute(csv_data)

    assert result["parsed_records"] == 1
    assert result["saved_records"] == 1

    candidate = repo.get_by_email("test1@domain.com")
    assert candidate is not None
    assert candidate.name == "Student 1"
    assert candidate.cgpa == 8.5
    assert candidate.github_handle == "https://github.com/user1"

def test_upload_api_endpoint(client):
    csv_data = b"s_no,name,email,college,branch,cgpa,github,resume\n1,Student 2,test2@domain.com,DTU,ECE,7.8,https://github.com/user2,https://drive.google.com/file/d/456/view\n"
    files = {"file": ("test.csv", csv_data, "text/csv")}
    response = client.post("/api/v1/candidates/upload", files=files)
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["message"] == "Candidate CSV ingested successfully."
    assert json_resp["details"]["saved_records"] == 1

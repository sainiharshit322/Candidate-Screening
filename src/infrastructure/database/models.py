import json
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, Text, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from src.config import settings

Base = declarative_base()

class JobDescriptionModel(Base):
    __tablename__ = "job_descriptions"

    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    required_skills = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

class CandidateModel(Base):
    __tablename__ = "candidates"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)

    college = Column(String(255), nullable=True)
    branch = Column(String(100), nullable=True)
    cgpa = Column(Float, nullable=True)
    best_ai_project = Column(Text, nullable=True)
    research_work = Column(Text, nullable=True)
    github_handle = Column(String(100), nullable=True)
    resume_url = Column(Text, nullable=True)
    resume_text = Column(Text, nullable=True)
    github_score = Column(Float, default=0.0)
    github_details = Column(JSON, nullable=True, default=dict)
    resume_score = Column(Float, default=0.0)
    aptitude_score = Column(Float, nullable=True)
    coding_score = Column(Float, nullable=True)
    composite_score = Column(Float, default=0.0, index=True)
    ai_reasoning = Column(JSON, nullable=True, default=dict)
    status = Column(String(50), default="UPLOADED", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class InterviewModel(Base):
    __tablename__ = "interviews"

    id = Column(String(36), primary_key=True)
    candidate_id = Column(String(36), nullable=False)
    google_event_id = Column(String(255), nullable=False)
    google_meet_url = Column(Text, nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

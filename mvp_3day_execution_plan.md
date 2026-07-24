# 3-Day MVP Execution Plan & Pragmatic Architecture

**Project Name:** AI Candidate Screening Platform (*myNachiketa*)  
**Target Delivery Window:** 3 Days (72 Hours)  
**Strategy:** Lean Core Workflow + Modularity for Future Scaling  

---

## 1. Scope De-Risking Matrix (MVP vs. Future Upgrades)

To meet the strict 3-day deadline, non-essential complexity is stripped away while preserving clean interface abstractions (**Dependency Injection**) so advanced capabilities can be plugged in seamlessly post-launch.

| Functional Area | Cut / Simplified for 3-Day MVP | Future Upgrade Expansion (Extension Seams) |
| :--- | :--- | :--- |
| **Authentication** | Environment-configured Admin Session / API Key | OAuth 2.0 Google SSO + Multi-tenant RBAC |
| **Database & Vector** | Lightweight PostgreSQL / SQLite + SQLAlchemy | `pgvector` Semantic Embedding DB |
| **Task Engine** | FastAPI `BackgroundTasks` / ThreadPoolExecutor | Celery / RabbitMQ Distributed Cluster |
| **Resume Parsing** | Direct PyMuPDF text extraction stream | Dual-pass Tesseract OCR pipeline |
| **GitHub Engine** | GitHub REST API (Top 3 repos, stars, languages) | GraphQL AST Code Parser & Commitment Heatmaps |
| **AI Evaluation** | Single Gemini 1.5 Flash API with JSON mode | Multi-model fallback chain (Claude + Local Ollama) |
| **Calendar Sync** | Google Calendar API Service Account + Meet Link | Multi-interviewer `freeBusy` conflict resolver |
| **UI Dashboard** | Single-Page React / Next.js Dashboard or Streamlit | Real-time WebSocket multi-tab Recruiter Analytics |

---

## 2. Pragmatic MVP Architecture

The system uses a **Pragmatic Monolith** architecture with clean service interfaces. Business logic depends on abstractions (Interfaces), making future upgrades trivial.

```
                         +-----------------------------------+
                         | Recruiter Web Dashboard (React)   |
                         +-----------------+-----------------+
                                           | HTTP REST
                                           v
                         +-----------------------------------+
                         | FastAPI Application Gateway       |
                         +-----------------+-----------------+
                                           |
         +---------------------------------+---------------------------------+
         |                                 |                                 |
         v                                 v                                 v
+------------------+             +------------------+             +------------------+
| IResumeParser    |             | IGitHubAnalyzer  |             | IEvaluationEngine|
| -> PyMuPDF       |             | -> GitHub REST   |             | -> Gemini LLM    |
+------------------+             +------------------+             +------------------+
         |                                 |                                 |
         +---------------------------------+---------------------------------+
                                           |
                                           v
                         +-----------------------------------+
                         | ICalendarService & IEmailService  |
                         | -> Google Meet & SMTP Dispatch    |
                         +-----------------+-----------------+
                                           |
                                           v
                         +-----------------------------------+
                         | PostgreSQL / SQLite Database      |
                         +-----------------------------------+
```

---

## 3. Hour-by-Hour 3-Day Execution Roadmap

```
Day 1: Foundation & Data Processing (Hours 0 - 24)
├── H00 - H04: Setup FastAPI project structure & SQLAlchemy DB models
├── H04 - H08: Build CSV Upload & Parsing Endpoints (Candidate Intake)
├── H08 - H14: Implement PyMuPDF Resume Downloader & Text Extractor
└── H14 - H24: Build GitHub REST API Client (Repos, Stars, Languages)

Day 2: AI Scoring & Automation Engine (Hours 25 - 48)
├── H25 - H32: Implement Gemini LLM Structured Evaluation Engine
├── H32 - H38: Implement Composite Score Calculator & Leaderboard API
├── H38 - H44: Build SMTP Email Dispatcher for Test Invitations
└── H44 - H48: Build Google Calendar API & Meet Link Generation Service

Day 3: UI Dashboard, Integration & Deployment (Hours 49 - 72)
├── H49 - H60: Build Recruiter Dashboard UI (Upload, Funnel, Candidate Drawer)
├── H60 - H66: End-to-End Workflow Testing & Data Fixes
└── H66 - H72: Public Cloud Hosting (Render / Vercel / Railway) & Demo Recording
```

---

## 4. Code Architecture Seams (Pluggable Design for Upgrades)

To ensure future upgrades do not break existing code, all external services use **Interface Contracts** (Abstract Base Classes).

### Example: LLM Provider Interface
```python
# Future-proof interface: Can swap Gemini for OpenAI/Claude without altering application logic
from abc import ABC, abstractmethod
from typing import Dict, Any

class IEvaluationEngine(ABC):
    @abstractmethod
    async def evaluate_candidate(self, resume_text: str, github_data: Dict[str, Any], jd_text: str) -> Dict[str, Any]:
        pass

class GeminiEvaluationEngine(IEvaluationEngine):
    async def evaluate_candidate(self, resume_text: str, github_data: Dict[str, Any], jd_text: str) -> Dict[str, Any]:
        # Fast Gemini 1.5 Flash implementation for 3-Day MVP
        ...
```

---

## 5. Lean Database Schema (SQLAlchemy MVP)

```sql
CREATE TABLE candidates (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    college VARCHAR(255),
    branch VARCHAR(100),
    cgpa NUMERIC(3,2),
    best_ai_project TEXT,
    research_work TEXT,
    github_handle VARCHAR(100),
    resume_url TEXT NOT NULL,
    resume_text TEXT,
    github_score NUMERIC(5,2) DEFAULT 0,
    resume_score NUMERIC(5,2) DEFAULT 0,
    aptitude_score NUMERIC(5,2) DEFAULT 0,
    coding_score NUMERIC(5,2) DEFAULT 0,
    composite_score NUMERIC(5,2) DEFAULT 0,
    ai_reasoning JSONB,
    status VARCHAR(50) DEFAULT 'UPLOADED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE interviews (
    id VARCHAR(36) PRIMARY KEY,
    candidate_id VARCHAR(36) REFERENCES candidates(id),
    google_event_id VARCHAR(255),
    google_meet_url TEXT NOT NULL,
    scheduled_time TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 6. End-to-End 3-Day Verification Plan

1. **Upload Test**: Post sample candidate CSV via API/UI $\rightarrow$ verify DB population.
2. **AI & GitHub Test**: Trigger async batch processing $\rightarrow$ verify resume text extraction, GitHub REST fetch, and Gemini score generation.
3. **Shortlist & Email Test**: Upload test results CSV $\rightarrow$ verify top candidates advance to `SHORTLISTED_L2` and receive email invite.
4. **Google Calendar & Meet Test**: Trigger interview scheduler $\rightarrow$ verify Google Calendar event created with active `https://meet.google.com/...` link.

# User Stories Backlog

**System Name:** AI Candidate Screening Platform (*myNachiketa*)  
**Author:** Principal Software Architect  
**Format:** Standard Agile User Stories (`As a [role], I want to [action] so that [benefit]`)  

---

## Epic 1: Authentication & Access Control

### Story 1.1: Recruiter Authentication & JWT Issuance
> **User Story:** "As a recruiter, I want to securely log into the platform using my credentials so that I can access candidate data and recruitment workflows."

**Acceptance Criteria:**
* User can submit email and password via login interface.
* System verifies credentials using `Argon2id` / `bcrypt` hash comparison.
* Upon successful authentication, system issues a 15-minute JWT Access Token (RS256 signed) and a 7-day HttpOnly Refresh Cookie.
* Failed login attempts return generic `401 Unauthorized` message to prevent email enumeration.
* Redis rate limiter blocks login attempts exceeding 5 failures per minute per IP address.

---

### Story 1.2: OAuth 2.0 Google SSO Integration
> **User Story:** "As a recruiter, I want to sign in using my company Google Workspace account so that I don't have to manage separate passwords."

**Acceptance Criteria:**
* Login UI provides "Sign in with Google" OAuth 2.0 button.
* System validates Google ID Token and extracts user profile info (`email`, `name`).
* Automatically provisions a new user record if email domain matches authorized organization domains.
* Securely stores Google Refresh Token in encrypted KMS vault for downstream Calendar API access.

---

### Story 1.3: Role-Based Access Control (RBAC) & Token Refresh
> **User Story:** "As a recruiter, I want my active session to refresh automatically without interrupting my work, while keeping administrative functions restricted to Admins."

**Acceptance Criteria:**
* API Gateway enforces RBAC roles (`ADMIN`, `RECRUITER`, `INTERVIEWER`).
* Client application automatically invokes `/api/v1/auth/refresh` when Access Token is near expiry.
* Unauthenticated requests to protected endpoints return `401 Unauthorized`.
* Accessing Admin-only endpoints with a `RECRUITER` token returns `403 Forbidden`.

---

## Epic 2: Candidate Intake & CSV Processing

### Story 2.1: CSV Dataset Upload
> **User Story:** "As a recruiter, I want to upload a candidate CSV dataset so that candidate records are automatically parsed and ingested into the hiring pipeline."

**Acceptance Criteria:**
* Recruiter can drag and drop a CSV file into the upload dropzone.
* System validates required headers: `Name`, `Email`, `College`, `Branch`, `CGPA`, `Best AI Project`, `Research Work`, `GitHub Profile`, `Resume Link`.
* Rejects non-CSV files or files larger than 25MB with clear validation errors.
* Returns an asynchronous `batch_id` with `202 Accepted` response.

---

### Story 2.2: Duplicate Detection & Data Sanitization
> **User Story:** "As a system operator, I want candidate entries deduplicated by email address so that duplicate applications do not clutter the pipeline."

**Acceptance Criteria:**
* System checks existing database records for matching `Email` addresses.
* If a duplicate email is found, system updates the existing profile with the latest CSV attributes rather than creating a duplicate row.
* Trims whitespace and normalizes email strings to lowercase.
* Validates CGPA range ($0.00 \le \text{CGPA} \le 10.00$) and flags out-of-bounds values.

---

### Story 2.3: Real-Time Intake Progress & Batch Error Reporting
> **User Story:** "As a recruiter, I want to view real-time upload progress and download an error report if any rows fail parsing."

**Acceptance Criteria:**
* UI displays progress bar indicating percentage of processed CSV rows.
* If specific rows contain invalid formatting (missing mandatory fields), system continues processing valid rows.
* Generates a downloadable `parsing_errors.csv` detailing line numbers and exact failure reasons.
* Emits a WebSocket event when batch ingestion completes.

---

## Epic 3: Resume Processing & OCR Pipeline

### Story 3.1: Asynchronous PDF Resume Ingestion
> **User Story:** "As a system, I want to asynchronously download candidate PDF resumes from provided links so that candidate resumes are ready for text extraction."

**Acceptance Criteria:**
* Worker consumes `candidate.process.resume` task from Redis queue.
* Downloads PDF resume with a strict 15-second HTTP timeout and 10MB maximum file size limit.
* Validates PDF file header magic bytes (`%PDF-`).
* Stores raw PDF file in Cloud Storage (`S3 / GCS`) under `resumes/{candidate_id}.pdf`.

---

### Story 3.2: SSRF Proxy Protection for Resume Links
> **User Story:** "As a security engineer, I want all resume URLs sanitized via an SSRF proxy so that malicious links cannot access internal cloud infrastructure metadata."

**Acceptance Criteria:**
* Outbound HTTP client pre-resolves domain names to IP addresses.
* Blocks requests resolving to private or internal IP blocks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.169.254`).
* Rejects non-HTTP/HTTPS protocols (`file://`, `ftp://`, `gopher://`).
* If URL fails validation, marks candidate status as `RESUME_FETCH_FAILED`.

---

### Story 3.3: Dual PDF Text Extraction & OCR Fallback
> **User Story:** "As an AI engineer, I want text extracted from resumes using OCR when standard PDF text parsing fails, ensuring complete data ingestion."

**Acceptance Criteria:**
* Primary pass extracts text using high-performance PDF parser (`pdfplumber`).
* If extracted text contains $< 50$ words (scanned image PDF), triggers secondary OCR pipeline (`tesseract`).
* Sanitizes extracted text by removing control characters and HTML tags.
* Persists cleaned text string in `candidate_resumes` database table.

---

## Epic 4: GitHub Profile Analyzer

### Story 4.1: GitHub GraphQL Metadata Ingestion
> **User Story:** "As an AI evaluator, I want candidate GitHub profile data fetched via GraphQL so that technical background can be analyzed in a single request."

**Acceptance Criteria:**
* Queries GitHub GraphQL API for candidate handle extracted from CSV.
* Fetches profile bio, total stars across public repos, pinned repositories, and commit contribution counts over the last 12 months.
* Caches raw GitHub JSON payload in PostgreSQL `github_profiles` table.
* Respects GitHub rate limits using token rotation and exponential backoff retry.

---

### Story 4.2: Fork Filtering & Original Repository Analysis
> **User Story:** "As a recruiter, I want forked repositories excluded from GitHub evaluations so that candidates are assessed solely on original technical work."

**Acceptance Criteria:**
* Filters out all repositories flagged with `isFork: true`.
* Inspects `README.md` text content, directory tree depth, and language breakdown of top 3 original repositories.
* Identifies presence of test directories (`/tests`, `/spec`) and containerization configs (`Dockerfile`, `docker-compose.yml`).

---

### Story 4.3: Engineering Effort Index (EEI) Calculation
> **User Story:** "As a hiring manager, I want a normalized Engineering Effort Index calculated for each candidate's GitHub profile so that code quality can be objectively quantified."

**Acceptance Criteria:**
* Computes EEI score ($0 - 100$) derived from star count, commit velocity, original repository code size, and test coverage indicators.
* Handles missing or private GitHub profiles gracefully by assigning neutral flag `NO_GITHUB_DATA` without crashing task queue.
* Exposes calculated EEI score via candidate summary API.

---

## Epic 5: LLM Evaluation Engine

### Story 5.1: XML Context Isolation & Prompt Injection Defense
> **User Story:** "As a system security architect, I want candidate resume text isolated within XML delimiters in LLM prompts so that prompt injection attempts are rendered ineffective."

**Acceptance Criteria:**
* System prompt wraps candidate resume text inside `<resume_context>` tags.
* System instructions explicitly direct LLM to treat content within delimiters strictly as data, ignoring instructions embedded within data.
* Regex pre-processor strips known injection patterns (e.g., *"Ignore previous instructions"*).

---

### Story 5.2: Structured JSON LLM Scoring Output
> **User Story:** "As an application developer, I want the LLM to output evaluation scores in strict JSON format so that results can be validated and stored reliably."

**Acceptance Criteria:**
* Configures LLM API with strict JSON Schema output mode (`response_format: json_object`).
* Schema enforces numeric scores ($0-100$) for `relevance_score`, `technical_depth_score`, and `project_complexity_score`.
* Schema enforces string array fields for `strengths`, `concerns`, and `jd_alignment_summary`.
* Validates JSON output against JSON schema; retries up to 3 times on schema mismatch.

---

### Story 5.3: Multi-Model Resilience Fallback Chain
> **User Story:** "As a platform operator, I want the evaluation engine to fallback to secondary LLM providers when the primary LLM API experiences rate limits or outages."

**Acceptance Criteria:**
* Primary attempt routes to `Gemini 1.5 Flash API`.
* If primary call fails (HTTP 429 / 5xx / Timeout after 10s), falls back to `Claude 3.5 Haiku API`.
* If secondary call fails, routes task to fallback `Local Ollama / Llama 3` worker.
* Logs model provider used in `candidate_evaluations` record for auditability.

---

## Epic 6: Candidate Ranking & Shortlisting State Machine

### Story 6.1: Composite Score Calculation
> **User Story:** "As a recruiter, I want candidate composite scores calculated automatically across AI evaluations and test scores so that candidates are ranked fairly."

**Acceptance Criteria:**
* System computes Composite Score using weighted formula:
  $$\text{Composite} = 0.35 S_{\text{Resume}} + 0.25 S_{\text{GitHub}} + 0.20 S_{\text{Aptitude}} + 0.20 S_{\text{Coding}}$$
* Handles missing test scores by calculating provisional score based on available weights.
* Updates `candidate_evaluations.composite_score` field in database.

---

### Story 6.2: Dynamic Leaderboard & Tie-Breaking
> **User Story:** "As a recruiter, I want a sorted leaderboard of candidates so that I can view the top performers instantly."

**Acceptance Criteria:**
* Endpoint `GET /api/v1/candidates` returns candidate list ordered by `composite_score DESC`.
* Implements tie-breaking logic: equal composite scores are ordered by Coding score, then Resume score, then CGPA.
* Returns paginated response ($20$ candidates per page) with response latency $< 150$ms.

---

### Story 6.3: Automated Shortlisting State Machine Transitions
> **User Story:** "As a hiring manager, I want candidates automatically transitioned through hiring pipeline states based on score thresholds."

**Acceptance Criteria:**
* Candidates scoring above configured threshold $\tau_1$ transition state from `EVALUATED` to `SHORTLISTED_L1`.
* Upon test result upload, candidates scoring above threshold $\tau_2$ transition state to `SHORTLISTED_L2`.
* State transitions recorded in `audit_logs` table for workflow compliance.

---

## Epic 7: Email Automation Engine

### Story 7.1: Custom Recruiter SMTP Configuration
> **User Story:** "As a recruiter, I want to configure my company's SMTP settings so that automated emails originate from my organization's domain."

**Acceptance Criteria:**
* Settings UI allows input of SMTP Host, Port, Username, Password, and Encryption Type (TLS/SSL).
* Securely encrypts SMTP password using AES-256 before storing in `users.smtp_credentials`.
* "Send Test Email" button validates SMTP connection parameters.

---

### Story 7.2: Async Test Link Email Dispatch
> **User Story:** "As a candidate, I want to receive an email containing my unique online test link once I am shortlisted."

**Acceptance Criteria:**
* Worker consumes `notification.send_test_link` task for candidates in `SHORTLISTED_L1` state.
* Generates email body rendering dynamic HTML template with candidate name and test link URL.
* Sends email asynchronously via Celery worker pool without blocking recruiter UI.
* Transitions candidate state to `TEST_SENT`.

---

### Story 7.3: Delivery Logging & Bounce Handling
> **User Story:** "As a recruiter, I want email delivery failures tracked so that I know if a shortlisted candidate did not receive their test link."

**Acceptance Criteria:**
* Records every email dispatch attempt in `email_logs` table (`SENT`, `FAILED`).
* Captures SMTP error codes and bounce reasons if dispatch fails.
* Flag failed emails in Recruiter Dashboard with "Retry Email" quick action.

---

## Epic 8: Automated Interview Scheduling

### Story 8.1: Google OAuth Calendar Integration
> **User Story:** "As a recruiter, I want to connect my Google Calendar account so that interview slots can be scheduled automatically based on my real-time availability."

**Acceptance Criteria:**
* Recruiter authorizes platform via Google OAuth 2.0 with scope `https://www.googleapis.com/auth/calendar`.
* Platform securely stores encrypted OAuth Access and Refresh Tokens.
* Automatically refreshes expired tokens in background.

---

### Story 8.2: Conflict-Free Slot Finder
> **User Story:** "As a system, I want to query the recruiter's Google Calendar `freeBusy` endpoint so that interviews are scheduled only during free working hours."

**Acceptance Criteria:**
* Queries Google Calendar `freeBusy` API for recruiter's primary calendar over requested date range.
* Filters out non-working hours (e.g., outside 9 AM - 5 PM) and existing event conflicts.
* Identifies next available 30-minute open window for each shortlisted candidate.

---

### Story 8.3: Event Creation & Google Meet Link Generation
> **User Story:** "As a candidate, I want an interview invite sent to my calendar with an automatically generated Google Meet link."

**Acceptance Criteria:**
* Creates a Google Calendar Event containing Candidate Name, Job Title, and Description.
* Enables `conferenceDataVersion: 1` parameter to generate a valid Google Meet video link.
* Sends calendar invite to both Candidate Email and Recruiter Email.
* Saves `google_event_id` and `google_meet_url` in `interviews` database table.
* Updates candidate pipeline status to `INTERVIEW_SCHEDULED`.

---

## Epic 9: Recruiter Dashboard UI

### Story 9.1: Interactive Candidate Pipeline Funnel
> **User Story:** "As a recruiter, I want a visual dashboard summary of candidate pipeline stages so that I can monitor recruitment progress at a glance."

**Acceptance Criteria:**
* Displays key metrics tiles: Total Uploaded, AI Shortlisted (L1), Test Completed, Final Shortlist (L2), Scheduled.
* Pipeline funnel graph updates dynamically as candidates progress through states.
* Built using modern Vanilla CSS / Tailwind styling with responsive mobile/desktop layouts.

---

### Story 9.2: Test Results CSV Upload & Matching
> **User Story:** "As a recruiter, I want to upload a test results CSV file so that candidate aptitude and coding scores update automatically."

**Acceptance Criteria:**
* Upload modal accepts CSV file containing fields `Email`, `test_la`, `test_code`.
* Joins test scores to existing candidate records matching on `Email`.
* Re-calculates composite scores and triggers `SHORTLISTED_L2` state transitions automatically.
* Displays summary of matched records vs unmatched email rows.

---

### Story 9.3: Candidate Detail Drawer & Explainable AI View
> **User Story:** "As a recruiter, I want to click any candidate row to view their full resume, GitHub insights, and AI scoring breakdown."

**Acceptance Criteria:**
* Clicking candidate table row slides open a detailed drawer.
* Displays tabbed views: Overview, Resume Text, GitHub Repos, AI Reasoning, Interview Details.
* AI Reasoning tab renders Explainable AI strengths, concerns, and matching quotes from resume.

---

## Epic 10: Infrastructure, Containerization & CI/CD Deployment

### Story 10.1: OCI Containerization & Multi-Stage Builds
> **User Story:** "As a DevOps engineer, I want application components containerized into lightweight Docker images so that deployments are consistent across environments."

**Acceptance Criteria:**
* Defines multi-stage `Dockerfile` for API app and background worker services.
* Final production container image size $< 250$MB using Alpine / Slim base images.
* Non-root user execution (`USER appuser`) inside container for security compliance.

---

### Story 10.2: Database Migration & Health Probes
> **User Story:** "As a system reliability engineer, I want automated database migrations and health check probes so that zero-downtime updates are guaranteed."

**Acceptance Criteria:**
* Container startup executes Alembic / Flyway database migrations safely.
* `/healthz` endpoint returns `200 OK` for liveness probe.
* `/readyz` endpoint validates PostgreSQL DB connection and Redis ping before receiving traffic.

---

### Story 10.3: Automated CI/CD Pipeline Deployment
> **User Story:** "As a software engineer, I want code pushed to the main branch automatically tested, scanned, built, and deployed to production."

**Acceptance Criteria:**
* GitHub Actions workflow triggers on PR merge to `main`.
* Stage 1: Runs Linter and Unit Test suite.
* Stage 2: Executes Security Static Analysis (Semgrep) and Vulnerability Scanning (Trivy).
* Stage 3: Builds OCI image and pushes to Container Registry.
* Stage 4: Performs zero-downtime rolling update on ECS / Kubernetes cluster.

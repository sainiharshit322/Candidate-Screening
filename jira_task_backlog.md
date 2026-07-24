# Jira Engineering Task Backlog
**System Name:** AI Candidate Screening Platform (*myNachiketa*)  
**Author:** Principal Software Architect  
**Purpose:** Actionable Engineering Execution Tickets for Sprint Planning  

---

## Phase 1: Core Foundation, Database & Auth (Tasks 001 - 005)

### TASK-001: Implement Core PostgreSQL Database Migration & DDL
* **Priority:** Critical
* **Estimate:** 3 hours
* **Dependencies:** None
* **Files Affected:**
  * `src/infrastructure/persistence/migrations/env.py`
  * `src/infrastructure/persistence/migrations/versions/001_initial_schema.py`
  * `src/infrastructure/persistence/models.py`
* **Acceptance Criteria:**
  * Define SQLAlchemy models and Alembic migration for `users`, `job_descriptions`, `candidates`, `github_profiles`, `candidate_evaluations`, and `interviews` tables.
  * Include `pgvector` extension and indexing (`idx_candidates_email`, `idx_evaluations_composite`).
* **Unit Tests:** Migration upgrade/downgrade test against test database.
* **Integration Tests:** Database connection pool initialization test.

---

### TASK-002: Implement User Authentication Service & Password Hashing
* **Priority:** High
* **Estimate:** 4 hours
* **Dependencies:** TASK-001
* **Files Affected:**
  * `src/domain/entities/user.py`
  * `src/infrastructure/security/password_hasher.py`
  * `src/application/use_cases/authenticate_user.py`
* **Acceptance Criteria:**
  * Implement password hashing using `Argon2id` / `bcrypt` with salt generation.
  * Verify user credentials against `users` table.
* **Unit Tests:** Password hash generation and verification tests.
* **Integration Tests:** Database user lookup and verification integration test.

---

### TASK-003: Implement JWT Access Token & Refresh Cookie Service
* **Priority:** High
* **Estimate:** 3 hours
* **Dependencies:** TASK-002
* **Files Affected:**
  * `src/infrastructure/security/jwt_service.py`
  * `src/presentation/api/middlewares/auth_middleware.py`
* **Acceptance Criteria:**
  * Generate RS256-signed JWT Access Tokens (15-min TTL) and Refresh Tokens (7-day TTL).
  * Build FastAPI HTTP Bearer authentication middleware enforcing JWT verification.
* **Unit Tests:** JWT token encoding, decoding, and expiration validation tests.
* **Integration Tests:** Protected API route middleware HTTP test (`401 Unauthorized` for invalid token).

---

### TASK-004: Implement Google OAuth 2.0 Recruiter Login Handler
* **Priority:** Medium
* **Estimate:** 5 hours
* **Dependencies:** TASK-003
* **Files Affected:**
  * `src/infrastructure/external_services/google_oauth_adapter.py`
  * `src/presentation/api/v1/auth_router.py`
* **Acceptance Criteria:**
  * Process Google OAuth callback code, exchange for ID token and Refresh Token.
  * Provision user profile and store encrypted refresh token in database.
* **Unit Tests:** Google ID Token decoder and claim validation unit test.
* **Integration Tests:** Mocked Google OAuth token exchange flow test.

---

### TASK-005: Implement Redis Rate Limiting Guard Middleware
* **Priority:** Medium
* **Estimate:** 3 hours
* **Dependencies:** TASK-003
* **Files Affected:**
  * `src/infrastructure/security/rate_limiter.py`
  * `src/presentation/api/middlewares/rate_limit_middleware.py`
* **Acceptance Criteria:**
  * Implement Redis sliding window rate limiter (5 login attempts/min, 100 API requests/min).
  * Return `429 Too Many Requests` with `X-RateLimit-Reset` header upon limit exceedance.
* **Unit Tests:** Sliding window mathematical algorithm unit test.
* **Integration Tests:** Redis connection failure fallback test (fail open safely).

---

## Phase 2: Data Ingestion & Security Proxy (Tasks 006 - 010)

### TASK-006: Implement Job Description CRUD Domain Service
* **Priority:** High
* **Estimate:** 3 hours
* **Dependencies:** TASK-001
* **Files Affected:**
  * `src/domain/entities/job_description.py`
  * `src/application/use_cases/create_job_description.py`
  * `src/presentation/api/v1/jobs_router.py`
* **Acceptance Criteria:**
  * CRUD endpoints for Job Descriptions (`POST /api/v1/jobs`, `GET /api/v1/jobs/:id`).
  * Validate required skills array and non-empty text description.
* **Unit Tests:** Job Description entity validation rules test.
* **Integration Tests:** REST API endpoint POST/GET integration test.

---

### TASK-007: Implement CSV Candidate Dataset Parser & Schema Validator
* **Priority:** High
* **Estimate:** 5 hours
* **Dependencies:** TASK-006
* **Files Affected:**
  * `src/application/use_cases/ingest_candidate_csv.py`
  * `src/infrastructure/parsers/csv_parser.py`
* **Acceptance Criteria:**
  * Parse uploaded CSV file using `pandas` / `polars`.
  * Validate required CSV headers (`Name`, `Email`, `College`, `Branch`, `CGPA`, `Best AI Project`, `Research Work`, `GitHub Profile`, `Resume Link`).
* **Unit Tests:** CSV header validation and missing column handling test.
* **Integration Tests:** Upload sample 500-row CSV file test.

---

### TASK-008: Implement Candidate Email Deduplication Engine
* **Priority:** High
* **Estimate:** 3 hours
* **Dependencies:** TASK-007
* **Files Affected:**
  * `src/infrastructure/persistence/postgres_candidate_repo.py`
  * `src/domain/services/candidate_deduplicator.py`
* **Acceptance Criteria:**
  * Check existing candidate records by lowercase normalized email.
  * Perform batch `UPSERT` on candidate tables updating existing fields.
* **Unit Tests:** Email normalization and string comparison test.
* **Integration Tests:** Duplicate candidate CSV upload test (assert row count unchanged).

---

### TASK-009: Implement SSRF Prevention Network Proxy Guard
* **Priority:** Critical
* **Estimate:** 4 hours
* **Dependencies:** None
* **Files Affected:**
  * `src/infrastructure/security/ssrf_proxy.py`
* **Acceptance Criteria:**
  * Pre-resolve domain names via DNS before HTTP request.
  * Block IPs matching private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.169.254`).
* **Unit Tests:** Test against internal IP list and AWS metadata endpoints.
* **Integration Tests:** Outbound HTTP request interception test.

---

### TASK-010: Implement Candidate Intake Async Task Publisher
* **Priority:** High
* **Estimate:** 3 hours
* **Dependencies:** TASK-007, TASK-009
* **Files Affected:**
  * `src/infrastructure/messaging/redis_publisher.py`
  * `src/presentation/api/v1/candidates_router.py`
* **Acceptance Criteria:**
  * Endpoint `POST /api/v1/candidates/upload` enqueues batch tasks into Redis.
  * Return `202 Accepted` response with `batch_id` payload immediately.
* **Unit Tests:** Redis task message serialization test.
* **Integration Tests:** HTTP POST upload endpoint response test.

---

## Phase 3: Async Workers & Resume OCR Pipeline (Tasks 011 - 015)

### TASK-011: Setup Celery / BullMQ Worker Process Infrastructure
* **Priority:** High
* **Estimate:** 4 hours
* **Dependencies:** TASK-010
* **Files Affected:**
  * `src/infrastructure/messaging/celery_app.py`
  * `src/infrastructure/messaging/worker_tasks.py`
* **Acceptance Criteria:**
  * Initialize task queue worker process connecting to Redis broker.
  * Configure concurrency pool, task prefetched counts, and dead-letter queues (DLQ).
* **Unit Tests:** Worker task handler function wrapper test.
* **Integration Tests:** Redis queue message consumption integration test.

---

### TASK-012: Implement Async Resume Downloader & S3 Storage Adapter
* **Priority:** High
* **Estimate:** 4 hours
* **Dependencies:** TASK-009, TASK-011
* **Files Affected:**
  * `src/infrastructure/external_services/s3_storage_adapter.py`
  * `src/domain/services/resume_fetcher.py`
* **Acceptance Criteria:**
  * Download PDF resume via SSRF proxy with 15s timeout limit.
  * Upload raw PDF stream to AWS S3 bucket (`resumes/{candidate_id}.pdf`).
* **Unit Tests:** S3 key name generator test.
* **Integration Tests:** Mocked S3 client upload integration test.

---

### TASK-013: Implement PyMuPDF Text Extractor Engine
* **Priority:** High
* **Estimate:** 4 hours
* **Dependencies:** TASK-012
* **Files Affected:**
  * `src/infrastructure/parsers/pdf_text_parser.py`
* **Acceptance Criteria:**
  * Extract plain text from PDF bytes using `pdfplumber` / `pypdf`.
  * Return word count and extracted text payload string.
* **Unit Tests:** Multi-page text PDF extraction unit test.
* **Integration Tests:** PDF file read and text parse integration test.

---

### TASK-014: Implement Tesseract OCR Fallback Pipeline
* **Priority:** Medium
* **Estimate:** 5 hours
* **Dependencies:** TASK-013
* **Files Affected:**
  * `src/infrastructure/parsers/ocr_parser.py`
* **Acceptance Criteria:**
  * Fallback to `pytesseract` + `pdf2image` if extracted text count $< 50$ words.
  * Convert PDF pages to PNG images and extract text via OCR engine.
* **Unit Tests:** Image pre-processing unit test.
* **Integration Tests:** Scanned image PDF OCR text extraction test.

---

### TASK-015: Implement Resume Text Sanitizer & Control Character Cleaner
* **Priority:** Medium
* **Estimate:** 2 hours
* **Dependencies:** TASK-013
* **Files Affected:**
  * `src/domain/services/text_sanitizer.py`
* **Acceptance Criteria:**
  * Strip null bytes, unprintable control characters, and HTML tags from parsed text.
  * Persist sanitized text in `candidate_resumes` database table.
* **Unit Tests:** Regex control character replacement test.
* **Integration Tests:** Database save and retrieve cleaned resume text test.

---

## Phase 4: GitHub Profile Intelligence (Tasks 016 - 020)

### TASK-016: Implement GitHub GraphQL Client Adapter
* **Priority:** High
* **Estimate:** 5 hours
* **Dependencies:** TASK-001
* **Files Affected:**
  * `src/infrastructure/external_services/github_graphql_adapter.py`
  * `src/domain/interfaces/github_client.py`
* **Acceptance Criteria:**
  * Query GitHub GraphQL API v4 for user bio, star counts, pinned repos, and commit stats.
  * Handle GitHub API authentication tokens via environment configuration.
* **Unit Tests:** GraphQL query payload builder test.
* **Integration Tests:** Mocked GraphQL server query response test.

---

### TASK-017: Implement GitHub Fork Filtering Service
* **Priority:** Medium
* **Estimate:** 3 hours
* **Dependencies:** TASK-016
* **Files Affected:**
  * `src/domain/services/github_fork_filter.py`
* **Acceptance Criteria:**
  * Filter out repositories flagged with `isFork: true`.
  * Identify top 3 non-fork original repositories by star count and recency.
* **Unit Tests:** Repository array filtering logic test.
* **Integration Tests:** GitHub GraphQL repository payload parser test.

---

### TASK-018: Implement Engineering Effort Index (EEI) Calculator
* **Priority:** High
* **Estimate:** 4 hours
* **Dependencies:** TASK-017
* **Files Affected:**
  * `src/domain/services/eei_calculator.py`
* **Acceptance Criteria:**
  * Calculate EEI score ($0-100$) using commit velocity, repository sizes, and language breakdown.
  * Award bonus score points for detected test directories (`/tests`).
* **Unit Tests:** EEI scoring mathematical formula unit test.
* **Integration Tests:** Candidate profile EEI evaluation end-to-end test.

---

### TASK-019: Implement GitHub API Rate Limit & Retry Handler
* **Priority:** Medium
* **Estimate:** 3 hours
* **Dependencies:** TASK-016
* **Files Affected:**
  * `src/infrastructure/external_services/github_rate_limiter.py`
* **Acceptance Criteria:**
  * Intercept HTTP 429 rate limit responses from GitHub API.
  * Pause task worker and retry using exponential backoff with full jitter.
* **Unit Tests:** Backoff delay calculation unit test.
* **Integration Tests:** Simulated 429 response rate-limit retry test.

---

### TASK-020: Implement Missing GitHub Handle Graceful Fallback
* **Priority:** Medium
* **Estimate:** 2 hours
* **Dependencies:** TASK-018
* **Files Affected:**
  * `src/domain/services/github_fallback_handler.py`
* **Acceptance Criteria:**
  * If GitHub profile URL is missing, invalid, or 404, assign `0` GitHub score and flag `NO_GITHUB_DATA`.
  * Ensure overall candidate evaluation pipeline continues without error.
* **Unit Tests:** Missing handle exception handling unit test.
* **Integration Tests:** Pipeline run with invalid GitHub URL test.

---

## Phase 5: AI Scoring Engine & Prompt Guardrails (Tasks 021 - 025)

### TASK-021: Implement XML Prompt Injection Delimiter Guardrail
* **Priority:** Critical
* **Estimate:** 3 hours
* **Dependencies:** None
* **Files Affected:**
  * `src/infrastructure/security/prompt_sanitizer.py`
* **Acceptance Criteria:**
  * Wrap candidate context inside `<candidate_context>` XML tags.
  * System prompt instructs LLM to treat content strictly as untrusted data.
* **Unit Tests:** Adversarial prompt override string sanitizer test.
* **Integration Tests:** LLM prompt execution with injection attack payload test.

---

### TASK-022: Implement Gemini LLM API Adapter & JSON Schema Enforcement
* **Priority:** Critical
* **Estimate:** 5 hours
* **Dependencies:** TASK-021
* **Files Affected:**
  * `src/infrastructure/external_services/gemini_llm_adapter.py`
  * `src/domain/interfaces/llm_provider.py`
* **Acceptance Criteria:**
  * Execute evaluation prompt against Gemini 1.5 Flash API with `response_format: json_object`.
  * Enforce strict JSON schema for sub-scores, strengths, concerns, and JD summary.
* **Unit Tests:** Prompt string template formatter unit test.
* **Integration Tests:** Mocked Gemini LLM JSON response test.

---

### TASK-023: Implement Multi-Model LLM Fallback Chain
* **Priority:** High
* **Estimate:** 4 hours
* **Dependencies:** TASK-022
* **Files Affected:**
  * `src/infrastructure/external_services/llm_fallback_chain.py`
* **Acceptance Criteria:**
  * Fallback to Claude 3.5 Haiku if Gemini API fails or times out ($> 10$s).
  * Fallback to local Ollama worker if secondary LLM fails.
* **Unit Tests:** Multi-model fallback switch unit test.
* **Integration Tests:** Primary LLM timeout simulation fallback test.

---

### TASK-024: Implement LLM JSON Output Schema Validator & Retry Loop
* **Priority:** High
* **Estimate:** 3 hours
* **Dependencies:** TASK-022
* **Files Affected:**
  * `src/domain/services/llm_output_validator.py`
* **Acceptance Criteria:**
  * Validate returned JSON string against Pydantic schema model.
  * Retry up to 3 times with lower temperature if JSON parsing fails.
* **Unit Tests:** Pydantic JSON schema validator unit test.
* **Integration Tests:** Invalid JSON response retry loop integration test.

---

### TASK-025: Implement Candidate Evaluation Result Persistence
* **Priority:** High
* **Estimate:** 3 hours
* **Dependencies:** TASK-022
* **Files Affected:**
  * `src/infrastructure/persistence/postgres_evaluation_repo.py`
* **Acceptance Criteria:**
  * Save evaluation sub-scores, reasoning JSON, and evaluated timestamp in `candidate_evaluations` table.
  * Update candidate state to `EVALUATED`.
* **Unit Tests:** Evaluation repository entity mapping test.
* **Integration Tests:** PostgreSQL database evaluation record save test.

---

## Phase 6: Candidate Ranking & Shortlisting Engine (Tasks 026 - 030)

### TASK-026: Implement Weighted Composite Score Aggregator
* **Priority:** High
* **Estimate:** 3 hours
* **Dependencies:** TASK-025
* **Files Affected:**
  * `src/domain/services/composite_score_calculator.py`
* **Acceptance Criteria:**
  * Compute composite score formula: $0.35 S_{\text{Resume}} + 0.25 S_{\text{GitHub}} + 0.20 S_{\text{Aptitude}} + 0.20 S_{\text{Coding}}$.
  * Normalize score to scale of $0.00 - 100.00$.
* **Unit Tests:** Weighted composite score calculation unit test.
* **Integration Tests:** Composite score calculation DB update test.

---

### TASK-027: Implement Ranked Leaderboard Database Query Engine
* **Priority:** High
* **Estimate:** 4 hours
* **Dependencies:** TASK-026
* **Files Affected:**
  * `src/infrastructure/persistence/postgres_candidate_repo.py`
  * `src/presentation/api/v1/candidates_router.py`
* **Acceptance Criteria:**
  * Endpoint `GET /api/v1/candidates` returns candidate list sorted by `composite_score DESC`.
  * Support pagination (`limit`, `offset`) and status filtering.
* **Unit Tests:** Query builder parameter validation test.
* **Integration Tests:** Leaderboard API endpoint database query test.

---

### TASK-028: Implement Candidate Leaderboard Tie-Breaker Logic
* **Priority:** Medium
* **Estimate:** 2 hours
* **Dependencies:** TASK-027
* **Files Affected:**
  * `src/domain/services/candidate_tie_breaker.py`
* **Acceptance Criteria:**
  * In case of equal composite scores, order by `coding_score`, then `resume_score`, then `cgpa`.
* **Unit Tests:** Multi-column tie-breaker sorting algorithm test.
* **Integration Tests:** Database query test with equal score mock records.

---

### TASK-029: Implement Shortlist L1 Threshold Trigger Use Case
* **Priority:** High
* **Estimate:** 3 hours
* **Dependencies:** TASK-026
* **Files Affected:**
  * `src/application/use_cases/shortlist_candidates_l1.py`
* **Acceptance Criteria:**
  * Auto-shortlist top $N$ candidates based on initial AI score threshold $\tau_1$.
  * Transition candidate state to `SHORTLISTED_L1`.
* **Unit Tests:** Shortlisting cutoff boundary unit test.
* **Integration Tests:** Shortlist L1 trigger integration test.

---

### TASK-030: Implement Shortlist L2 Test Result Integration Trigger
* **Priority:** High
* **Estimate:** 4 hours
* **Dependencies:** TASK-029
* **Files Affected:**
  * `src/application/use_cases/shortlist_candidates_l2.py`
* **Acceptance Criteria:**
  * Re-calculate composite scores upon test result CSV ingestion.
  * Transition top qualifying candidates to state `SHORTLISTED_L2`.
* **Unit Tests:** L2 shortlist recalculation logic test.
* **Integration Tests:** Test result ingestion and L2 state transition test.

---

## Phase 7: Email & Interview Scheduling (Tasks 031 - 035)

### TASK-031: Implement Encrypted Recruiter SMTP Adapter
* **Priority:** High
* **Estimate:** 4 hours
* **Dependencies:** TASK-001
* **Files Affected:**
  * `src/infrastructure/external_services/smtp_email_adapter.py`
  * `src/domain/interfaces/email_client.py`
* **Acceptance Criteria:**
  * Send emails via custom recruiter SMTP configuration (Host, Port, User, Pass).
  * Decrypt stored SMTP password from database before connection.
* **Unit Tests:** Dynamic HTML email body template renderer test.
* **Integration Tests:** Mock SMTP server connection and email dispatch test.

---

### TASK-032: Implement Test Link Email Worker Task
* **Priority:** High
* **Estimate:** 3 hours
* **Dependencies:** TASK-031
* **Files Affected:**
  * `src/infrastructure/messaging/worker_tasks.py`
* **Acceptance Criteria:**
  * Worker task consumes `notification.send_test_link` task.
  * Dispatches test link email and logs delivery status in `email_logs`.
* **Unit Tests:** Task payload parser test.
* **Integration Tests:** Async email task queue dispatch test.

---

### TASK-033: Implement Google Calendar API freeBusy Availability Engine
* **Priority:** Critical
* **Estimate:** 5 hours
* **Dependencies:** TASK-004
* **Files Affected:**
  * `src/infrastructure/external_services/google_calendar_adapter.py`
  * `src/domain/interfaces/calendar_client.py`
* **Acceptance Criteria:**
  * Query Google Calendar `freeBusy` API for recruiter calendar ID.
  * Identify open 30-minute interview slots during working hours.
* **Unit Tests:** Working hour slot calculation algorithm test.
* **Integration Tests:** Mocked Google Calendar `freeBusy` response test.

---

### TASK-034: Implement Google Meet Video Link Event Generator
* **Priority:** Critical
* **Estimate:** 5 hours
* **Dependencies:** TASK-033
* **Files Affected:**
  * `src/application/use_cases/schedule_interview.py`
* **Acceptance Criteria:**
  * Create Google Calendar event with `conferenceDataVersion: 1`.
  * Save generated `google_meet_url` and `google_event_id` in `interviews` table.
* **Unit Tests:** Calendar event body serializer unit test.
* **Integration Tests:** Mocked Google Calendar API event creation test.

---

### TASK-035: Implement Automated Interview Email Inviter
* **Priority:** High
* **Estimate:** 3 hours
* **Dependencies:** TASK-034
* **Files Affected:**
  * `src/domain/services/interview_inviter.py`
* **Acceptance Criteria:**
  * Send interview invite email containing date, time, and Google Meet URL.
  * Update candidate state to `INTERVIEW_SCHEDULED`.
* **Unit Tests:** Interview email template rendering test.
* **Integration Tests:** End-to-end interview scheduling workflow test.

---

## Phase 8: Recruiter Dashboard UI (Tasks 036 - 040)

### TASK-036: Implement Recruiter Pipeline Funnel Dashboard Component
* **Priority:** High
* **Estimate:** 5 hours
* **Dependencies:** TASK-027
* **Files Affected:**
  * `src/presentation/ui/components/PipelineFunnel.tsx`
  * `src/presentation/ui/pages/Dashboard.tsx`
* **Acceptance Criteria:**
  * Render visual funnel tiles: Total Uploaded, Shortlisted L1, Test Completed, Shortlisted L2, Scheduled.
  * Responsive layout styled with modern CSS/Tailwind.
* **Unit Tests:** React component render test.
* **Integration Tests:** Funnel data API fetch integration test.

---

### TASK-037: Implement Ranked Candidate Table & Filter Component
* **Priority:** High
* **Estimate:** 5 hours
* **Dependencies:** TASK-036
* **Files Affected:**
  * `src/presentation/ui/components/CandidateTable.tsx`
* **Acceptance Criteria:**
  * Sortable columns for Composite Score, Resume Score, GitHub Score, Test Score.
  * Pagination controls and search filter by name or email.
* **Unit Tests:** Table row sorting unit test.
* **Integration Tests:** Candidate list API pagination integration test.

---

### TASK-038: Implement Candidate Detail Drawer & Explainable AI View
* **Priority:** High
* **Estimate:** 6 hours
* **Dependencies:** TASK-037
* **Files Affected:**
  * `src/presentation/ui/components/CandidateDrawer.tsx`
  * `src/presentation/ui/components/ExplainableAIView.tsx`
* **Acceptance Criteria:**
  * Sliding drawer displaying tabs: Resume Text, GitHub Metrics, Explainable AI Strengths & Concerns.
* **Unit Tests:** Tab switching component unit test.
* **Integration Tests:** Candidate details API endpoint fetch test.

---

### TASK-039: Implement Test Results CSV Upload Modal
* **Priority:** High
* **Estimate:** 4 hours
* **Dependencies:** TASK-030
* **Files Affected:**
  * `src/presentation/ui/components/TestUploadModal.tsx`
* **Acceptance Criteria:**
  * Modal for uploading test CSV containing fields `Email`, `test_la`, `test_code`.
  * Display success banner with count of updated records.
* **Unit Tests:** File dropzone component unit test.
* **Integration Tests:** Test result upload API integration test.

---

### TASK-040: Implement Real-Time Job Progress WebSockets Handler
* **Priority:** Medium
* **Estimate:** 4 hours
* **Dependencies:** TASK-010
* **Files Affected:**
  * `src/presentation/api/v1/websocket_router.py`
  * `src/presentation/ui/hooks/useProgressWebSocket.ts`
* **Acceptance Criteria:**
  * Push real-time batch processing updates to dashboard UI via WebSockets.
  * Auto-reconnect on connection loss.
* **Unit Tests:** WebSocket connection lifecycle test.
* **Integration Tests:** Background worker task progress push test.

---

## Phase 9: Observability, Security & CI/CD Deployment (Tasks 041 - 045)

### TASK-041: Implement Prometheus Metrics Exporter
* **Priority:** Medium
* **Estimate:** 3 hours
* **Dependencies:** None
* **Files Affected:**
  * `src/infrastructure/observability/metrics.py`
  * `src/presentation/api/v1/metrics_router.py`
* **Acceptance Criteria:**
  * Expose `/metrics` endpoint for Prometheus scraping.
  * Track candidate process rates, LLM API latency, and queue lengths.
* **Unit Tests:** Metric counter increment unit test.
* **Integration Tests:** Prometheus `/metrics` scraping HTTP endpoint test.

---

### TASK-042: Implement Structured JSON Logger & PII Redaction Filter
* **Priority:** High
* **Estimate:** 3 hours
* **Dependencies:** None
* **Files Affected:**
  * `src/infrastructure/observability/json_logger.py`
* **Acceptance Criteria:**
  * Format all application logs as structured JSON containing `timestamp`, `level`, `trace_id`.
  * Mask sensitive PII fields (Email, Phone) in log outputs.
* **Unit Tests:** Log string PII masking regex test.
* **Integration Tests:** End-to-end API request trace ID logging test.

---

### TASK-043: Implement Multi-Stage Production OCI Dockerfile
* **Priority:** High
* **Estimate:** 4 hours
* **Dependencies:** None
* **Files Affected:**
  * `Dockerfile`
  * `docker-compose.yml`
  * `.dockerignore`
* **Acceptance Criteria:**
  * Build multi-stage OCI image for API service and async workers.
  * Final container image size $< 250$MB running under non-root `appuser`.
* **Unit Tests:** Container build script test.
* **Integration Tests:** Container healthcheck probe (`/healthz`) test.

---

### TASK-044: Implement Database Migration & Readiness Probe Endpoints
* **Priority:** High
* **Estimate:** 3 hours
* **Dependencies:** TASK-001
* **Files Affected:**
  * `src/presentation/api/v1/health_router.py`
* **Acceptance Criteria:**
  * Endpoint `/healthz` returns `200 OK`.
  * Endpoint `/readyz` checks PostgreSQL DB pool and Redis connectivity before returning `200 OK`.
* **Unit Tests:** Health check route unit test.
* **Integration Tests:** Simulated DB outage readiness failure test.

---

### TASK-045: Implement GitHub Actions Automated CI/CD Pipeline
* **Priority:** High
* **Estimate:** 5 hours
* **Dependencies:** TASK-043, TASK-044
* **Files Affected:**
  * `.github/workflows/ci-cd-pipeline.yml`
* **Acceptance Criteria:**
  * Trigger pipeline on pull requests and pushes to `main` branch.
  * Execute stages: Linting, Unit/Integration Tests, Semgrep Security Scan, OCI Image Build, and Deployment.
* **Unit Tests:** GitHub Actions YAML syntax check.
* **Integration Tests:** CI workflow run on test repository branch.

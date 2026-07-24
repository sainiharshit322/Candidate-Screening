import json
import logging
import requests
from typing import Dict, Any
from src.config import settings
from src.domain.entities.candidate import Candidate, JobDescription
from src.domain.interfaces import IEvaluationEngine

logger = logging.getLogger(__name__)

class GeminiEvaluationEngine(IEvaluationEngine):
    def evaluate(self, candidate: Candidate, jd: JobDescription) -> Dict[str, Any]:
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set. Using heuristic fallback evaluation.")
            return self._heuristic_fallback(candidate, jd)

        prompt = self._build_prompt(candidate, jd)

        # Try Gemini API endpoints (gemini-2.5-flash, gemini-2.0-flash, gemini-1.5-flash)
        models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

        headers = {"Content-Type": "application/json"}
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    candidates_choices = data.get("candidates", [])
                    if candidates_choices:
                        text_content = candidates_choices[0]["content"]["parts"][0]["text"]
                        eval_json = json.loads(text_content)
                        resume_score = float(eval_json.get("resume_score", 70.0))
                        resume_score = max(0.0, min(100.0, resume_score))
                        return {
                            "resume_score": resume_score,
                            "relevance_score": float(eval_json.get("relevance_score", 70.0)),
                            "technical_depth_score": float(eval_json.get("technical_depth_score", 70.0)),
                            "strengths": eval_json.get("strengths", []),
                            "concerns": eval_json.get("concerns", []),
                            "summary": eval_json.get("summary", "Evaluation complete."),
                            "evaluator": f"Gemini ({model_name})"
                        }
            except Exception as e:
                logger.warning(f"Failed Gemini attempt for {model_name}: {str(e)}")

        logger.warning("All Gemini model endpoints failed. Using heuristic fallback evaluation.")
        return self._heuristic_fallback(candidate, jd)


    def _build_prompt(self, candidate: Candidate, jd: JobDescription) -> str:
        resume_snippet = candidate.resume_text[:3000] if candidate.resume_text else "Not provided"
        ai_proj = candidate.best_ai_project or "Not provided"
        research = candidate.research_work or "Not provided"
        github_handle = candidate.github_handle or "Not provided"
        github_score = candidate.github_score or 0.0

        return f"""
System Instruction: You are a Principal Technical Recruiter. Evaluate the candidate against the Job Description.
Return a STRICT JSON object with the following schema:
{{
  "resume_score": number (0-100),
  "relevance_score": number (0-100),
  "technical_depth_score": number (0-100),
  "strengths": [string],
  "concerns": [string],
  "summary": string
}}

Target Job Description:
Title: {jd.title}
Description: {jd.description}
Required Skills: {", ".join(jd.required_skills)}

Candidate Context:
Name: {candidate.name}
College: {candidate.college or 'N/A'}
Branch: {candidate.branch or 'N/A'}
CGPA: {candidate.cgpa or 'N/A'}
GitHub Profile: {github_handle} (Effort Score: {github_score}/100)

<best_ai_project>
{ai_proj}
</best_ai_project>

<research_work>
{research}
</research_work>

<resume_text>
{resume_snippet}
</resume_text>
"""

    def _heuristic_fallback(self, candidate: Candidate, jd: JobDescription) -> Dict[str, Any]:
        """Deterministic heuristic evaluation fallback when API is unreachable."""
        score = 60.0
        strengths = []
        concerns = []

        if candidate.cgpa and candidate.cgpa >= 8.0:
            score += 15.0
            strengths.append(f"Strong academic performance (CGPA: {candidate.cgpa})")
        elif candidate.cgpa and candidate.cgpa < 7.0:
            concerns.append(f"Lower academic CGPA: {candidate.cgpa}")

        if candidate.best_ai_project and len(candidate.best_ai_project) > 50:
            score += 15.0
            strengths.append("Detailed AI project experience provided")

        if candidate.research_work and len(candidate.research_work) > 30:
            score += 10.0
            strengths.append("Research experience documented")

        score = max(0.0, min(100.0, score))
        return {
            "resume_score": score,
            "relevance_score": score,
            "technical_depth_score": score,
            "strengths": strengths,
            "concerns": concerns,
            "summary": "Heuristic evaluation based on structured profile fields.",
            "evaluator": "Heuristic Fallback Engine"
        }

import re
import logging
import requests
from typing import Dict, Any
from src.config import settings
from src.domain.interfaces import IGitHubAnalyzer

logger = logging.getLogger(__name__)

class RESTGitHubAnalyzer(IGitHubAnalyzer):
    @staticmethod
    def extract_handle(github_url_or_handle: str) -> str:
        if not github_url_or_handle:
            return ""
        # Match URL: github.com/username
        clean = github_url_or_handle.strip().rstrip('/')
        match = re.search(r'github\.com/([a-zA-Z0-9_-]+)', clean)
        if match:
            return match.group(1)
        # If raw username string
        return clean.replace('@', '')

    def analyze(self, github_url_or_handle: str) -> Dict[str, Any]:
        handle = self.extract_handle(github_url_or_handle)
        if not handle:
            return {
                "handle": "",
                "score": 0.0,
                "public_repos": 0,
                "total_stars": 0,
                "languages": [],
                "status": "NO_GITHUB_HANDLE"
            }

        headers = {}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        url = f"https://api.github.com/users/{handle}/repos?per_page=100&sort=updated"
        logger.info(f"Analyzing GitHub profile for handle: {handle}")

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.warning(f"GitHub API request failed for {handle}. HTTP {response.status_code}")
                return {
                    "handle": handle,
                    "score": 0.0,
                    "public_repos": 0,
                    "total_stars": 0,
                    "languages": [],
                    "status": f"GITHUB_API_HTTP_{response.status_code}"
                }

            repos = response.json()
            if not isinstance(repos, list):
                return {
                    "handle": handle,
                    "score": 0.0,
                    "public_repos": 0,
                    "total_stars": 0,
                    "languages": [],
                    "status": "INVALID_RESPONSE"
                }

            total_stars = 0
            original_repos_count = 0
            languages = {}

            for repo in repos:
                if not repo.get("fork", False):
                    original_repos_count += 1
                    total_stars += repo.get("stargazers_count", 0)
                    lang = repo.get("language")
                    if lang:
                        languages[lang] = languages.get(lang, 0) + 1

            # Compute GitHub Effort Score (0 - 100)
            # Base repo score: up to 40 pts (4 pts per original repo up to 10 repos)
            # Star score: up to 40 pts (5 pts per star up to 8 stars)
            # Language diversity score: up to 20 pts (5 pts per unique language up to 4 languages)
            repo_pts = min(40.0, original_repos_count * 4.0)
            star_pts = min(40.0, total_stars * 5.0)
            lang_pts = min(20.0, len(languages) * 5.0)
            
            github_score = round(repo_pts + star_pts + lang_pts, 2)

            return {
                "handle": handle,
                "score": github_score,
                "public_repos": len(repos),
                "original_repos": original_repos_count,
                "total_stars": total_stars,
                "languages": list(languages.keys()),
                "language_distribution": languages,
                "status": "ANALYZED"
            }

        except Exception as e:
            logger.error(f"Error analyzing GitHub handle {handle}: {str(e)}")
            return {
                "handle": handle,
                "score": 0.0,
                "public_repos": 0,
                "total_stars": 0,
                "languages": [],
                "status": f"ERROR: {str(e)}"
            }

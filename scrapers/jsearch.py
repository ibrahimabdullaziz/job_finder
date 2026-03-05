"""JSearch API via RapidAPI — sources from Google for Jobs.
Free tier: limited requests/month. Get key at rapidapi.com."""

import logging
import os

import requests

from models import Job, JobBoard, SearchQuery

logger = logging.getLogger(__name__)

API_URL = "https://jsearch.p.rapidapi.com/search"


class JSearchScraper:
    """Fetch jobs from JSearch (Google Jobs aggregator via RapidAPI)."""

    def __init__(self):
        self.api_key = os.environ.get("RAPIDAPI_KEY", "")
        if not self.api_key:
            logger.warning(
                "RAPIDAPI_KEY not set. "
                "Get a free key at https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch"
            )

    def scrape(self, query: SearchQuery, max_results: int = 50) -> list[Job]:
        if not self.api_key:
            logger.warning("Skipping JSearch (no API key)")
            return []

        jobs = []
        page = 1
        per_page = min(20, max_results)  # JSearch max per page

        while len(jobs) < max_results:
            headers = {
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            }

            search_query = query.keywords
            if query.location:
                search_query += f" in {query.location}"
            if query.remote:
                search_query += " remote"

            params = {
                "query": search_query,
                "page": str(page),
                "num_pages": "1",
                "date_posted": self._age_to_filter(query.max_age_days),
            }
            if query.job_type:
                params["employment_types"] = query.job_type.upper().replace("-", "")

            try:
                resp = requests.get(API_URL, headers=headers, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error(f"JSearch API error: {e}")
                break

            results = data.get("data", [])
            if not results:
                break

            for item in results:
                job = Job(
                    title=item.get("job_title", ""),
                    company=item.get("employer_name", "Unknown"),
                    location=f"{item.get('job_city', '')} {item.get('job_country', '')}".strip(),
                    url=item.get("job_apply_link", "") or item.get("job_google_link", ""),
                    board=JobBoard.JSEARCH,
                    description=item.get("job_description", ""),
                    salary=self._format_salary(item),
                    date_posted=item.get("job_posted_at_datetime_utc", ""),
                    job_type=item.get("job_employment_type", ""),
                )
                if job.url and job.title:
                    jobs.append(job)

            page += 1
            if len(results) < per_page:
                break

        logger.info(f"  JSearch: {len(jobs)} jobs found")
        return jobs[:max_results]

    def get_job_details(self, job: Job) -> Job:
        # JSearch returns full descriptions
        return job

    def _age_to_filter(self, days: int) -> str:
        if days <= 1:
            return "today"
        elif days <= 3:
            return "3days"
        elif days <= 7:
            return "week"
        else:
            return "month"

    def _format_salary(self, item: dict) -> str:
        min_sal = item.get("job_min_salary")
        max_sal = item.get("job_max_salary")
        currency = item.get("job_salary_currency", "")
        period = item.get("job_salary_period", "")
        if min_sal and max_sal:
            return f"{currency} {int(min_sal):,} - {int(max_sal):,} {period}".strip()
        return ""

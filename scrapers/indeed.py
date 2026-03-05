"""Indeed job scraper."""

import logging
import urllib.parse

from models import Job, JobBoard, SearchQuery
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.indeed.com"


class IndeedScraper(BaseScraper):
    """Scrape jobs from Indeed search results."""

    def scrape(self, query: SearchQuery, max_results: int = 50) -> list[Job]:
        jobs = []
        start = 0
        per_page = 10

        while len(jobs) < max_results:
            params = {
                "q": query.keywords,
                "l": query.location,
                "start": start,
                "fromage": query.max_age_days,
            }
            if query.job_type:
                params["jt"] = query.job_type
            if query.remote:
                params["remotejob"] = "032b3046-06a3-4876-8dfd-474eb5e7ed11"

            soup = self._get(f"{BASE_URL}/jobs", params=params)
            if not soup:
                break

            cards = soup.select("div.job_seen_beacon, div.jobsearch-ResultsList > div")
            if not cards:
                # Try alternative selectors (Indeed changes DOM frequently)
                cards = soup.select("[data-jk]")
            if not cards:
                logger.info("No more Indeed results found")
                break

            for card in cards:
                try:
                    job = self._parse_card(card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Failed to parse Indeed card: {e}")

            start += per_page
            if len(cards) < per_page:
                break

        return jobs[:max_results]

    def _parse_card(self, card) -> Job | None:
        # Title
        title_el = card.select_one("h2.jobTitle a, h2.jobTitle span, a.jcs-JobTitle")
        if not title_el:
            return None
        title = title_el.get_text(strip=True)

        # URL
        link = card.select_one("a[href*='/rc/clk'], a[href*='viewjob'], a.jcs-JobTitle")
        if link and link.get("href"):
            url = urllib.parse.urljoin(BASE_URL, link["href"])
        else:
            jk = card.get("data-jk", "")
            url = f"{BASE_URL}/viewjob?jk={jk}" if jk else ""

        if not url:
            return None

        # Company
        company_el = card.select_one("span.css-63koeb, span[data-testid='company-name'], div.company_location span.companyName")
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        # Location
        loc_el = card.select_one("div[data-testid='text-location'], div.companyLocation")
        location = loc_el.get_text(strip=True) if loc_el else ""

        # Salary
        salary_el = card.select_one("div.salary-snippet-container, div[data-testid='attribute_snippet_testid']")
        salary = salary_el.get_text(strip=True) if salary_el else ""

        # Snippet / description preview
        snippet_el = card.select_one("div.job-snippet, td.resultContent div.css-9446fg")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        return Job(
            title=title,
            company=company,
            location=location,
            url=url,
            board=JobBoard.INDEED,
            description=snippet,
            salary=salary,
        )

    def get_job_details(self, job: Job) -> Job:
        soup = self._get(job.url)
        if not soup:
            return job

        desc_el = soup.select_one("div#jobDescriptionText, div.jobsearch-jobDescriptionText")
        if desc_el:
            job.description = desc_el.get_text(separator="\n", strip=True)

        return job

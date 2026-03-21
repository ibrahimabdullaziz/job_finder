"""Glassdoor job scraper."""

import logging
import urllib.parse
from typing import Optional

from models import Job, JobBoard, SearchQuery
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.glassdoor.com"


class GlassdoorScraper(BaseScraper):
    """Scrape Glassdoor job listings."""

    def scrape(self, query: SearchQuery, max_results: int = 50) -> list[Job]:
        jobs = []
        page = 1

        while len(jobs) < max_results:
            keyword_slug = urllib.parse.quote_plus(query.keywords)
            location_slug = urllib.parse.quote_plus(query.location) if query.location else ""

            url = f"{BASE_URL}/Job/jobs.htm"
            params = {
                "sc.keyword": query.keywords,
                "locT": "",
                "locId": "",
                "locKeyword": query.location,
                "jobType": "",
                "fromAge": query.max_age_days,
                "p": page,
            }

            soup = self._get(url, params=params)
            if not soup:
                break

            cards = soup.select(
                "li.react-job-listing, "
                "li[data-test='jobListing'], "
                "div.JobCard_jobCardContainer__arQlW"
            )
            if not cards:
                logger.info("No more Glassdoor results found")
                break

            for card in cards:
                try:
                    job = self._parse_card(card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Failed to parse Glassdoor card: {e}")

            page += 1
            if len(cards) < 10:
                break

        return jobs[:max_results]

    def _parse_card(self, card) -> Optional[Job]:
        title_el = card.select_one(
            "a.jobLink, "
            "a[data-test='job-link'], "
            "a.JobCard_jobTitle__GLyJ1"
        )
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        url = urllib.parse.urljoin(BASE_URL, title_el.get("href", ""))
        if not url or url == BASE_URL:
            return None

        company_el = card.select_one(
            "div.jobHeader a, "
            "span.EmployerProfile_employerName__0dMPx, "
            "div[data-test='emp-name']"
        )
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        loc_el = card.select_one(
            "span.subtle.loc, "
            "span[data-test='emp-location'], "
            "div.JobCard_location__rCz3x"
        )
        location = loc_el.get_text(strip=True) if loc_el else ""

        salary_el = card.select_one(
            "span.css-18034rf, "
            "div[data-test='detailSalary'], "
            "div.JobCard_salaryEstimate__arV5J"
        )
        salary = salary_el.get_text(strip=True) if salary_el else ""

        return Job(
            title=title,
            company=company,
            location=location,
            url=url,
            board=JobBoard.GLASSDOOR,
            salary=salary,
        )

    def get_job_details(self, job: Job) -> Job:
        soup = self._get(job.url)
        if not soup:
            return job

        desc_el = soup.select_one(
            "div.jobDescriptionContent, "
            "div[data-test='jobDescription'], "
            "div.JobDetails_jobDescription__uW_fK"
        )
        if desc_el:
            job.description = desc_el.get_text(separator="\n", strip=True)

        return job

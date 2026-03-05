"""LinkedIn job scraper (public guest API, no login required)."""

import logging
import urllib.parse

from models import Job, JobBoard, SearchQuery
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.linkedin.com"

# LinkedIn job type mapping
JOB_TYPE_MAP = {
    "full-time": "F",
    "part-time": "P",
    "contract": "C",
    "internship": "I",
    "temporary": "T",
}


class LinkedInScraper(BaseScraper):
    """Scrape LinkedIn public job search (no authentication needed)."""

    def scrape(self, query: SearchQuery, max_results: int = 50) -> list[Job]:
        jobs = []
        start = 0
        per_page = 25

        while len(jobs) < max_results:
            params = {
                "keywords": query.keywords,
                "location": query.location,
                "start": start,
                "f_TPR": f"r{query.max_age_days * 86400}",  # time posted filter
            }
            if query.remote:
                params["f_WT"] = "2"  # remote filter
            if query.job_type and query.job_type in JOB_TYPE_MAP:
                params["f_JT"] = JOB_TYPE_MAP[query.job_type]

            soup = self._get(f"{BASE_URL}/jobs/search/", params=params)
            if not soup:
                break

            cards = soup.select("div.base-card, li.result-card, div.job-search-card")
            if not cards:
                # Fallback selector
                cards = soup.select("ul.jobs-search__results-list > li")
            if not cards:
                logger.info("No more LinkedIn results found")
                break

            for card in cards:
                try:
                    job = self._parse_card(card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Failed to parse LinkedIn card: {e}")

            start += per_page
            if len(cards) < per_page:
                break

        return jobs[:max_results]

    def _parse_card(self, card) -> Job | None:
        title_el = card.select_one("h3.base-search-card__title, h3.job-search-card__title")
        if not title_el:
            return None
        title = title_el.get_text(strip=True)

        link = card.select_one("a.base-card__full-link, a.result-card__full-card-link")
        url = link["href"].split("?")[0] if link and link.get("href") else ""
        if not url:
            return None

        company_el = card.select_one("h4.base-search-card__subtitle a, h4.job-search-card__subtitle")
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        loc_el = card.select_one("span.job-search-card__location")
        location = loc_el.get_text(strip=True) if loc_el else ""

        date_el = card.select_one("time")
        date_posted = date_el.get("datetime", "") if date_el else ""

        return Job(
            title=title,
            company=company,
            location=location,
            url=url,
            board=JobBoard.LINKEDIN,
            date_posted=date_posted,
        )

    def get_job_details(self, job: Job) -> Job:
        soup = self._get(job.url)
        if not soup:
            return job

        desc_el = soup.select_one(
            "div.show-more-less-html__markup, "
            "div.description__text, "
            "section.show-more-less-html"
        )
        if desc_el:
            job.description = desc_el.get_text(separator="\n", strip=True)

        return job

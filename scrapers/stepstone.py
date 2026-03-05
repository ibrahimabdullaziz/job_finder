"""Stepstone job scraper."""

import logging
import urllib.parse

from models import Job, JobBoard, SearchQuery
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.stepstone.de"


class StepstoneScraper(BaseScraper):
    """Scrape Stepstone (Germany) job listings."""

    def scrape(self, query: SearchQuery, max_results: int = 50) -> list[Job]:
        jobs = []
        page = 1

        while len(jobs) < max_results:
            params = {
                "q": query.keywords,
                "li": query.location if query.location else "",
                "of": (page - 1) * 25,
                "action": "facet_selected;age;" + str(query.max_age_days),
            }
            if query.remote:
                params["wt"] = "homeoffice"

            soup = self._get(f"{BASE_URL}/jobs", params=params)
            if not soup:
                break

            cards = soup.select(
                "article[data-at='job-item'], "
                "div[data-testid='job-item'], "
                "article.res-1p8f0z4"
            )
            if not cards:
                logger.info("No more Stepstone results found")
                break

            for card in cards:
                try:
                    job = self._parse_card(card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Failed to parse Stepstone card: {e}")

            page += 1
            if len(cards) < 25:
                break

        return jobs[:max_results]

    def _parse_card(self, card) -> Job | None:
        title_el = card.select_one(
            "a[data-at='job-item-title'], "
            "h2 a, "
            "a[data-testid='job-item-title']"
        )
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        url = urllib.parse.urljoin(BASE_URL, href) if href else ""
        if not url:
            return None

        company_el = card.select_one(
            "div[data-at='job-item-company-name'], "
            "span[data-testid='job-item-company-name'], "
            "a[data-at='job-item-company-name']"
        )
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        loc_el = card.select_one(
            "span[data-at='job-item-location'], "
            "span[data-testid='job-item-location']"
        )
        location = loc_el.get_text(strip=True) if loc_el else ""

        return Job(
            title=title,
            company=company,
            location=location,
            url=url,
            board=JobBoard.STEPSTONE,
        )

    def get_job_details(self, job: Job) -> Job:
        soup = self._get(job.url)
        if not soup:
            return job

        desc_el = soup.select_one(
            "div[data-at='job-ad-content'], "
            "div.listing-content, "
            "div[data-testid='job-ad-content']"
        )
        if desc_el:
            job.description = desc_el.get_text(separator="\n", strip=True)

        return job

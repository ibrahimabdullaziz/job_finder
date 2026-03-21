"""LinkedIn Guest API — unofficial, no auth needed.
Uses the public jobs-guest endpoint. May break if LinkedIn changes their API."""

import logging
import time
import random
from typing import Optional

import requests
from bs4 import BeautifulSoup

from models import Job, JobBoard, SearchQuery

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

JOB_TYPE_MAP = {
    "full-time": "F",
    "part-time": "P",
    "contract": "C",
    "internship": "I",
}

# LinkedIn geoId for target regions
GEO_IDS = {
    "germany": "101282230",
    "france": "105015875",
    "netherlands": "102890719",
    "belgium": "100565514",
    "switzerland": "106693272",
    "uk": "101165590",
    "united kingdom": "101165590",
    "europe": "100506914",
    "uae": "104305776",
    "saudi arabia": "100459316",
    "qatar": "104104669",
    "remote": "",
}


class LinkedInGuestScraper:
    """Scrape LinkedIn public job API (no login required)."""

    def __init__(self, delay_range: tuple[float, float] = (1.5, 3.0)):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.delay_range = delay_range

    def scrape(self, query: SearchQuery, max_results: int = 50) -> list[Job]:
        jobs = []
        start = 0
        per_page = 25

        while len(jobs) < max_results:
            params = {
                "keywords": query.keywords,
                "start": start,
                "f_TPR": f"r{query.max_age_days * 86400}",
            }

            # Location / geoId
            geo_id = self._resolve_geo(query.location)
            if geo_id:
                params["geoId"] = geo_id
            elif query.location:
                params["location"] = query.location

            if query.remote:
                params["f_WT"] = "2"  # remote filter
            if query.job_type and query.job_type in JOB_TYPE_MAP:
                params["f_JT"] = JOB_TYPE_MAP[query.job_type]

            time.sleep(random.uniform(*self.delay_range))

            try:
                resp = self.session.get(SEARCH_URL, params=params, timeout=15)
                if resp.status_code == 429:
                    logger.warning("LinkedIn rate limited, stopping")
                    break
                resp.raise_for_status()
            except Exception as e:
                logger.error(f"LinkedIn guest API error: {e}")
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("li")
            if not cards:
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

        logger.info(f"  LinkedIn (guest): {len(jobs)} jobs found")
        return jobs[:max_results]

    def _parse_card(self, card) -> Optional[Job]:
        title_el = card.select_one("h3.base-search-card__title")
        if not title_el:
            return None
        title = title_el.get_text(strip=True)

        link_el = card.select_one("a.base-card__full-link")
        url = link_el["href"].split("?")[0] if link_el and link_el.get("href") else ""
        if not url:
            return None

        company_el = card.select_one("h4.base-search-card__subtitle a")
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
        """Fetch full job description from LinkedIn."""
        # Extract job ID from URL
        job_id = job.url.rstrip("/").split("-")[-1] if job.url else ""
        if not job_id or not job_id.isdigit():
            return job

        time.sleep(random.uniform(*self.delay_range))

        try:
            resp = self.session.get(f"{DETAIL_URL}/{job_id}", timeout=15)
            if resp.status_code != 200:
                return job
        except Exception:
            return job

        soup = BeautifulSoup(resp.text, "html.parser")
        desc_el = soup.select_one(
            "div.show-more-less-html__markup, "
            "div.description__text"
        )
        if desc_el:
            job.description = desc_el.get_text(separator="\n", strip=True)

        return job

    def _resolve_geo(self, location: str) -> str:
        if not location:
            return ""
        loc = location.lower().strip()
        for key, geo_id in GEO_IDS.items():
            if key in loc:
                return geo_id
        return ""

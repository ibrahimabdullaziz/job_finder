"""Base scraper interface."""

import logging
import time
import random
from abc import ABC, abstractmethod
from typing import Optional

import requests
from bs4 import BeautifulSoup

from models import Job, SearchQuery

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class BaseScraper(ABC):
    """Abstract base class for job board scrapers."""

    def __init__(self, delay_range: tuple[float, float] = (1.0, 3.0)):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.delay_range = delay_range

    def _get(self, url: str, params: Optional[dict] = None) -> Optional[BeautifulSoup]:
        """Fetch a URL and return parsed HTML."""
        try:
            time.sleep(random.uniform(*self.delay_range))
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

    @abstractmethod
    def scrape(self, query: SearchQuery, max_results: int = 50) -> list[Job]:
        """Scrape jobs matching the query. Returns list of Job objects."""
        ...

    @abstractmethod
    def get_job_details(self, job: Job) -> Job:
        """Fetch full job description for a scraped job."""
        ...

from .base import BaseScraper
from .indeed import IndeedScraper
from .linkedin import LinkedInScraper
from .glassdoor import GlassdoorScraper
from .stepstone import StepstoneScraper
from .remotive import RemotiveScraper
from .adzuna import AdzunaScraper
from .jsearch import JSearchScraper
from .linkedin_guest import LinkedInGuestScraper

SCRAPERS = {
    "indeed": IndeedScraper,
    "linkedin": LinkedInGuestScraper,
    "glassdoor": GlassdoorScraper,
    "stepstone": StepstoneScraper,
    "remotive": RemotiveScraper,
    "adzuna": AdzunaScraper,
    "jsearch": JSearchScraper,
}

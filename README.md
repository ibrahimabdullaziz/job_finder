# AI Apply — Job Scraping & Matching Pipeline

Automated job scraper and matcher that pulls listings from multiple job boards, scores them against your profile (skills, preferred titles, keywords, locations), and presents the best matches via CLI or a web dashboard.

---

## Features

- **Multi-source scraping** — pulls from 7 job boards simultaneously
- **Smart matching** — TF-IDF-style scoring against your skills, titles, keywords, and location preferences
- **AI relevance filter** — automatically filters for ML/AI/CV-related roles
- **SQLite storage** — deduplicates and persists all scraped jobs
- **Web dashboard** — Flask UI with filtering, sorting, and apply/hide actions
- **CLI tools** — scrape, match, export, and view top jobs from the terminal

---

## Supported Job Sources

| Source | Type | API Key Required | Signup URL |
|---|---|---|---|
| **Remotive** | REST API | No | — |
| **Adzuna** | REST API | Yes | [developer.adzuna.com](https://developer.adzuna.com) |
| **JSearch** (Google Jobs) | RapidAPI | Yes | [rapidapi.com/jsearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) |
| **LinkedIn** | Guest scraper | No | — |
| **Indeed** | Web scraper | No | — |
| **Glassdoor** | Web scraper | No | — |
| **StepStone** | Web scraper | No | — |

### Recommended Additional APIs to Add

| API | Coverage | Free Tier | URL |
|---|---|---|---|
| **Arbeitnow** | EU + remote jobs | Unlimited, no key | [arbeitnow.com/api](https://www.arbeitnow.com/api) |
| **The Muse** | Curated tech/ML jobs | Unlimited, no key | [themuse.com/developers](https://www.themuse.com/developers) |
| **Reed** | UK jobs | 10k req/day, free key | [reed.co.uk/developers](https://www.reed.co.uk/developers) |
| **findwork.dev** | Dev/ML-focused jobs | 50 req/day, free key | [findwork.dev](https://findwork.dev) |
| **USAJobs** | US government roles | Unlimited, free key | [developer.usajobs.gov](https://developer.usajobs.gov) |
| **Himalayas** | Remote tech jobs | Unlimited, no key | [himalayas.app/api](https://himalayas.app/api) |
| **Wellfound** (AngelList) | Startup jobs | Varies | [wellfound.com](https://wellfound.com) |

---

## Quick Start

### 1. Clone & Install

```bash
git clone <your-repo-url> && cd open_aiapply
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Your Profile

Edit `profile.yaml` with your skills, desired titles, keywords, locations, and scoring weights. The file is self-documenting — update each section to match your background.

### 3. Set API Keys (optional but recommended)

```bash
# Adzuna — free at https://developer.adzuna.com
export ADZUNA_APP_ID="your_app_id"
export ADZUNA_APP_KEY="your_app_key"

# JSearch (RapidAPI) — free at https://rapidapi.com
export RAPIDAPI_KEY="your_rapidapi_key"
```

> **Tip:** Add these to a `.env` file or your shell profile (`~/.bashrc`).

Sources without API keys (Remotive, LinkedIn, Indeed, Glassdoor, StepStone) work out of the box.

---

## Usage

### Scrape Jobs

```bash
# Scrape all configured boards (set in profile.yaml → search.boards)
python main.py scrape

# Scrape specific boards only
python main.py scrape --boards remotive adzuna linkedin

# Limit results per board per query
python main.py scrape --max 30

# Also fetch full job descriptions (slower but better matching)
python main.py scrape --fetch-details
```

### Re-Score Jobs

After editing `profile.yaml`, re-score all stored jobs without re-scraping:

```bash
python main.py match

# Only keep jobs above a minimum score
python main.py match --min-score 0.3
```

### View Top Matches

```bash
# Show top 20 jobs
python main.py top

# Show top 50 with minimum score
python main.py top --limit 50 --min-score 0.2
```

### Export to JSON

```bash
python main.py export -o top_jobs.json
python main.py export --limit 100 --min-score 0.3 -o filtered.json
```

### Launch Web Dashboard

```bash
python main.py ui

# Custom port / debug mode
python main.py ui --port 8080 --debug
```

Then open **http://localhost:5000** (or your custom port) in a browser.

---

## Project Structure

```
open_aiapply/
├── main.py              # CLI entry point (scrape, match, top, export, ui)
├── app.py               # Flask web dashboard
├── matcher.py           # Scoring engine (TF-IDF + keyword matching)
├── models.py            # Data models (Job, JobBoard, SearchQuery)
├── storage.py           # SQLite persistence layer
├── profile.yaml         # Your profile config (skills, titles, search params)
├── requirements.txt     # Python dependencies
├── jobs.db              # SQLite database (created on first run)
├── scrapers/
│   ├── base.py          # Abstract scraper interface
│   ├── adzuna.py        # Adzuna API scraper
│   ├── jsearch.py       # JSearch (RapidAPI) scraper
│   ├── remotive.py      # Remotive API scraper
│   ├── linkedin.py      # LinkedIn scraper (authenticated)
│   ├── linkedin_guest.py# LinkedIn guest scraper (no login)
│   ├── indeed.py        # Indeed scraper
│   ├── glassdoor.py     # Glassdoor scraper
│   └── stepstone.py     # StepStone scraper
├── templates/           # Jinja2 templates for web UI
│   ├── base.html
│   ├── dashboard.html
│   ├── jobs.html
│   └── job_detail.html
└── static/              # CSS/JS assets
```

---

## Configuration Reference

### `profile.yaml`

| Section | Description |
|---|---|
| `skills` | Your technical skills (matched against job descriptions) |
| `titles` | Desired job titles (matched against job titles) |
| `keywords` | Domain keywords that boost a job's score |
| `search.queries` | Search terms sent to each job board |
| `search.locations` | Locations to search (one query per location × keyword) |
| `search.boards` | Which boards to scrape (`remotive`, `adzuna`, `linkedin`, `jsearch`, `indeed`, `glassdoor`, `stepstone`) |
| `search.remote` | Include remote positions |
| `search.max_age_days` | Skip jobs older than N days |
| `preferred_locations` | Locations that boost a job's score |
| `weights` | Scoring weights for skills/title/keywords/location (should sum to ~1.0) |

---

## Adding a New Scraper

1. Create `scrapers/my_board.py` implementing `scrape()` and `get_job_details()` methods
2. Add the board to the `JobBoard` enum in `models.py`
3. Register it in `scrapers/__init__.py`:
   ```python
   from .my_board import MyBoardScraper
   SCRAPERS["my_board"] = MyBoardScraper
   ```
4. Add `"my_board"` to the `search.boards` list in `profile.yaml`

---

## Environment Variables

| Variable | Required For | Where to Get |
|---|---|---|
| `ADZUNA_APP_ID` | Adzuna | [developer.adzuna.com](https://developer.adzuna.com) |
| `ADZUNA_APP_KEY` | Adzuna | [developer.adzuna.com](https://developer.adzuna.com) |
| `RAPIDAPI_KEY` | JSearch | [rapidapi.com](https://rapidapi.com) |

---

## License

MIT

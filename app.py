"""Flask web UI for AI Apply."""

import json
import logging
import threading
from pathlib import Path

import yaml
from flask import Flask, render_template, request, jsonify, redirect, url_for

from models import Job, JobBoard, SearchQuery
from scrapers import SCRAPERS
from matcher import JobMatcher
from storage import (
    get_db, save_jobs, update_scores, get_top_jobs,
    mark_applied, mark_hidden, DB_PATH,
)

logger = logging.getLogger(__name__)
CONFIG_PATH = Path(__file__).parent / "profile.yaml"


def load_profile() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.route("/")
    def dashboard():
        """Main dashboard showing stats and top jobs."""
        conn = get_db()
        total = conn.execute("SELECT COUNT(*) FROM jobs WHERE hidden = 0").fetchone()[0]
        applied = conn.execute("SELECT COUNT(*) FROM jobs WHERE applied = 1").fetchone()[0]
        avg_score = conn.execute("SELECT AVG(match_score) FROM jobs WHERE hidden = 0").fetchone()[0] or 0

        # Board distribution
        boards = conn.execute(
            "SELECT board, COUNT(*) as cnt FROM jobs WHERE hidden = 0 GROUP BY board ORDER BY cnt DESC"
        ).fetchall()

        # Top jobs
        top = conn.execute(
            "SELECT * FROM jobs WHERE hidden = 0 ORDER BY match_score DESC, date_posted DESC LIMIT 20"
        ).fetchall()

        conn.close()

        jobs = []
        for r in top:
            j = dict(r)
            j["match_details"] = json.loads(j.get("match_details", "{}"))
            jobs.append(j)

        return render_template("dashboard.html",
            total=total, applied=applied, avg_score=round(avg_score, 2),
            boards=[dict(b) for b in boards], jobs=jobs)

    @app.route("/jobs")
    def jobs_list():
        """Paginated, filterable job list."""
        page = int(request.args.get("page", 1))
        per_page = 25
        offset = (page - 1) * per_page
        board_filter = request.args.get("board", "")
        min_score = float(request.args.get("min_score", 0))
        search = request.args.get("q", "")
        sort = request.args.get("sort", "score")  # score, date, company

        conn = get_db()
        where = ["hidden = 0"]
        params = []
        if board_filter:
            where.append("board = ?")
            params.append(board_filter)
        if min_score > 0:
            where.append("match_score >= ?")
            params.append(min_score)
        if search:
            where.append("(title LIKE ? OR company LIKE ? OR description LIKE ?)")
            params.extend([f"%{search}%"] * 3)

        where_sql = " AND ".join(where)

        order_map = {
            "score": "match_score DESC, date_posted DESC",
            "date": "date_posted DESC, match_score DESC",
            "company": "company ASC, match_score DESC",
            "title": "title ASC, match_score DESC",
        }
        order_sql = order_map.get(sort, "match_score DESC, date_posted DESC")

        total = conn.execute(f"SELECT COUNT(*) FROM jobs WHERE {where_sql}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM jobs WHERE {where_sql} ORDER BY {order_sql} LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()
        conn.close()

        jobs = []
        for r in rows:
            j = dict(r)
            j["match_details"] = json.loads(j.get("match_details", "{}"))
            jobs.append(j)

        total_pages = (total + per_page - 1) // per_page

        return render_template("jobs.html",
            jobs=jobs, page=page, total_pages=total_pages, total=total,
            board_filter=board_filter, min_score=min_score, search=search, sort=sort,
            boards=[b.value for b in JobBoard])

    @app.route("/job/<path:url>")
    def job_detail(url):
        """Show single job details."""
        conn = get_db()
        row = conn.execute("SELECT * FROM jobs WHERE url = ?", (url,)).fetchone()
        conn.close()
        if not row:
            return "Job not found", 404
        job = dict(row)
        job["match_details"] = json.loads(job.get("match_details", "{}"))
        return render_template("job_detail.html", job=job)

    @app.route("/api/scrape", methods=["POST"])
    def api_scrape():
        """Trigger a scrape via the API."""
        data = request.json or {}
        boards = data.get("boards", [])
        max_results = data.get("max_results", 30)
        keywords = data.get("keywords", "")

        def run_scrape():
            profile = load_profile()
            matcher = JobMatcher(profile)
            all_jobs = []

            if keywords:
                queries = [SearchQuery(
                    keywords=keywords,
                    location=data.get("location", ""),
                    remote=data.get("remote", True),
                    max_age_days=14,
                    boards=[JobBoard(b) for b in boards] if boards else [
                        JobBoard(b) for b in profile.get("search", {}).get("boards", ["remotive"])
                    ],
                )]
            else:
                search = profile.get("search", {})
                board_list = [JobBoard(b) for b in boards] if boards else [
                    JobBoard(b) for b in search.get("boards", ["remotive"])
                ]
                queries = []
                for kw in search.get("queries", ["machine learning engineer"])[:3]:
                    for loc in search.get("locations", [""])[:3]:
                        queries.append(SearchQuery(
                            keywords=kw, location=loc, remote=search.get("remote", True),
                            max_age_days=search.get("max_age_days", 14), boards=board_list,
                        ))

            for query in queries:
                for board in query.boards:
                    scraper_cls = SCRAPERS.get(board.value)
                    if not scraper_cls:
                        continue
                    try:
                        scraper = scraper_cls()
                        jobs = scraper.scrape(query, max_results=max_results)
                        all_jobs.extend(jobs)
                    except Exception as e:
                        logger.error(f"Scrape error ({board.value}): {e}")

            # Deduplicate
            seen = set()
            unique = []
            for j in all_jobs:
                if j.url not in seen:
                    seen.add(j.url)
                    unique.append(j)

            ranked = matcher.rank(unique)
            save_jobs(ranked)

        thread = threading.Thread(target=run_scrape)
        thread.start()

        return jsonify({"status": "started", "message": "Scraping in background..."})

    @app.route("/api/rescore", methods=["POST"])
    def api_rescore():
        """Re-score all jobs."""
        profile = load_profile()
        matcher = JobMatcher(profile)
        conn = get_db()
        rows = conn.execute("SELECT * FROM jobs WHERE hidden = 0").fetchall()
        conn.close()

        jobs = []
        for r in rows:
            jobs.append(Job(
                title=r["title"], company=r["company"], location=r["location"],
                url=r["url"], board=JobBoard(r["board"]),
                description=r["description"] or "", salary=r["salary"] or "",
            ))
        ranked = matcher.rank(jobs)
        update_scores(ranked)
        return jsonify({"status": "ok", "rescored": len(ranked)})

    @app.route("/api/job/apply", methods=["POST"])
    def api_apply():
        url = request.json.get("url", "")
        if url:
            mark_applied(url)
        return jsonify({"status": "ok"})

    @app.route("/api/job/hide", methods=["POST"])
    def api_hide():
        url = request.json.get("url", "")
        if url:
            mark_hidden(url)
        return jsonify({"status": "ok"})

    @app.route("/api/stats")
    def api_stats():
        conn = get_db()
        total = conn.execute("SELECT COUNT(*) FROM jobs WHERE hidden = 0").fetchone()[0]
        applied = conn.execute("SELECT COUNT(*) FROM jobs WHERE applied = 1").fetchone()[0]
        by_board = conn.execute(
            "SELECT board, COUNT(*) as cnt FROM jobs WHERE hidden = 0 GROUP BY board"
        ).fetchall()
        by_score = conn.execute(
            "SELECT CASE WHEN match_score >= 0.7 THEN 'excellent' "
            "WHEN match_score >= 0.4 THEN 'good' "
            "WHEN match_score >= 0.2 THEN 'fair' "
            "ELSE 'low' END as tier, COUNT(*) as cnt "
            "FROM jobs WHERE hidden = 0 GROUP BY tier"
        ).fetchall()
        conn.close()
        return jsonify({
            "total": total, "applied": applied,
            "by_board": {r["board"]: r["cnt"] for r in by_board},
            "by_score": {r["tier"]: r["cnt"] for r in by_score},
        })

    return app

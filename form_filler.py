"""Application form auto-filler using Chrome MCP.

This module prepares form-filling instructions for the Chrome MCP tools.
It maps pre-generated answers to form fields and provides a structured
workflow for auto-filling application forms with user review before submit.

NOTE: Chrome MCP tools (navigate, read_page, form_input, file_upload) are
only available within a Claude agent session. This module generates the
fill instructions; the actual MCP calls are made by the agent.
"""

import json
import logging
from typing import Dict, List, Optional

from storage import get_application_by_job

logger = logging.getLogger(__name__)

# Common field name patterns and what answer to map them to
FIELD_MAPPINGS = {
    # Name fields
    "first_name": "Ahmed",
    "last_name": "Tawfik Aboukhadra",
    "full_name": "Ahmed Tawfik Aboukhadra",
    "name": "Ahmed Tawfik Aboukhadra",

    # Contact
    "email": "ahmed.tawfik96@gmail.com",
    "phone": "",  # User should fill
    "linkedin": "https://www.linkedin.com/in/ahmed-tawfik-aboukhadra/",
    "github": "https://github.com/ATAboukhadra",
    "website": "https://ataboukhadra.github.io/",
    "portfolio": "https://ataboukhadra.github.io/",

    # Location
    "city": "Kaiserslautern",
    "country": "Germany",
    "address": "Kaiserslautern, Germany",
    "location": "Kaiserslautern, Germany",

    # Education
    "degree": "PhD in Computer Science (expected 2026)",
    "university": "RPTU Kaiserslautern-Landau",
    "school": "RPTU Kaiserslautern-Landau",
    "education": "PhD Computer Science, RPTU Kaiserslautern (2021-Present); MSc AI, Maastricht University (2019-2021); BSc CS&E, German University in Cairo (2014-2019)",
    "gpa": "8.33/10 (MSc), 1.06/A (BSc)",

    # Work
    "current_company": "DFKI - German Research Center for AI",
    "current_title": "Researcher - Computer Vision & 3D Reconstruction",
    "years_experience": "5+",
    "experience": "5+ years in computer vision and deep learning research",
}


def get_fill_instructions(job_url: str) -> Optional[Dict]:
    """Get auto-fill instructions for a job application.

    Returns a dict with:
    - static_fields: field name -> value (always the same)
    - dynamic_fields: question -> answer (from pre-generated form answers)
    - cv_pdf_path: path to customized CV for upload
    - cover_letter_pdf_path: path to cover letter for upload
    - application_url: the job URL to navigate to
    """
    app = get_application_by_job(job_url)
    if not app:
        logger.warning("No application found for %s", job_url)
        return None

    # Parse form answers
    answers = {}
    try:
        answers = json.loads(app.get("form_answers_json", "{}"))
    except json.JSONDecodeError:
        pass

    return {
        "application_url": job_url,
        "static_fields": FIELD_MAPPINGS.copy(),
        "dynamic_fields": answers,
        "cv_pdf_path": app.get("cv_pdf_path", ""),
        "cover_letter_pdf_path": app.get("cover_letter_pdf_path", ""),
        "status": app.get("status", "unknown"),
        "slug": app.get("slug", ""),
    }


def format_fill_guide(instructions: Dict) -> str:
    """Format fill instructions as a human-readable guide for copy-paste."""
    lines = []
    lines.append("=" * 60)
    lines.append("APPLICATION FILL GUIDE")
    lines.append("=" * 60)
    lines.append(f"\nJob URL: {instructions['application_url']}")
    lines.append(f"CV PDF: {instructions['cv_pdf_path']}")
    lines.append(f"Cover Letter: {instructions['cover_letter_pdf_path']}")

    lines.append("\n--- STATIC FIELDS ---")
    for field, value in instructions["static_fields"].items():
        if value:
            lines.append(f"  {field}: {value}")

    lines.append("\n--- APPLICATION QUESTIONS ---")
    for question, answer in instructions["dynamic_fields"].items():
        lines.append(f"\n  Q: {question}")
        lines.append(f"  A: {answer}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)

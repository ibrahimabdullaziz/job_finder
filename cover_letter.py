"""Automated cover letter generator.

Uses the pupil-labs cover letter as a structural template.
LLM generates body paragraphs; LaTeX wrapper is hardcoded.
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional

from llm import generate_latex, check_ollama_available

logger = logging.getLogger(__name__)

# LaTeX template — header/footer are fixed, only body paragraphs change
COVER_LETTER_TEMPLATE = r"""%% Cover Letter — {company} — {role_title}
\documentclass[a4paper,11pt]{{article}}

\usepackage[T1]{{fontenc}}
\usepackage[p,osf,swashQ]{{cochineal}}
\usepackage{{cabin}}
\usepackage[varqu,varl,scale=0.9]{{zi4}}
\usepackage[a4paper,hmargin=2.5cm,top=2.2cm,bottom=2.5cm]{{geometry}}
\usepackage[dvipsnames,svgnames]{{xcolor}}
\usepackage{{hyperref}}
\usepackage{{microtype}}
\usepackage{{parskip}}
\usepackage[fixed]{{fontawesome5}}

\definecolor{{AccentColour}}{{HTML}}{{88AC0B}}
\definecolor{{MarkerColour}}{{HTML}}{{B6073F}}

\hypersetup{{colorlinks=true,allcolors=MarkerColour,breaklinks=true}}

\pagestyle{{empty}}

\newcommand{{\infoitem}}[2]{{\makebox[1.5em]{{\color{{MarkerColour!80!black}}#1}}\,#2}}

\begin{{document}}

%% ---- Header ---------------------------------------------------------------
{{\sffamily\bfseries\LARGE Ahmed Tawfik Aboukhadra}}\\[4pt]
\infoitem{{\faEnvelope[regular]}}{{\href{{mailto:ahmed.tawfik96@gmail.com}}{{\texttt{{ahmed.tawfik96@gmail.com}}}}}}\quad
\infoitem{{\faLinkedin}}{{\href{{https://www.linkedin.com/in/ahmed-tawfik-aboukhadra/}}{{\texttt{{ahmed-tawfik-aboukhadra}}}}}}\quad
\infoitem{{\faGithub}}{{\href{{https://github.com/ATAboukhadra}}{{\texttt{{ATAboukhadra}}}}}}\quad
\infoitem{{\faGlobe}}{{\href{{https://ataboukhadra.github.io/}}{{\texttt{{ataboukhadra.github.io}}}}}}

{{\color{{AccentColour}}\rule{{\linewidth}}{{2.5pt}}}}
\vspace{{1em}}

%% ---- Date & Recipient ------------------------------------------------------
\today

\medskip
\textbf{{{company}}}\\
{location}

\medskip

\textbf{{Re: {role_title_escaped}}}

\bigskip

%% ---- Body ------------------------------------------------------------------
{body}

\bigskip

Sincerely,\\[2em]
\textbf{{Ahmed Tawfik Aboukhadra}}

\end{{document}}
"""


def _escape_latex(text: str) -> str:
    """Escape special LaTeX characters in plain text."""
    replacements = [
        ('&', r'\&'),
        ('%', r'\%'),
        ('#', r'\#'),
        ('_', r'\_'),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def generate_cover_letter_body(
    life_story: str,
    job_analysis: Dict,
    title: str,
    company: str,
    description: str,
    model: str = "qwen3.5:9b",
) -> str:
    """Generate cover letter body paragraphs using LLM."""

    system = """You are writing a cover letter for Ahmed Tawfik Aboukhadra, a Computer Vision PhD candidate
at RPTU Kaiserslautern and Researcher at DFKI Augmented Vision.

Write in first person. Be specific and technical — reference actual projects, metrics, and technologies.
Do NOT be generic. Every paragraph should connect Ahmed's specific work to the specific role.
Output LaTeX-formatted text (use \\textbf{} for emphasis, \\& for ampersand).
Do NOT include \\begin{document} or any preamble — only the body paragraphs.
Do NOT include "Dear..." salutation or "Sincerely" closing — those are handled by the template."""

    prompt = f"""Write 4 cover letter body paragraphs for this application.

TARGET ROLE: {title} at {company}
DOMAIN: {job_analysis.get('domain', 'general_ml')}
KEY TECHNOLOGIES: {', '.join(job_analysis.get('key_technologies', []))}
FOCUS AREAS: {', '.join(job_analysis.get('focus_areas', []))}
COMPANY MISSION: {job_analysis.get('company_mission', 'Not specified')}

JOB DESCRIPTION (excerpt):
{description[:2000]}

AHMED'S FULL BACKGROUND:
{life_story[:5000]}

PARAGRAPH STRUCTURE:
1. Opening (2-3 sentences): Direct connection between Ahmed's work and this specific role. Mention the role title. Show genuine excitement about the company's specific mission.
2. Main achievement (4-5 sentences): Detail the most relevant project (usually GHOST for vision roles). Include specific metrics (13x speed-up, 1st Place). Reference specific technologies that overlap with the job requirements.
3. Secondary expertise (3-4 sentences): Highlight other relevant work. Connect to additional job requirements.
4. Closing (2-3 sentences): Express readiness to transition from academia to industry (or contribute to research). Reference portfolio at ataboukhadra.github.io.

Start with "Dear {company} Team," on the first line."""

    body = generate_latex(prompt, system=system, model=model, max_tokens=2500)

    # Basic cleanup
    body = body.strip()
    if body.startswith("```"):
        lines = body.split("\n")
        body = "\n".join(l for l in lines if not l.strip().startswith("```"))

    return body


def create_cover_letter(
    app_dir: str,
    title: str,
    company: str,
    location: str,
    description: str,
    life_story: str,
    job_analysis: Dict,
    model: str = "qwen3.5:9b",
) -> Optional[str]:
    """Generate and compile a cover letter. Returns PDF path or None."""

    if not check_ollama_available():
        logger.error("Ollama not available")
        return None

    logger.info("Generating cover letter for %s at %s...", title, company)

    # Generate body
    body = generate_cover_letter_body(
        life_story=life_story,
        job_analysis=job_analysis,
        title=title,
        company=company,
        description=description,
        model=model,
    )

    if not body:
        logger.error("Failed to generate cover letter body")
        return None

    # Escape role title for LaTeX Re: line
    role_title_escaped = _escape_latex(title)

    # Fill template
    tex_content = COVER_LETTER_TEMPLATE.format(
        company=_escape_latex(company),
        location=_escape_latex(location),
        role_title=title,
        role_title_escaped=role_title_escaped,
        body=body,
    )

    # Write and compile
    app_path = Path(app_dir)
    tex_file = app_path / "cover-letter.tex"
    tex_file.write_text(tex_content, encoding="utf-8")

    try:
        result = subprocess.run(
            ["latexmk", "-pdf", "-interaction=nonstopmode", "cover-letter.tex"],
            cwd=str(app_path),
            capture_output=True,
            text=True,
            timeout=120,
        )

        pdf_path = app_path / "cover-letter.pdf"
        if pdf_path.exists():
            # Clean aux files
            for ext in [".aux", ".fdb_latexmk", ".fls", ".log", ".out", ".synctex.gz"]:
                aux = app_path / ("cover-letter" + ext)
                if aux.exists():
                    aux.unlink()
            logger.info("Cover letter generated: %s", pdf_path)
            return str(pdf_path)
        else:
            logger.error("Cover letter PDF not generated. Errors:\n%s", result.stderr[-1000:])
            return None
    except subprocess.TimeoutExpired:
        logger.error("Cover letter compilation timed out")
        return None
    except FileNotFoundError:
        logger.error("latexmk not found")
        return None

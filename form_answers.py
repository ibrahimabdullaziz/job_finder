"""Application form answer pre-generator.

Generates answers to common ATS questions for each job application.
Answers are stored as JSON for copy-paste or auto-fill.
"""

import logging
from typing import Dict, Optional

from llm import generate_structured, check_ollama_available

logger = logging.getLogger(__name__)

STANDARD_QUESTIONS = [
    "Why do you want to work at {company}?",
    "What are your greatest strengths?",
    "Describe a challenging technical project you worked on.",
    "Why are you leaving your current position?",
    "Where do you see yourself in 5 years?",
    "Tell us about yourself (elevator pitch).",
    "What is your experience with {tech}?",
    "What is your expected salary?",
    "What is your earliest start date?",
    "Do you require visa sponsorship?",
]


def generate_form_answers(
    life_story: str,
    title: str,
    company: str,
    description: str,
    job_analysis: Dict,
    model: str = "qwen3.5:9b",
) -> Dict[str, str]:
    """Generate answers to common application form questions.

    Returns dict mapping question -> answer.
    """
    if not check_ollama_available():
        logger.error("Ollama not available")
        return {}

    key_tech = ", ".join(job_analysis.get("key_technologies", [])[:3])

    # Build the questions with company/tech filled in
    questions = []
    for q in STANDARD_QUESTIONS:
        q = q.replace("{company}", company)
        q = q.replace("{tech}", key_tech or "the technologies in this role")
        questions.append(q)

    questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    prompt = f"""Generate answers to these job application form questions for Ahmed Tawfik Aboukhadra.

ROLE: {title} at {company}
DOMAIN: {job_analysis.get('domain', 'general_ml')}
KEY TECHNOLOGIES: {key_tech}
COMPANY MISSION: {job_analysis.get('company_mission', '')}

JOB DESCRIPTION (excerpt):
{description[:1500]}

AHMED'S BACKGROUND:
{life_story[:4000]}

QUESTIONS:
{questions_text}

RULES:
- Each answer should be 2-4 sentences, professional but genuine
- Reference specific projects, metrics, and technologies from Ahmed's background
- For salary: say "I'm open to discussing compensation based on the full package and role scope. My expectation is aligned with market rates for senior ML/CV roles in [location]."
- For visa: "I currently hold a German residence permit for research purposes. I may need employer support for a work visa transition depending on the country, but this is typically straightforward."
- For start date: "I can start within 2-3 months, allowing time to complete my current commitments at DFKI."
- For "leaving current position": Frame as natural transition from PhD/research to industry impact

Return a JSON object where keys are the question numbers (as strings "1" through "10") and values are the answer strings.
"""

    result = generate_structured(prompt, model=model, max_tokens=3000)

    if not result:
        return {}

    # Map back to question text
    answers = {}
    for i, q in enumerate(questions):
        key = str(i + 1)
        if key in result:
            answers[q] = result[key]

    logger.info("Generated %d form answers for %s at %s", len(answers), title, company)
    return answers

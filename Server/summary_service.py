"""
summary_service.py
==================
AI Coach "Give Summary" Service Layer.

Implements the Compressed Injection Pattern: reads the pre-calculated
AnalyticsSummaryResponse Pydantic model from the in-memory cache, converts
its metrics into a compact JSON string, and injects it into an engineered
prompt template sent to the Gemini model via the OpenAI-compatible API.
"""

from __future__ import annotations

import logging
import os

from openai import AsyncOpenAI

try:
    from .data_transformer import AnalyticsSummaryResponse
except ImportError:
    from data_transformer import AnalyticsSummaryResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM Client Configuration
# ---------------------------------------------------------------------------
# Uses the OpenAI SDK pointed at Google's Gemini-compatible endpoint.
# Requires GOOGLE_API_KEY and GOOGLE_BASE_URL environment variables.

_MODEL_NAME: str = "gemini-3.5-flash"



def _get_client() -> AsyncOpenAI:
    """Lazy-initialise the async OpenAI-compatible client."""
    return AsyncOpenAI(
        api_key=os.getenv("GOOGLE_API_KEY"),
        base_url=os.getenv("GOOGLE_BASE_URL"),
    )


# ---------------------------------------------------------------------------
# Prompt Template
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an elite, world-class Competitive Programming Coach. Your job is to \
analyze a student's pre-calculated performance metrics and compile an incisive, \
highly personalized diagnostic executive summary. 

Do not repeat raw numbers or percentages back to the user point-blank. Instead, \
translate what those numbers reveal about their coding behaviors, cognitive \
blocks, and implementation style.\
"""

_USER_PROMPT_TEMPLATE = """\
### THE STUDENT TELEMETRY DATA (JSON):
{analytics_json}

### OUTPUT FORMAT REQUIREMENTS:
Generate a beautifully formatted Markdown response divided into exactly three \
distinct sections with the specified headings. Keep the tone professional, \
direct, analytical, and encouraging yet firm.

### SECTION INSTRUCTIONS:

## 🤖 Coach's Diagnostic Summary

### 1. Executive Position Analysis
Assess their competitive programming equilibrium using their 'current_rating', \
'max_rating', and platform 'rank'. Look at their 'overall_acceptance_rate'. \
A low acceptance rate (e.g., under 45%) with many submissions points to a \
reckless "submit-and-pray" habit. A high acceptance rate with static ratings \
suggests over-cautiousness. Provide a razor-sharp assessment of their mental \
pacing.

### 2. Primary Bottleneck & Code Failure Analysis
Examine their highest-ranked 'weak_tags' alongside their 'top_issue_verdict' \
(e.g., TIME_LIMIT_EXCEEDED, WRONG_ANSWER, RUNTIME_ERROR). Explain the precise \
conceptual or structural programming mistakes causing this exact combination. 
- If 'TIME_LIMIT_EXCEEDED' is paired with topics like graphs/dp, call out poor \
time complexity awareness, accidental nested loops, or failure to use efficient \
data structures like Adjacency Lists.
- If 'WRONG_ANSWER' dominates, highlight poor edge-case tracking, lack of \
dry-running inputs, or weak mathematical invariant handling.

### 3. The 2D Skill Reality Check
Scan the 'weak_tags' and 'strong_tags' arrays for any item marked with the \
status flag `"status": "under_explored_needs_depth"`. 
If found, issue a critical reality check. Explicitly warn them that their low \
failure index on this topic is an illusion of mastery caused by a low problem \
count (sample size bias). Tell them exactly what kind of advanced sub-topics or \
harder rating tiers they need to tackle to genuinely stress-test their skills \
in that category.\
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_coach_summary(analytics_data: AnalyticsSummaryResponse) -> str:
    """
    Generate a personalised AI Coach diagnostic summary.

    Parameters
    ----------
    analytics_data:
        The fully processed AnalyticsSummaryResponse pulled from SERVER_CACHE.

    Returns
    -------
    str
        Markdown-formatted coaching summary from the LLM.

    Raises
    ------
    Exception
        Propagated from the OpenAI client if the API call fails.
    """
    # Safely serialise the Pydantic model to a clean JSON string.
    analytics_json: str = analytics_data.model_dump_json(indent=2)

    user_prompt = _USER_PROMPT_TEMPLATE.format(analytics_json=analytics_json)

    client = _get_client()

    logger.info("Sending AI Coach prompt to model '%s'.", _MODEL_NAME)

    response = await client.chat.completions.create(
        model=_MODEL_NAME,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
    )

    summary_text: str = response.choices[0].message.content or ""

    logger.info(
        "AI Coach summary generated successfully (%d chars).", len(summary_text)
    )

    return summary_text

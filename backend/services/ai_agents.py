"""LLM tutor / NPC / scenario generation.  OWNER: Person 1 (GenAI).

The contract the backend depends on is `generate(...) -> (text, source)`
where source is 'ai' or 'authored-fallback'. Swap the internals for
LangGraph, a supervisor + sub-agents, a different provider -- anything --
as long as that tuple and the never-raise behaviour hold.

Never-raise is load-bearing: a provider outage must degrade to authored
content, not a 500.
"""
import json

from openai import AsyncOpenAI

from ..config import openai_key, openai_model

SYSTEM_PREAMBLE = (
    'You are a friendly Mars colony science tutor for ages 10-14. '
    'Stay within the supplied science facts. Use at most 80 words. '
    'Never ask for personal information. '
)


async def generate(instruction: str, context: dict, fallback: str) -> tuple[str, str]:
    if not openai_key():
        return fallback, 'authored-fallback'
    try:
        async with AsyncOpenAI(timeout=18, max_retries=0) as client:
            response = await client.responses.create(
                model=openai_model(),
                instructions=SYSTEM_PREAMBLE + instruction,
                # `context` must never contain student_id or any PII.
                input=json.dumps(context),
                max_output_tokens=220,
                store=False,
            )
            if response.output_text and response.output_text.strip():
                return response.output_text.strip(), 'ai'
    except Exception:
        # Do not expose credentials, upstream error bodies, or student data.
        pass
    return fallback, 'authored-fallback'

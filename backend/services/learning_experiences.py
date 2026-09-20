"""Generate safe presentation content for the three chapter experience formats.

The model supplies narration and scene beats only. Tested browser renderers own
the animation and game mechanics, so generated text can never execute as code.
"""
import os

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field


FORMATS = ('animated', 'mini_game', 'simulation')
MODEL_ENV = {
    'animated': 'GROQ_ANIMATED_MODEL',
    'mini_game': 'GROQ_MINIGAME_MODEL',
    'simulation': 'GROQ_SIMULATION_MODEL',
}


class ExperienceDraft(BaseModel):
    title: str = Field(min_length=3, max_length=80)
    narration: str = Field(min_length=10, max_length=400)
    beats: list[str] = Field(min_length=3, max_length=5)


FALLBACKS = {
    'M001': {
        'title': 'Rover Force Rescue',
        'narration': 'Help a stranded rover move safely by balancing its mass, acceleration, and net force.',
        'beats': ['Inspect the rover mass.', 'Choose a safe acceleration.', 'Apply F = m × a.', 'Launch the rover and observe its motion.'],
    },
    'M002': {
        'title': 'Mirror Signal Rescue',
        'narration': 'Redirect a light signal through the colony by using reflection and the normal line.',
        'beats': ['Aim the incident ray.', 'Measure from the normal.', 'Match the reflected angle.', 'Send the signal to the receiver.'],
    },
    'M003': {
        'title': 'Outpost Power Shift',
        'narration': 'Keep the outpost running by connecting power, operating time, and total energy use.',
        'beats': ['Read the device power.', 'Choose the running time.', 'Calculate E = P × t.', 'Check the outpost energy budget.'],
    },
}


async def generate(mission_id: str, format_name: str, lesson: dict, context: list[str]) -> dict:
    if format_name not in FORMATS:
        raise ValueError('Unknown learning experience format')
    fallback = FALLBACKS[mission_id]
    model = os.getenv(MODEL_ENV[format_name], os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b'))
    result = {**fallback, 'format': format_name, 'source': 'authored-fallback', 'model': model}
    if not os.getenv('GROQ_API_KEY'):
        return result

    prompts = {
        'animated': 'Write a 30-60 second animated explainer storyboard.',
        'mini_game': 'Write a short briefing for a playable educational mini-game.',
        'simulation': 'Write a guided mission simulation with clear decision moments.',
    }
    try:
        llm = ChatGroq(model=model, api_key=os.getenv('GROQ_API_KEY'), temperature=0.6)
        draft = await llm.with_structured_output(ExperienceDraft).ainvoke([
            ('system', 'You design concise Grade 9 science learning experiences for a Mars game. Use only the supplied approved facts. Never provide quiz answers, HTML, code, or unsafe instructions.'),
            ('human', f"{prompts[format_name]}\nChapter: {lesson['title']}\nLesson: {lesson['lesson']}\nApproved curriculum context:\n" + '\n'.join(context[:3])),
        ])
        return {**draft.model_dump(), 'format': format_name, 'source': 'ai', 'model': model}
    except Exception:
        return result

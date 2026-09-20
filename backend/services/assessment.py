"""Grading, performance signals, misconception analysis, and assessment results.
OWNER: Person 5 (Assessment).
"""
from dataclasses import dataclass
from typing import Optional

WRONG_ANSWER_FEEDBACK = (
    'Not quite. Check the relationship between the quantities, then try again.'
)

# Known misconception mapping per question distractor (if reliably inferrable)
MISCONCEPTION_MAP = {
    "Q001": {
        "A": ("divided_mass_by_acceleration", "It looks like you divided mass by acceleration (500 / 4) instead of multiplying. F = m × a."),
        "B": ("added_mass_and_acceleration", "It looks like you added mass and acceleration (500 + 4) instead of multiplying. F = m × a."),
        "D": ("squared_or_overmultiplied", "Your result is far too large. Double check your calculation for F = m × a (500 × 4)."),
    },
    "Q002": {
        "A": ("divided_power_by_time", "It looks like you divided power by time (200 / 5) instead of multiplying power by time. E = P × t."),
        "C": ("added_power_and_time", "It looks like you added power and time (200 + 5) instead of multiplying. E = P × t."),
    },
    "Q003": {
        "A": ("confused_inputs_with_outputs", "Oxygen and glucose are outputs (products) of photosynthesis, not inputs."),
        "B": ("missing_carbon_dioxide", "Photosynthesis requires carbon dioxide, water, and light energy to produce sugar."),
        "D": ("confused_cellular_respiration", "Plants absorb carbon dioxide and water using light energy for photosynthesis."),
    },
}


@dataclass
class AssessmentResult:
    correct: bool
    question_id: str
    mission_id: str
    context: str
    objective_id: Optional[str]
    difficulty: int
    time_taken: float
    hints_used: int
    performance_factor: float
    evidence_score: float
    misconception: Optional[str]
    feedback: str


def grade(question: dict, answer: str) -> bool:
    return answer == question['answer']


def feedback(question: dict, correct: bool) -> str:
    return question['explanation'] if correct else WRONG_ANSWER_FEEDBACK


def infer_misconception(question_id: str, selected_answer: str) -> tuple[Optional[str], Optional[str]]:
    """Return (misconception_code, custom_feedback) if a known distractor misconception matches."""
    q_map = MISCONCEPTION_MAP.get(question_id, {})
    if selected_answer in q_map:
        return q_map[selected_answer]
    return None, None


def evaluate_assessment(
    question: dict,
    answer: str,
    time_taken: float,
    hints_used: int,
    context: str = 'numerical',
    mission_id: str = 'M001',
) -> AssessmentResult:
    """Evaluate student performance, calculate assessment signals, infer misconceptions,
    and package a structured assessment result for Adaptive Learning (Person 2).
    """
    correct = grade(question, answer)
    question_id = question.get('question_id', 'unknown')
    difficulty = question.get('difficulty', 1)
    objective_id = question.get('objective_id') or question.get('concept')

    # Performance factor based on time efficiency and hint reliance
    expected_time = 30.0 + (difficulty - 1) * 10.0
    if correct:
        time_efficiency = 1.0 if time_taken <= expected_time else max(0.6, 1.0 - (time_taken - expected_time) * 0.005)
        hint_penalty = 0.15 * hints_used
        performance_factor = max(0.5, round(time_efficiency - hint_penalty, 3))
    else:
        performance_factor = 0.0

    # Evidence score quantifying demonstrated mastery evidence for this interaction
    if correct:
        difficulty_weight = 0.8 + (difficulty - 1) * 0.05
        evidence_score = min(1.0, max(0.6, difficulty_weight - 0.15 * hints_used))
    else:
        evidence_score = max(0.0, 0.2 - (difficulty - 1) * 0.025)

    # Diagnostic misconception identification
    misconception = None
    if not correct:
        misconception, diagnostic_msg = infer_misconception(question_id, answer)
        diag_feedback = diagnostic_msg if diagnostic_msg else WRONG_ANSWER_FEEDBACK
    else:
        diag_feedback = question.get('explanation', 'Correct!')

    return AssessmentResult(
        correct=correct,
        question_id=question_id,
        mission_id=mission_id,
        context=context,
        objective_id=objective_id,
        difficulty=difficulty,
        time_taken=time_taken,
        hints_used=hints_used,
        performance_factor=performance_factor,
        evidence_score=evidence_score,
        misconception=misconception,
        feedback=diag_feedback,
    )


def validate_question(question: dict) -> tuple[bool, str]:
    """Check an LLM-generated question before it reaches a student.
    Person 5 implements: objective match, answer check, arithmetic, difficulty.
    """
    raise NotImplementedError('Person 5: generated-question validation')


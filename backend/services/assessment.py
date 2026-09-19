"""Grading and answer validation.  OWNER: Person 5 (Assessment & Validation).

Currently a plain option-letter comparison. This is where deterministic
numeric checking, reasoning analysis, misconception classification and
generated-question validation belong. Keep `grade()` returning a bool and
`feedback()` returning a string.
"""
WRONG_ANSWER_FEEDBACK = (
    'Not quite. Check the relationship between the quantities, then try again.'
)


def grade(question: dict, answer: str) -> bool:
    return answer == question['answer']


def feedback(question: dict, correct: bool) -> str:
    return question['explanation'] if correct else WRONG_ANSWER_FEEDBACK


def validate_question(question: dict) -> tuple[bool, str]:
    """Check an LLM-generated question before it reaches a student.
    Person 5 implements: objective match, answer check, arithmetic, difficulty.
    """
    raise NotImplementedError('Person 5: generated-question validation')

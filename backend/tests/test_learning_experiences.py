import asyncio

from backend.services import learning_experiences


LESSON = {
    'title': 'Forces and Motion',
    'lesson': 'Net force, mass and acceleration are linked by F = m × a.',
}


def test_all_experience_formats_have_safe_offline_content(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    for format_name in learning_experiences.FORMATS:
        result = asyncio.run(
            learning_experiences.generate('M001', format_name, LESSON, [])
        )
        assert result['format'] == format_name
        assert result['source'] == 'authored-fallback'
        assert len(result['beats']) >= 3


def test_each_format_can_select_its_own_model(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    monkeypatch.setenv('GROQ_MINIGAME_MODEL', 'test/fast-mini-game-model')
    result = asyncio.run(
        learning_experiences.generate('M001', 'mini_game', LESSON, [])
    )
    assert result['model'] == 'test/fast-mini-game-model'

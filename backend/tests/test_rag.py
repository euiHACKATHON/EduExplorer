"""Tests for Person 3's curriculum / knowledge-graph / retrieval module."""
import io

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.routers import rag as rag_router
from backend.services import curriculum
from backend.services.ai_agents import _contains_correct_answer
from backend.services.rag.chunking import (
    PDFError, chunk_text, chunks_from_curriculum, clean_text, extract_pdf_text,
)
from backend.services.rag.graph import KnowledgeGraph
from backend.services.rag.index import CurriculumIndex
from backend.services.rag.models import Curriculum, load_curriculum
from backend.services.rag.search import BM25, tokenize

client = TestClient(app)


@pytest.fixture(scope='module')
def cur():
    return load_curriculum()


@pytest.fixture()
def index(tmp_path):
    return CurriculumIndex(uploads_path=tmp_path / 'u.json', mode='bm25')


def _register(student_id):
    r = client.post('/auth/register', json=dict(
        student_id=student_id, display_name='Cadet', grade_level='9', password='testpass123'))
    assert r.status_code == 200, r.text
    return {'Authorization': f"Bearer {r.json()['access_token']}"}


# --- curriculum data ---------------------------------------------------------------
def test_curriculum_is_grade9_physics_with_light_and_motion(cur):
    assert cur.subject == 'Physics' and cur.grade == 9
    ids = {t.id for t in cur.topics}
    assert {'scalar-vector', 'speed-velocity', 'acceleration', 'plane-mirrors',
            'spherical-mirrors', 'lenses'} <= ids
    assert {u.title for u in cur.units} >= {'Forces and Motion'}


def test_every_topic_has_a_status_and_unconfirmed_ones_explain_why(cur):
    for t in cur.topics:
        assert t.status in ('core', 'supporting', 'unconfirmed')
        if t.status == 'unconfirmed':
            assert t.source_note, f'{t.id} is unconfirmed but has no source_note'


def test_unknown_prerequisite_is_rejected(cur):
    data = cur.model_dump()
    data['topics'][0]['prerequisites'] = ['does-not-exist']
    with pytest.raises(ValueError):
        Curriculum.model_validate(data)


def test_missions_map_to_topics(cur):
    assert [t.id for t in cur.topics_for_mission('M001')] == ['newton-second']
    assert [t.id for t in cur.topics_for_mission('M002')] == ['power-energy']
    assert cur.topics_for_mission('M003') == []  # biology: not in a physics curriculum


@pytest.mark.parametrize('mission_id', ['M001', 'M002', 'M003'])
def test_no_chunk_contains_a_graded_answer(cur, mission_id):
    """Retrieved text goes into LLM prompts. It must never contain the correct
    answer of any mission, judged by the team's own answer-leak guard."""
    raw = curriculum.challenge(mission_id)
    leaks = [c.id for c in chunks_from_curriculum(cur) if _contains_correct_answer(c.text, raw)]
    assert leaks == []


# --- knowledge graph -----------------------------------------------------------------
def test_learning_path_respects_prerequisites(cur):
    order = KnowledgeGraph(cur).learning_path()
    pos = {t: i for i, t in enumerate(order)}
    assert len(order) == len(cur.topics)
    for topic in cur.topics:
        for pre in topic.prerequisites:
            assert pos[pre] < pos[topic.id]


def test_transitive_prerequisites_and_unlocks(cur):
    g = KnowledgeGraph(cur)
    assert {'acceleration', 'speed-velocity', 'distance-displacement', 'scalar-vector',
            'force-basics', 'mass-weight'} <= set(g.prerequisites('newton-second', transitive=True))
    assert g.prerequisites('lenses') == ['light-refraction']
    assert 'newton-third' in g.unlocks('newton-second')
    assert 'F = ma' in g.concepts('newton-second')
    with pytest.raises(KeyError):
        g.prerequisites('nope')


def test_next_topics_only_returns_unlocked_ones(cur):
    g = KnowledgeGraph(cur)
    start = g.next_topics(set())
    assert 'scalar-vector' in start and 'distance-displacement' not in start
    assert 'distance-displacement' in g.next_topics({'scalar-vector'})
    assert 'optical-applications' not in g.next_topics({'lenses'})  # still needs spherical mirrors


def test_cycle_is_rejected(cur):
    data = cur.model_dump()
    by_id = {t['id']: t for t in data['topics']}
    by_id['scalar-vector']['prerequisites'] = ['distance-displacement']
    with pytest.raises(ValueError, match='cycle'):
        KnowledgeGraph(Curriculum.model_validate(data))


# --- chunking / cleaning -----------------------------------------------------------------
def test_chunk_text_respects_size_and_overlaps():
    sentence = 'Force is a push or a pull acting on an object.'
    chunks = chunk_text(' '.join([sentence] * 40), max_words=60)
    assert len(chunks) > 1
    assert all(len(c.split()) <= 60 + len(sentence.split()) for c in chunks)
    assert chunks[1].startswith(sentence)  # one-sentence overlap


def test_clean_text_joins_hyphenation_and_drops_page_numbers():
    cleaned = clean_text('accelera-\ntion is key\n\n12\n\nPage 13\nNext idea')
    assert 'acceleration is key' in cleaned
    assert '12' not in cleaned.split() and 'Page 13' not in cleaned


def test_pdf_validation():
    with pytest.raises(PDFError):
        extract_pdf_text(b'not a pdf')


# --- search ----------------------------------------------------------------------------------
def test_tokenizer_stems_and_drops_stopwords():
    assert tokenize('The rover accelerates quickly') == tokenize('rover accelerate quickly')
    assert 'the' not in tokenize('the mirror')


def test_bm25_prefers_documents_with_rare_matching_terms():
    docs = [tokenize(t) for t in ['force and mass', 'concave mirror focus', 'mirror image virtual']]
    scores = BM25(docs).scores(tokenize('concave mirror'))
    assert scores[1] > scores[2] > 0 and scores[0] == 0


@pytest.mark.parametrize('question, expected_topic', [
    ('Why does acceleration decrease when the mass increases?', 'newton-second'),
    ('What is the difference between mass and weight?', 'mass-weight'),
    ('How do I calculate energy from power and time in watt-hours?', 'power-energy'),
    ('Why do action and reaction forces not cancel out?', 'newton-third'),
    ('What is the difference between distance and displacement?', 'distance-displacement'),
    ('What is the difference between a scalar and a vector?', 'scalar-vector'),
    ('What is the difference between speed and velocity?', 'speed-velocity'),
    ('What are the laws of reflection?', 'light-reflection'),
    ('What is lateral inversion in a plane mirror?', 'plane-mirrors'),
    ('What image does a concave mirror form when the object is beyond the centre of curvature?', 'spherical-mirrors'),
    ('Why does a convex lens make a magnifying glass work?', 'lenses'),
    ('How is short sight corrected?', 'optical-applications'),
    ('Why does a straw look bent in water?', 'light-refraction'),
])
def test_retrieval_finds_the_right_topic(index, question, expected_topic):
    hits = index.search(question, k=3)
    assert hits, 'no results'
    assert expected_topic in [h.chunk.topic_id for h in hits], [h.chunk.topic_id for h in hits]


def test_topic_filter_nonsense_and_empty_query(index):
    hits = index.search('force', k=5, topic_id='friction')
    assert hits and all(h.chunk.topic_id == 'friction' for h in hits)
    assert index.search('   ') == []
    assert index.search('zzqx blorptastic') == []


def test_context_for_mission(index):
    ctx = index.context_for('M001', 'why does a heavier rover accelerate less?')
    assert 1 <= len(ctx) <= 3 and any('mass' in c.lower() for c in ctx)
    assert index.context_for('M001')  # works without a question
    assert index.context_for('M003') == []  # biology mission has no physics topic


def test_context_for_never_raises(monkeypatch):
    monkeypatch.setattr(curriculum, 'get_index', lambda: (_ for _ in ()).throw(RuntimeError('boom')))
    assert curriculum.context_for('M001', 'anything') == []


def test_upload_is_indexed_persisted_and_replaceable(tmp_path):
    path = tmp_path / 'u.json'
    idx = CurriculumIndex(uploads_path=path, mode='bm25')
    n = idx.add_upload('school.txt', 'Buoyancy is the upward force that a fluid exerts on a submerged object.\n\n'
                                     'Archimedes principle relates it to displaced fluid.')
    assert n == 2
    assert idx.search('upward force fluid buoyancy', k=1)[0].chunk.source == 'school.txt'
    again = CurriculumIndex(uploads_path=path, mode='bm25')  # reloads the saved upload
    assert again.search('buoyancy', k=1)[0].chunk.source == 'school.txt'
    idx.add_upload('school.txt', 'Only one short paragraph now about density and volume of materials.')
    assert sum(c.source == 'school.txt' for c in idx.all_chunks()) == 1


# --- HTTP API ----------------------------------------------------------------------------------
def test_api_objectives_topic_graph():
    body = client.get('/curriculum/objectives', params={'topic_id': 'newton-second'}).json()
    assert len(body['objectives']) == 4 and body['objectives'][0]['mission_ids'] == ['M001']
    assert body['grade'] == 9
    topic = client.get('/topic/newton-second').json()
    assert 'newton-third' in topic['unlocks'] and topic['status'] == 'unconfirmed'
    assert client.get('/topic/nope').status_code == 404
    graph = client.get('/curriculum/graph').json()
    assert graph['learning_path'][:4] == ['scalar-vector', 'distance-displacement', 'speed-velocity', 'acceleration']
    assert graph['edges'] and graph['nodes']


def test_api_rag_query_and_validation():
    r = client.post('/rag/query', json={'question': 'what is inertia?', 'k': 2})
    assert r.status_code == 200
    body = r.json()
    assert body['retrieval_backend'] == 'bm25'
    assert body['results'] and body['results'][0]['topic_id'] == 'newton-first'
    assert client.post('/rag/query', json={'question': 'x'}).status_code == 422
    assert client.post('/rag/query', json={'question': 'inertia?', 'topic_id': 'nope'}).status_code == 404


def test_upload_requires_auth_and_is_off_by_default():
    body = b'Density is mass per unit volume. It is measured in kg per cubic metre.'
    assert client.post('/curriculum/upload?filename=n.txt', content=body).status_code == 401
    h = _register('rag-upload-off')
    r = client.post('/curriculum/upload?filename=n.txt', content=body, headers=h)
    assert r.status_code == 403 and 'RAG_ALLOW_UPLOAD' in r.json()['detail']


def test_upload_rules_when_enabled(monkeypatch):
    monkeypatch.setenv('RAG_ALLOW_UPLOAD', '1')
    h = _register('rag-upload-on')
    ok = client.post('/curriculum/upload?filename=../../notes.txt', headers=h,
                     content=b'Density is mass per unit volume. It is measured in kg per cubic metre.')
    assert ok.status_code == 200 and ok.json() == {'filename': 'notes.txt', 'chunks_indexed': 1}
    assert client.post('/curriculum/upload?filename=x.exe', content=b'data', headers=h).status_code == 400
    assert client.post('/curriculum/upload?filename=x.pdf', content=b'hello', headers=h).status_code == 400
    monkeypatch.setattr(rag_router, 'MAX_UPLOAD_BYTES', 50)
    assert client.post('/curriculum/upload?filename=big.txt', content=b'a' * 100, headers=h).status_code == 413


def test_real_pdf_upload(monkeypatch):
    pytest.importorskip('pypdf')
    monkeypatch.setenv('RAG_ALLOW_UPLOAD', '1')
    lines = ['Buoyancy is the upward force exerted by a fluid on a submerged object.',
             'Archimedes principle says the buoyant force equals the weight of displaced fluid.']
    content = 'BT /F1 11 Tf 50 750 Td 16 TL ' + ' '.join(f'({t}) Tj T*' for t in lines) + ' ET'
    objs = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
            f'<< /Length {len(content)} >>\nstream\n{content}\nendstream',
            '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    pdf, offsets = b'%PDF-1.4\n', []
    for i, o in enumerate(objs, 1):
        offsets.append(len(pdf))
        pdf += f'{i} 0 obj\n{o}\nendobj\n'.encode()
    xref = len(pdf)
    pdf += f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n'.encode()
    pdf += ''.join(f'{o:010d} 00000 n \n' for o in offsets).encode()
    pdf += f'trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()
    h = _register('rag-pdf')
    r = client.post('/curriculum/upload?filename=buoyancy.pdf', content=pdf, headers=h)
    assert r.status_code == 200 and r.json()['chunks_indexed'] >= 1
    hit = client.post('/rag/query', json={'question': 'buoyant force displaced fluid', 'k': 1}).json()['results'][0]
    assert hit['source'] == 'buoyancy.pdf'


# --- integration with the tutor agent -------------------------------------------------------
def test_tutor_routes_receive_retrieved_context(monkeypatch):
    """/ai/explain and /ai/ask must hand curriculum passages to the agent graph."""
    from backend.agents.schemas import TutorResponse
    from backend.services import ai_agents

    captured = []

    async def fake_run_agent(state, thread_id):
        captured.append(state['retrieved_context'])
        return {'tutor_result': TutorResponse(message='ok', source='ai')}

    monkeypatch.setattr(ai_agents, 'run_agent', fake_run_agent)
    assert client.post('/ai/explain', json={'mission_id': 'M001'}).status_code == 200
    assert client.post('/ai/ask', json={'mission_id': 'M001', 'student_id': 's1',
                                        'message': 'why does mass matter?'}).status_code == 200
    assert client.post('/ai/explain', json={'mission_id': 'M003'}).status_code == 200
    assert captured[0] and captured[1]
    assert captured[2] == []  # biology mission: no physics context


# --- optional semantic search (tested with a stand-in model; the real one needs a download) ---
class _FakeModel:
    """Deterministic bag-of-words 'embedding' with the sentence-transformers encode() signature."""
    DIM = 256

    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False):
        import numpy as np

        out = np.zeros((len(texts), self.DIM), dtype='float32')
        for row, text in enumerate(texts):
            for tok in tokenize(text):
                out[row, hash(tok) % self.DIM] += 1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return out / norms


def test_hybrid_search_fuses_keyword_and_semantic_rankings(monkeypatch, tmp_path):
    pytest.importorskip('numpy')
    from backend.services.rag import search as search_module

    monkeypatch.setattr(search_module, '_load_model', lambda name: _FakeModel())
    idx = CurriculumIndex(uploads_path=tmp_path / 'u.json', mode='semantic')
    assert idx.backend == 'bm25+semantic'
    hits = idx.search('What image does a concave mirror form?', k=3)
    assert hits and hits[0].chunk.topic_id == 'spherical-mirrors'
    assert all(0 < h.score < 0.05 for h in hits)  # reciprocal-rank-fusion scale
    assert idx.context_for('M001', 'why does mass matter for acceleration?')


def test_semantic_mode_fails_loudly_but_auto_falls_back(monkeypatch, tmp_path):
    from backend.services.rag import search as search_module

    def broken(name):
        raise ImportError('no sentence-transformers')

    monkeypatch.setattr(search_module, '_load_model', broken)
    assert CurriculumIndex(uploads_path=tmp_path / 'a.json', mode='auto').backend == 'bm25'
    with pytest.raises(ImportError):
        CurriculumIndex(uploads_path=tmp_path / 'b.json', mode='semantic')

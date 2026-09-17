import os
import tempfile
os.environ['MARS_DB']=os.path.join(tempfile.mkdtemp(),'test.sqlite3')
os.environ['OPENAI_API_KEY']=''
from fastapi.testclient import TestClient
from backend.main import app
client=TestClient(app)


def test_assessment_and_progress():
    p=dict(student_id='test-cadet',mission_id='M001',question_id='Q001',answer='A',time_taken=18,hints_used=1)
    assert client.post('/assessment',json=p).json()['correct'] is False
    p['answer']='C'
    result=client.post('/assessment',json=p).json()
    assert result['correct'] is True and result['xp_earned']==85
    assert client.post('/assessment',json=p).json()['xp_earned']==0
    progress=client.get('/students/test-cadet/progress').json()
    assert progress['xp']==85 and progress['completed']==['M001']
    p['question_id']='wrong'
    assert client.post('/assessment',json=p).status_code==400


def test_validation_and_private_answer():
    q=client.get('/challenges/M001').json()
    assert 'answer' not in q and 'explanation' not in q
    assert client.get('/challenges/M999').status_code==404
    assert client.get('/ai/dialogue?npc_id=unknown').status_code==404
    assert client.post('/ai/hint',json=dict(mission_id='M001',question_id='Q001',student_id='test',level=4)).status_code==422


def test_ai_fallback():
    result=client.get('/ai/dialogue?npc_id=scientist_01').json()
    assert result['source']=='authored-fallback' and len(result['options'])==2
    result=client.post('/ai/hint',json=dict(mission_id='M002',question_id='Q002',student_id='test',level=2)).json()
    assert result['source']=='authored-fallback' and '200' in result['hint']

def test_generated_content_and_provider_failure(monkeypatch):
    from types import SimpleNamespace
    import backend.main as module
    monkeypatch.setenv('OPENAI_API_KEY','test-placeholder')
    captured={}
    class FakeClient:
        def __init__(self,**kwargs): self.responses=self
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def create(self,**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_text='Think of power as the speed of filling an energy tank.')
    monkeypatch.setattr(module,'AsyncOpenAI',FakeClient)
    result=client.post('/ai/explain',json={'mission_id':'M002'}).json()
    assert result['source']=='ai' and 'energy tank' in result['message']
    assert captured['store'] is False
    assert 'student_id' not in captured['input']
    class FailedClient(FakeClient):
        async def create(self,**kwargs): raise TimeoutError('provider unavailable')
    monkeypatch.setattr(module,'AsyncOpenAI',FailedClient)
    result=client.post('/ai/explain',json={'mission_id':'M002'}).json()
    assert result['source']=='authored-fallback' and 'watt-hours' in result['message']

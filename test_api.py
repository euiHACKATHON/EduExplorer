import os
import tempfile
os.environ['MARS_DB']=os.path.join(tempfile.mkdtemp(),'test.sqlite3')
os.environ['OPENAI_API_KEY']=''
os.environ['AUTH_SECRET']='test-secret-do-not-use-in-prod'
from fastapi.testclient import TestClient
from backend.main import app
client=TestClient(app)


def auth_header(student_id, password='testpass123', display_name='Cadet', grade_level='10'):
    r = client.post('/auth/register', json=dict(
        student_id=student_id, display_name=display_name,
        grade_level=grade_level, password=password,
    ))
    assert r.status_code == 200, r.text
    return {'Authorization': f"Bearer {r.json()['access_token']}"}


def test_assessment_and_progress():
    h=auth_header('test-cadet')
    p=dict(student_id='test-cadet',mission_id='M001',question_id='Q001',answer='A',time_taken=18,hints_used=1)
    assert client.post('/assessment',json=p,headers=h).json()['correct'] is False
    p['answer']='C'
    result=client.post('/assessment',json=p,headers=h).json()
    assert result['correct'] is True and result['xp_earned']==85
    assert client.post('/assessment',json=p,headers=h).json()['xp_earned']==0
    progress=client.get('/students/test-cadet/progress',headers=h).json()
    assert progress['xp']==85 and progress['completed']==['M001']
    p['question_id']='wrong'
    assert client.post('/assessment',json=p,headers=h).status_code==400


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
    import backend.services.ai_agents as module
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


def test_student_registration():
    r=client.post('/auth/register',json=dict(student_id='cadet-2',display_name='Robin',grade_level='10',password='testpass123'))
    assert r.status_code==200
    token=r.json()['access_token']
    me=client.get('/auth/me',headers={'Authorization':f'Bearer {token}'}).json()
    assert me['display_name']=='Robin'
    # Registration now creates an account, not a profile upsert -- the same
    # student_id twice is a conflict.
    r=client.post('/auth/register',json=dict(student_id='cadet-2',display_name='Robin R.',grade_level='10',password='testpass123'))
    assert r.status_code==409


def test_login_and_ownership():
    auth_header('cadet-login')
    assert client.post('/auth/login',json=dict(student_id='cadet-login',password='wrong')).status_code==401
    r=client.post('/auth/login',json=dict(student_id='cadet-login',password='testpass123'))
    assert r.status_code==200 and 'access_token' in r.json()
    # No token at all.
    assert client.get('/students/cadet-login/progress').status_code==401
    # Valid token, but for a different student -- can't read someone else's progress.
    other=auth_header('cadet-other')
    assert client.get('/students/cadet-login/progress',headers=other).status_code==403
    # Can't submit an assessment claiming to be a different student either.
    p=dict(student_id='cadet-login',mission_id='M001',question_id='Q001',answer='C',time_taken=10,hints_used=0)
    assert client.post('/assessment',json=p,headers=other).status_code==403


def test_per_context_mastery_and_transfer_gap():
    h=auth_header('cadet-3')
    base=dict(student_id='cadet-3',mission_id='M001',question_id='Q001',answer='C',time_taken=20,hints_used=0)
    # Master the numerical context.
    r=client.post('/assessment',json={**base,'context':'numerical'},headers=h)
    assert r.status_code==200 and r.json()['correct'] is True
    # Fail the transfer context on the same objective/mission.
    r=client.post('/assessment',json={**base,'context':'transfer','answer':'A'},headers=h)
    assert r.status_code==200 and r.json()['correct'] is False

    progress=client.get('/students/cadet-3/progress',headers=h).json()
    assert 'M001' in progress['mastery']
    assert set(progress['mastery']['M001'].keys())=={'numerical','transfer'}
    assert progress['mastery']['M001']['numerical']['level']=='mastered'
    assert progress['mastery']['M001']['transfer']['level']=='weak'
    # The numerical/transfer score spread should trip the fake-mastery flag.
    assert 'M001' in progress['transfer_gaps']


def test_prediction_mechanic():
    h=auth_header('cadet-4')
    r=client.post('/student/cadet-4/predict',json=dict(mission_id='M001',question_id='Q001',predicted='force increases'),headers=h)
    assert r.status_code==200
    prediction_id=r.json()['prediction_id']

    r=client.post('/student/cadet-4/predict/resolve',json=dict(prediction_id=prediction_id,actual='force increases'),headers=h)
    assert r.status_code==200 and r.json()['matched'] is True

    progress=client.get('/students/cadet-4/progress',headers=h).json()
    assert progress['mastery']['M001']['transfer']['level'] in ('mastered','developing')

    r=client.post('/student/cadet-4/predict/resolve',json=dict(prediction_id=999999,actual='x'),headers=h)
    assert r.status_code==404

import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_get_api_key(client):
    res = client.get('/api/key')
    assert res.status_code == 200
    data = res.get_json()
    assert 'apiKey' in data
    assert isinstance(data['apiKey'], str)

def test_get_comments_empty(client):
    res = client.get('/api/comments?url=http://fake-url.com')
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)

def test_get_user_unauth(client):
    res = client.get('/api/user')
    assert res.status_code == 401

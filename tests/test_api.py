from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "API working"

def test_add():
    response = client.get("/add?a=2&b=3")
    assert response.status_code == 200
    assert response.json()["result"] == 5

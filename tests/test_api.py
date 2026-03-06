from fastapi.testclient import TestClient
from api.app import app, API_KEY

client = TestClient(app)

headers = {"X-API-KEY": API_KEY}

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_customer():
    data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@test.com"
    }

    response = client.post("/customers", json=data, headers=headers)

    assert response.status_code == 201
    body = response.json()

    assert body["first_name"] == "John"
    assert "id" in body


def test_list_customers():
    response = client.get("/customers?page=1&page_size=10", headers=headers)

    assert response.status_code == 200

def test_start(client):
    response = client.get("/")
    assert response.status_code == 200

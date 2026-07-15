"""Tests for auth + project CRUD (Day 2)."""

def test_register_and_login(client):
    r = client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "supersecret"})
    assert r.status_code == 200 and "access_token" in r.json()
    # duplicate email rejected
    r2 = client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "supersecret"})
    assert r2.status_code == 409


def test_login_wrong_password(client):
    client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "supersecret"})
    r = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "nope"})
    assert r.status_code == 401


def test_protected_route_requires_token(client):
    assert client.get("/api/v1/projects").status_code == 401
    assert client.post("/api/v1/projects", json={"name": "x"}).status_code == 401


def test_project_crud(client):
    token = _login(client)
    h = {"Authorization": f"Bearer {token}"}
    # create
    r = client.post("/api/v1/projects", headers=h, json={"name": "P1", "environment": "mock"})
    assert r.status_code == 201
    pid = r.json()["id"]
    # list
    assert len(client.get("/api/v1/projects", headers=h).json()) == 1
    # get
    assert client.get(f"/api/v1/projects/{pid}", headers=h).status_code == 200
    # update
    r = client.patch(f"/api/v1/projects/{pid}", headers=h, json={"description": "updated"})
    assert r.json()["description"] == "updated"
    # delete
    assert client.delete(f"/api/v1/projects/{pid}", headers=h).status_code == 204
    assert client.get(f"/api/v1/projects/{pid}", headers=h).status_code == 404


def test_project_isolation(client):
    t1 = _login(client, "u1@b.com")
    t2 = _login(client, "u2@b.com")
    h1 = {"Authorization": f"Bearer {t1}"}
    pid = client.post("/api/v1/projects", headers=h1, json={"name": "secret"}).json()["id"]
    # user2 cannot see or access user1's project
    assert client.get("/api/v1/projects", headers={"Authorization": f"Bearer {t2}"}).json() == []
    assert client.get(f"/api/v1/projects/{pid}", headers={"Authorization": f"Bearer {t2}"}).status_code == 404


def _login(client, email="dev@example.com", password="supersecret"):
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    return client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]

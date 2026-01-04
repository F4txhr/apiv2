from fastapi.testclient import TestClient
from src.main import app
from src.database import init_db
from unittest.mock import patch, MagicMock
import json
import os

# Initialize DB for tests
init_db()

client = TestClient(app)

def test_auth_workflow():
    # 1. Register
    import random
    username = f"user_{random.randint(1, 100000)}"
    password = "password123"
    
    resp_reg = client.post("/register", json={"username": username, "password": password})
    assert resp_reg.status_code == 200
    
    # 2. Login
    resp_login = client.post("/token", data={"username": username, "password": password})
    assert resp_login.status_code == 200
    token = resp_login.json()["access_token"]
    
    # 3. Access Protected Route
    headers = {"Authorization": f"Bearer {token}"}
    resp_me = client.get("/users/me", headers=headers)
    assert resp_me.status_code == 200
    assert resp_me.json()["username"] == username
    
    # 4. Save Config
    resp_save = client.post("/config/save", json={"name": "MyConfig", "data": "vmess://..."}, headers=headers)
    assert resp_save.status_code == 200
    
    # 5. List Configs
    resp_list = client.get("/config/list", headers=headers)
    assert resp_list.status_code == 200
    assert len(resp_list.json()) > 0
    assert resp_list.json()[0]["name"] == "MyConfig"

def test_pretty_json_output():
    # Test /stats for pretty print (indentation)
    resp = client.get("/stats")
    assert resp.status_code == 200
    # Check if content has newlines/indents (simple check for pretty print)
    assert b"\n" in resp.content
    assert b"  " in resp.content 

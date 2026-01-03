from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_subscription_display_clash():
    link = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@1.1.1.1:8388#test_ss"
    response = client.post("/sub", json={"data": link, "target": "clash"})
    assert response.status_code == 200
    # Should not enforce download by default
    assert "content-disposition" not in response.headers
    assert "proxies:" in response.text

def test_subscription_download_clash():
    link = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@1.1.1.1:8388#test_ss"
    response = client.post("/sub?download=true", json={"data": link, "target": "clash"})
    assert response.status_code == 200
    assert "attachment; filename=config.yaml" in response.headers["content-disposition"]
    assert "proxies:" in response.text

def test_subscription_display_singbox():
    link = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@1.1.1.1:8388#test_ss"
    response = client.post("/sub", json={"data": link, "target": "singbox"})
    assert response.status_code == 200
    assert "content-disposition" not in response.headers
    assert "outbounds" in response.text

def test_subscription_download_singbox():
    link = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@1.1.1.1:8388#test_ss"
    response = client.post("/sub?download=true", json={"data": link, "target": "singbox"})
    assert response.status_code == 200
    assert "attachment; filename=config.json" in response.headers["content-disposition"]
    assert "outbounds" in response.text

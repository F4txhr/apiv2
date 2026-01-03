from fastapi.testclient import TestClient
from src.main import app
import yaml
import json

client = TestClient(app)

def test_full_config_clash():
    link = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@1.1.1.1:8388#test_ss"
    response = client.post("/sub?full=true", json={"data": link, "target": "clash"})
    assert response.status_code == 200
    content = yaml.safe_load(response.text)
    assert "proxies" in content
    assert "proxy-groups" in content
    assert "rules" in content
    assert "dns" in content
    # Check if proxy is in groups
    assert "test_ss" in content["proxy-groups"][0]["proxies"]

def test_full_config_singbox():
    link = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@1.1.1.1:8388#test_ss"
    response = client.post("/sub?full=true", json={"data": link, "target": "singbox"})
    assert response.status_code == 200
    content = json.loads(response.text)
    assert "outbounds" in content
    assert "route" in content
    assert "dns" in content
    # Check if proxy is in selector
    selector = next(o for o in content["outbounds"] if o["tag"] == "PROXY")
    assert "test_ss" in selector["outbounds"]

def test_auto_detect_user_agent_clash():
    link = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@1.1.1.1:8388#test_ss"
    # Sending 'auto' target (default)
    response = client.post(
        "/sub", 
        json={"data": link}, 
        headers={"User-Agent": "Clash/1.0"}
    )
    assert response.status_code == 200
    assert "proxies:" in response.text # YAML indicator

def test_auto_detect_user_agent_singbox():
    link = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@1.1.1.1:8388#test_ss"
    response = client.post(
        "/sub", 
        json={"data": link}, 
        headers={"User-Agent": "sing-box/1.8.0"}
    )
    assert response.status_code == 200
    assert "outbounds" in response.text # JSON indicator

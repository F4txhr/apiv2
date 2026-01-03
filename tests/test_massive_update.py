from fastapi.testclient import TestClient
from src.main import app
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_modifiers_name_filter():
    link1 = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@1.1.1.1:8388#Gaming_Server"
    link2 = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@2.2.2.2:8388#Netflix_Server"
    data = f"{link1}\n{link2}"
    
    # Filter Include
    resp = client.post("/sub?filter_name=Gaming", json={"data": data, "target": "clash"})
    assert "Gaming_Server" in resp.text
    assert "Netflix_Server" not in resp.text
    
    # Filter Exclude
    resp = client.post("/sub?exclude_name=Gaming", json={"data": data, "target": "clash"})
    assert "Gaming_Server" not in resp.text
    assert "Netflix_Server" in resp.text

def test_modifiers_udp_override():
    link = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@1.1.1.1:8388#test"
    # Force UDP False
    resp = client.post("/sub?udp=false", json={"data": link, "target": "clash"})
    assert "udp: false" in resp.text

def test_modifiers_force_sni():
    link = "vless://uuid@1.1.1.1:443?sni=old.com#test"
    resp = client.post("/sub?force_sni=new.com", json={"data": link, "target": "clash"})
    assert "servername: new.com" in resp.text

def test_network_utils():
    # CIDR
    resp = client.get("/cidr?cidr=192.168.1.0/24")
    assert resp.status_code == 200
    assert "256" in str(resp.json()["num_addresses"])
    
    # MyIP (mock client host)
    # TestClient doesn't easily mock client.host but we check structure
    resp = client.get("/myip")
    assert "ip" in resp.json()
    assert "browser" in resp.json()

@patch("src.checker.ping")
def test_icmp_ping(mock_ping):
    mock_ping.return_value = 0.05
    resp = client.get("/ping?host=google.com")
    assert resp.json()["status"] == "reachable"
    assert resp.json()["latency_ms"] == 0.05

@patch("socket.create_connection")
def test_port_scan(mock_socket):
    resp = client.get("/scan?host=1.1.1.1&ports=80,443")
    assert resp.status_code == 200
    assert "scan_results" in resp.json()

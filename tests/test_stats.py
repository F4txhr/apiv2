from fastapi.testclient import TestClient
from src.main import app
import psutil

client = TestClient(app)

def test_stats_metrics():
    # Make some requests to increment counters
    client.get("/check?ip=1.1.1.1&port=80")
    client.get("/qr?text=test")
    
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "running"
    
    # Check System Stats
    assert "system" in data
    assert "cpu_percent" in data["system"]
    assert "ram_percent" in data["system"]
    assert isinstance(data["system"]["ram_used_mb"], float)
    
    # Check Traffic Stats
    assert "traffic" in data
    assert data["traffic"]["total_requests"] >= 3 # check + qr + stats itself
    assert data["traffic"]["check_requests"] >= 1
    assert data["traffic"]["qr_requests"] >= 1
    
    # Check Cache Stats
    assert "cache" in data
    assert "size" in data["cache"]

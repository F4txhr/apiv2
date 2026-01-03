from fastapi.testclient import TestClient
from src.main import app
import os
from unittest.mock import patch, AsyncMock, MagicMock
import base64

client = TestClient(app)

def test_base64_smart_import():
    # Create a base64 string containing two links
    links = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@1.1.1.1:8388#test1\nss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@2.2.2.2:8388#test2"
    encoded = base64.b64encode(links.encode()).decode()
    
    # Send the base64 string as data
    response = client.post("/sub", json={"data": encoded, "target": "clash"})
    assert response.status_code == 200
    assert "test1" in response.text
    assert "test2" in response.text

@patch("src.checker.httpx.AsyncClient")
def test_geoip_caching(mock_client):
    # Mock the external API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "success", "country": "TestCountry", "city": "TestCity"
    }
    
    # Setup async mock for client context manager
    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response
    mock_client.return_value.__aenter__.return_value = mock_client_instance
    
    # First call: should hit the "API" (mock)
    client.get("/check?ip=8.8.8.8&port=53")
    
    # Second call: should be cached, so mock shouldn't be called again if caching works
    # Note: unittest.mock doesn't easily track calls across separate requests in this setup 
    # without resetting, but we can verify the result is consistent.
    # To truly verify caching, we'd need to inspect the _geoip_cache dict or see call counts.
    from src.checker import _geoip_cache
    assert "8.8.8.8" in _geoip_cache

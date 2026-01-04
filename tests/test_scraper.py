from fastapi.testclient import TestClient
from src.main import app
from unittest.mock import patch, AsyncMock

client = TestClient(app)

@patch("src.scraper.fetch_url", new_callable=AsyncMock)
def test_free_accounts_scraper(mock_fetch):
    # Mock GitHub response
    mock_fetch.return_value = "vmess://eyJhZGQiOiAiMS4xLjEuMSIsICJwb3J0IjogNDQzLCAiaWQiOiAidXVpZCIsICJuZXQiOiAid3MiLCAicHMiOiAiRnJlZSBTZXJ2ZXIifQ=="
    
    # Test auto target
    resp = client.get("/free", headers={"User-Agent": "Clash"})
    assert resp.status_code == 200
    assert "Free Server" in resp.text
    assert "proxies:" in resp.text # YAML

    # Test explicit target
    resp_singbox = client.get("/free?target=singbox")
    assert resp_singbox.status_code == 200
    assert "outbounds" in resp_singbox.text

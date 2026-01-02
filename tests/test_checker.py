from unittest.mock import patch, MagicMock
from src.checker import check_connection
import socket

def test_check_connection_success():
    with patch("socket.create_connection") as mock_socket:
        mock_socket.return_value.__enter__.return_value = MagicMock()
        result = check_connection("1.1.1.1", 80)
        assert result["status"] == "open"
        assert result["host"] == "1.1.1.1"
        assert result["port"] == 80
        assert isinstance(result["latency_ms"], float)

def test_check_connection_failure():
    with patch("socket.create_connection") as mock_socket:
        mock_socket.side_effect = socket.timeout
        result = check_connection("1.1.1.1", 80)
        assert result["status"] == "closed"
        assert result["latency_ms"] is None

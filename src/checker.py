import socket
import time
import httpx
from typing import Optional, Dict, Any

# Simple in-memory cache: {ip: (data, timestamp)}
_geoip_cache: Dict[str, Any] = {}
CACHE_TTL = 600  # 10 minutes

def get_cache_stats() -> Dict[str, int]:
    """Returns statistics about the GeoIP cache."""
    # Optional: Clean up expired items lazily or just return current count
    return {"size": len(_geoip_cache)}

def check_connection(host: str, port: int, timeout: int = 3):
    """
    Checks if a TCP connection can be established to the given host and port.
    Returns a dictionary with status and latency.
    """
    start_time = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            latency = (time.time() - start_time) * 1000  # in ms
            return {
                "host": host,
                "port": port,
                "status": "open",
                "latency_ms": round(latency, 2)
            }
    except (socket.timeout, ConnectionRefusedError, OSError):
        return {
            "host": host,
            "port": port,
            "status": "closed",
            "latency_ms": None
        }

async def get_geoip(ip: str) -> Optional[Dict[str, Any]]:
    """
    Fetches GeoIP information for a given IP using ip-api.com with caching.
    """
    current_time = time.time()
    
    # Check cache
    if ip in _geoip_cache:
        data, timestamp = _geoip_cache[ip]
        if current_time - timestamp < CACHE_TTL:
            return data
        else:
            del _geoip_cache[ip] # Expired

    try:
        # Check if the input is a valid IP or hostname. 
        # ip-api supports hostnames too, but better to resolve or just pass it.
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"http://ip-api.com/json/{ip}?fields=status,country,city,isp,org")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    result = {
                        "country": data.get("country"),
                        "city": data.get("city"),
                        "isp": data.get("isp"),
                        "org": data.get("org")
                    }
                    # Save to cache
                    _geoip_cache[ip] = (result, current_time)
                    return result
    except Exception as e:
        print(f"GeoIP error: {e}")
    return None

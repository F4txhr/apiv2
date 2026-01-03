import socket
import time
import httpx
from typing import Optional, Dict, Any, List
from ping3 import ping

# Simple in-memory cache: {ip: (data, timestamp)}
_geoip_cache: Dict[str, Any] = {}
CACHE_TTL = 600  # 10 minutes

def get_cache_stats() -> Dict[str, int]:
    """Returns statistics about the GeoIP cache."""
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

def icmp_ping(host: str, count: int = 1, timeout: int = 2) -> Dict[str, Any]:
    """Performs ICMP ping."""
    try:
        # ping returns delay in seconds or None/False
        delay = ping(host, timeout=timeout, unit="ms")
        if delay is None or delay is False:
             return {"host": host, "status": "unreachable", "latency_ms": None}
        return {"host": host, "status": "reachable", "latency_ms": round(delay, 2)}
    except Exception as e:
        return {"host": host, "status": "error", "error": str(e)}

def port_scan(host: str, ports: List[int], timeout: int = 1) -> Dict[str, Any]:
    """Scans multiple ports on a host."""
    results = {}
    for port in ports:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                results[port] = "open"
        except:
            results[port] = "closed"
    return {"host": host, "scan_results": results}

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

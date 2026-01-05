import socket
import time
import httpx
import ssl
import datetime
import dns.resolver
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

async def check_website_status(url: str, timeout: int = 5) -> Dict[str, Any]:
    """Checks the HTTP status of a website."""
    if not url.startswith("http"):
        url = "http://" + url
    
    start_time = time.time()
    try:
        async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
            resp = await client.get(url)
            latency = (time.time() - start_time) * 1000
            return {
                "url": url,
                "status_code": resp.status_code,
                "reason": resp.reason_phrase,
                "latency_ms": round(latency, 2),
                "is_up": resp.status_code < 400
            }
    except Exception as e:
        return {
            "url": url,
            "error": str(e),
            "is_up": False
        }

def get_ssl_cert_info(host: str, port: int = 443) -> Dict[str, Any]:
    """Retrieves SSL certificate information."""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    try:
        with socket.create_connection((host, port), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert(binary_form=True)
                # We need to decode the cert or get it in dict form. 
                # CERT_NONE returns empty dict for getpeercert() unless binary_form=True is used, 
                # but to get parsed info we need CERT_REQUIRED or manual parsing.
                # Let's try connecting with default context but no verification if possible, 
                # or just use standard library calls.
                pass
            
        # Re-connect with verification to get parsed info if possible, or use a custom fetcher
        # Simplest way to get expiry:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_OPTIONAL 
        
        with socket.create_connection((host, port), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                if not cert:
                    return {"error": "No certificate found"}
                
                not_after = cert.get('notAfter')
                issuer = dict(x[0] for x in cert.get('issuer'))
                subject = dict(x[0] for x in cert.get('subject'))
                
                # Parse date format: 'May 26 23:59:59 2024 GMT'
                expiry_date = datetime.datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                days_left = (expiry_date - datetime.datetime.now()).days
                
                return {
                    "host": host,
                    "issuer": issuer.get('organizationName') or issuer.get('commonName'),
                    "subject": subject.get('commonName'),
                    "expiry_date": not_after,
                    "days_remaining": days_left,
                    "valid": days_left > 0
                }
    except Exception as e:
        return {"host": host, "error": str(e)}

def dns_lookup(domain: str, record_type: str = "A") -> Dict[str, Any]:
    """Performs a DNS lookup."""
    try:
        answers = dns.resolver.resolve(domain, record_type)
        results = [str(r) for r in answers]
        return {
            "domain": domain,
            "type": record_type,
            "records": results
        }
    except Exception as e:
        return {"domain": domain, "error": str(e)}

async def mac_vendor_lookup(mac: str) -> Dict[str, Any]:
    """Looks up MAC address vendor using macvendors.co API."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"https://macvendors.co/api/{mac}")
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "mac": mac,
                    "vendor": data.get("result", {}).get("company"),
                    "address": data.get("result", {}).get("address")
                }
    except Exception as e:
        return {"mac": mac, "error": str(e)}
    return {"mac": mac, "error": "Lookup failed"}

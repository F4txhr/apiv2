from fastapi import FastAPI, HTTPException, Response, Body, Query, Header, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional, List
import time
import os
import psutil
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from user_agents import parse as parse_ua
from ipaddress import ip_network, ip_address
from src.checker import check_connection, get_geoip, get_cache_stats, icmp_ping, port_scan
from src.parser import parse_link, decode_if_base64
from src.converter import to_clash, to_singbox, apply_modifiers
from src.qr_utils import generate_qr_image

# Setup Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

start_time = time.time()

# Request Counters
stats_counters = {
    "total_requests": 0,
    "check_requests": 0,
    "sub_requests": 0,
    "qr_requests": 0,
    "ping_requests": 0,
    "scan_requests": 0,
    "myip_requests": 0,
    "cidr_requests": 0
}

@app.middleware("http")
async def count_requests(request, call_next):
    stats_counters["total_requests"] += 1
    response = await call_next(request)
    return response

@app.get("/stats")
def get_stats():
    """Returns the status, uptime, resource usage, and traffic stats."""
    uptime_seconds = time.time() - start_time
    
    # System Resources
    cpu_usage = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    
    return {
        "status": "running",
        "version": "1.3.0",
        "uptime_seconds": round(uptime_seconds, 2),
        "uptime_human": f"{round(uptime_seconds / 60, 2)} minutes",
        "system": {
            "cpu_percent": cpu_usage,
            "ram_percent": ram.percent,
            "ram_used_mb": round(ram.used / 1024 / 1024, 2),
            "ram_total_mb": round(ram.total / 1024 / 1024, 2)
        },
        "traffic": stats_counters,
        "cache": get_cache_stats()
    }

@app.get("/check")
@limiter.limit("100/3seconds")
async def check_ip(request: Request, ip: str, port: int, timeout: int = 3):
    stats_counters["check_requests"] += 1
    result = await run_in_threadpool(check_connection, ip, port, timeout)
    geo = await get_geoip(ip)
    if geo:
        result["location"] = geo
    return result

@app.get("/ping")
@limiter.limit("100/3seconds")
async def ping_host(request: Request, host: str, count: int = 1):
    """Performs an ICMP Ping to the host."""
    stats_counters["ping_requests"] += 1
    return await run_in_threadpool(icmp_ping, host, count)

@app.get("/scan")
@limiter.limit("50/3seconds")
async def scan_ports(request: Request, host: str, ports: str = "80,443,22,8080,8443"):
    """Scans multiple ports (comma separated)."""
    stats_counters["scan_requests"] += 1
    try:
        port_list = [int(p) for p in ports.split(",")]
        # Limit to 10 ports max to prevent abuse
        if len(port_list) > 10:
            port_list = port_list[:10]
    except:
        raise HTTPException(status_code=400, detail="Invalid ports format")
        
    return await run_in_threadpool(port_scan, host, port_list)

@app.get("/myip")
@limiter.limit("100/3seconds")
def get_myip(request: Request, user_agent: Optional[str] = Header(None)):
    """Returns the requester's IP and User-Agent info."""
    stats_counters["myip_requests"] += 1
    ip = request.client.host
    ua_string = user_agent or ""
    ua = parse_ua(ua_string)
    
    return {
        "ip": ip,
        "browser": str(ua.browser),
        "os": str(ua.os),
        "device": str(ua.device),
        "raw_ua": ua_string
    }

@app.get("/cidr")
@limiter.limit("100/3seconds")
def cidr_calc(request: Request, cidr: str):
    """Calculates details for a CIDR subnet."""
    stats_counters["cidr_requests"] += 1
    try:
        network = ip_network(cidr, strict=False)
        return {
            "cidr": cidr,
            "netmask": str(network.netmask),
            "network_address": str(network.network_address),
            "broadcast_address": str(network.broadcast_address),
            "num_addresses": network.num_addresses,
            "first_host": str(network[1]) if network.num_addresses > 2 else None,
            "last_host": str(network[-2]) if network.num_addresses > 2 else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/sub")
@limiter.limit("100/3seconds")
def subscription_endpoint(
    request: Request,
    data: str = Body(..., embed=True), 
    target: str = Body("auto", embed=True),
    download: bool = Query(False),
    full: bool = Query(False),
    # New Filter Params
    filter_name: Optional[str] = Query(None),
    exclude_name: Optional[str] = Query(None),
    filter_protocol: Optional[str] = Query(None),
    force_sni: Optional[str] = Query(None),
    udp: Optional[bool] = Query(None),
    remove_expired: bool = Query(False),
    
    user_agent: Optional[str] = Header(None)
):
    stats_counters["sub_requests"] += 1
    decoded_data = decode_if_base64(data)
    links = decoded_data.strip().splitlines()
    parsed_list = []
    
    for link in links:
        link = link.strip()
        if not link:
            continue
        parsed = parse_link(link)
        if parsed:
            parsed_list.append(parsed)
            
    if not parsed_list:
        raise HTTPException(status_code=400, detail="No valid links found")

    # Apply Modifiers
    modifier_options = {
        "filter_name": filter_name,
        "exclude_name": exclude_name,
        "filter_protocol": filter_protocol,
        "force_sni": force_sni,
        "remove_expired": remove_expired
    }
    if udp is not None:
        modifier_options["udp_toggle"] = udp
        
    parsed_list = apply_modifiers(parsed_list, modifier_options)
    
    if not parsed_list:
        raise HTTPException(status_code=400, detail="No links remaining after filters")

    # Target Detection
    final_target = target.lower()
    if final_target == "auto":
        ua = (user_agent or "").lower()
        if "clash" in ua or "mihomo" in ua:
            final_target = "clash"
        elif "sing-box" in ua or "singbox" in ua or "neko" in ua:
            final_target = "singbox"
        else:
            final_target = "clash"

    content = ""
    media_type = ""
    filename = ""

    if final_target == "clash":
        content = to_clash(parsed_list, full=full)
        media_type = "application/x-yaml" if download else "text/yaml"
        filename = "config.yaml"
    elif final_target == "singbox":
        content = to_singbox(parsed_list, full=full)
        media_type = "application/json"
        filename = "config.json"
    else:
        raise HTTPException(status_code=400, detail="Unsupported target. Use 'clash' or 'singbox'")

    headers = {}
    if download:
        headers["Content-Disposition"] = f"attachment; filename={filename}"

    return Response(
        content=content, 
        media_type=media_type,
        headers=headers
    )

@app.get("/qr")
@limiter.limit("100/3seconds")
def get_qr(request: Request, text: str):
    """Generates a QR code for the given text."""
    stats_counters["qr_requests"] += 1
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    img_bytes = generate_qr_image(text)
    return Response(content=img_bytes, media_type="image/png")

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host=host, port=port)

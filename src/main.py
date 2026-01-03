from fastapi import FastAPI, HTTPException, Response, Body, Query, Header
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional, List
import time
import os
import psutil
from src.checker import check_connection, get_geoip, get_cache_stats
from src.parser import parse_link, decode_if_base64
from src.converter import to_clash, to_singbox
from src.qr_utils import generate_qr_image

app = FastAPI()
start_time = time.time()

# Request Counters
stats_counters = {
    "total_requests": 0,
    "check_requests": 0,
    "sub_requests": 0,
    "qr_requests": 0
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
        "version": "1.1.0",
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
async def check_ip(ip: str, port: int, timeout: int = 3):
    stats_counters["check_requests"] += 1
    # TCP check (run in threadpool to avoid blocking event loop)
    result = await run_in_threadpool(check_connection, ip, port, timeout)
    
    # GeoIP check (async)
    # Always check GeoIP to confirm server location regardless of port status
    geo = await get_geoip(ip)
    if geo:
        result["location"] = geo
             
    return result

@app.post("/sub")
def subscription_endpoint(
    data: str = Body(..., embed=True), 
    target: str = Body("auto", embed=True),
    download: bool = Query(False),
    full: bool = Query(False),
    user_agent: Optional[str] = Header(None)
):
    """
    Consolidated endpoint for converting and subscribing to VPN configs.
    
    - data: List of links separated by newlines (or a single base64 encoded string).
    - target: 'clash', 'singbox', or 'auto' (detect based on User-Agent).
    - download: If true, forces file download.
    - full: If true, returns a full config (Rules/DNS) instead of just proxy list.
    """
    stats_counters["sub_requests"] += 1
    
    # Try decoding if it looks like a single base64 block
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

    # Auto-detect target if 'auto'
    final_target = target.lower()
    if final_target == "auto":
        ua = (user_agent or "").lower()
        if "clash" in ua or "mihomo" in ua:
            final_target = "clash"
        elif "sing-box" in ua or "singbox" in ua or "neko" in ua:
            final_target = "singbox"
        else:
            # Default fallback if unknown
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
def get_qr(text: str):
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

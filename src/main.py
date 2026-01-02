from fastapi import FastAPI, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional, List
from src.checker import check_connection, get_geoip
from src.parser import parse_link
from src.converter import to_clash, to_singbox
from src.qr_utils import generate_qr_image

app = FastAPI()

class ConvertRequest(BaseModel):
    data: str  # text containing links
    target: str # 'clash' or 'singbox'

@app.get("/check")
async def check_ip(ip: str, port: int, timeout: int = 3):
    # TCP check (run in threadpool to avoid blocking event loop)
    result = await run_in_threadpool(check_connection, ip, port, timeout)
    
    # GeoIP check (async)
    # Always check GeoIP to confirm server location regardless of port status
    geo = await get_geoip(ip)
    if geo:
        result["location"] = geo
             
    return result

@app.post("/convert")
def convert_config(request: ConvertRequest):
    links = request.data.strip().splitlines()
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

    if request.target.lower() == "clash":
        return {"config": to_clash(parsed_list), "format": "yaml"}
    elif request.target.lower() == "singbox":
        return {"config": to_singbox(parsed_list), "format": "json"}
    else:
        raise HTTPException(status_code=400, detail="Unsupported target. Use 'clash' or 'singbox'")

@app.get("/qr")
def get_qr(text: str):
    """Generates a QR code for the given text."""
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    img_bytes = generate_qr_image(text)
    return Response(content=img_bytes, media_type="image/png")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

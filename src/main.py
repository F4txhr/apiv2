from fastapi import FastAPI, HTTPException, Response, Body, Query, Header, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, List
import time
import os
import psutil
import json
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from user_agents import parse as parse_ua
from ipaddress import ip_network, ip_address
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from src.checker import (
    check_connection, get_geoip, get_cache_stats, icmp_ping, port_scan, 
    check_website_status, get_ssl_cert_info, dns_lookup, mac_vendor_lookup
)
from src.warp import generate_warp_plus_mock
from src.downloader import get_media_info
from src.parser import parse_link, decode_if_base64
from src.converter import to_clash, to_singbox, apply_modifiers
from src.qr_utils import generate_qr_image
from src.scraper import get_free_accounts
from src.database import init_db, SessionLocal, User, Config
from src.auth import verify_password, get_password_hash, create_access_token, SECRET_KEY, ALGORITHM

# Setup Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

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
    "cidr_requests": 0,
    "free_requests": 0
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@app.on_event("startup")
def startup_event():
    init_db()

@app.middleware("http")
async def count_requests(request, call_next):
    stats_counters["total_requests"] += 1
    response = await call_next(request)
    return response

class PrettyJSONResponse(Response):
    media_type = "application/json"
    def render(self, content: any) -> bytes:
        return json.dumps(content, indent=2).encode("utf-8")

@app.get("/stats", response_class=PrettyJSONResponse)
def get_stats():
    """Returns the status, uptime, resource usage, and traffic stats."""
    uptime_seconds = time.time() - start_time
    cpu_usage = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "status": "running",
        "version": "1.5.0",
        "uptime_seconds": round(uptime_seconds, 2),
        "uptime_human": f"{round(uptime_seconds / 60, 2)} minutes",
        "system": {
            "cpu_percent": cpu_usage,
            "ram_percent": ram.percent,
            "ram_used_mb": round(ram.used / 1024 / 1024, 2),
            "ram_total_mb": round(ram.total / 1024 / 1024, 2),
            "disk_percent": disk.percent,
            "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
            "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 2)
        },
        "traffic": stats_counters,
        "cache": get_cache_stats()
    }

# --- Auth Endpoints ---

class UserCreate(BaseModel):
    username: str
    password: str

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    return {"message": "User created successfully"}

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "id": current_user.id}

class ConfigCreate(BaseModel):
    name: str
    data: str

@app.post("/config/save")
def save_config(config: ConfigCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_config = Config(name=config.name, data=config.data, owner_id=current_user.id)
    db.add(new_config)
    db.commit()
    return {"message": "Config saved", "id": new_config.id}

@app.get("/config/list")
def list_configs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Config).filter(Config.owner_id == current_user.id).all()

# --- Utility Endpoints ---

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
    stats_counters["ping_requests"] += 1
    return await run_in_threadpool(icmp_ping, host, count)

@app.get("/scan")
@limiter.limit("50/3seconds")
async def scan_ports(request: Request, host: str, ports: str = "80,443,22,8080,8443"):
    stats_counters["scan_requests"] += 1
    try:
        port_list = [int(p) for p in ports.split(",")]
        if len(port_list) > 10:
            port_list = port_list[:10]
    except:
        raise HTTPException(status_code=400, detail="Invalid ports format")
    return await run_in_threadpool(port_scan, host, port_list)

@app.get("/check/website")
@limiter.limit("50/3seconds")
async def website_checker(request: Request, url: str):
    return await check_website_status(url)

@app.get("/check/ssl")
@limiter.limit("50/3seconds")
async def ssl_checker(request: Request, host: str, port: int = 443):
    return await run_in_threadpool(get_ssl_cert_info, host, port)

@app.get("/tools/dns")
@limiter.limit("50/3seconds")
async def dns_tool(request: Request, domain: str, type: str = "A"):
    return await run_in_threadpool(dns_lookup, domain, type)

@app.get("/tools/mac")
@limiter.limit("50/3seconds")
async def mac_tool(request: Request, mac: str):
    return await mac_vendor_lookup(mac)

@app.get("/tools/warp")
@limiter.limit("5/60seconds")
async def warp_tool(request: Request):
    return await generate_warp_plus_mock()

@app.get("/tools/media")
@limiter.limit("5/60seconds")
async def media_downloader(request: Request, url: str):
    """Downloads social media content (Video/Audio/Metadata)."""
    return await run_in_threadpool(get_media_info, url)

@app.get("/myip")
@limiter.limit("100/3seconds")
def get_myip(request: Request, user_agent: Optional[str] = Header(None)):
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

@app.get("/free")
@limiter.limit("10/60seconds") 
async def free_accounts(
    request: Request, 
    target: str = "auto",
    user_agent: Optional[str] = Header(None),
    download: bool = Query(False)
):
    """Scrapes free VPN accounts."""
    stats_counters["free_requests"] += 1
    links = await get_free_accounts()
    if not links:
        raise HTTPException(status_code=503, detail="Unable to fetch free accounts")

    parsed_list = []
    for link in links:
        parsed = parse_link(link)
        if parsed:
            parsed_list.append(parsed)

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
        content = to_clash(parsed_list)
        media_type = "application/x-yaml" if download else "text/yaml"
        filename = "free_config.yaml"
    elif final_target == "singbox":
        content = to_singbox(parsed_list)
        media_type = "application/json"
        filename = "free_config.json"
    else:
        raise HTTPException(status_code=400, detail="Unsupported target")

    headers = {}
    if download:
        headers["Content-Disposition"] = f"attachment; filename={filename}"
        return Response(content=content, media_type=media_type, headers=headers)
    
    # Pretty print logic for JSON output when not downloading
    if final_target == "singbox":
         return PrettyJSONResponse(content=json.loads(content))
    else:
         return Response(content=content, media_type=media_type)

@app.post("/sub")
@limiter.limit("100/3seconds")
def subscription_endpoint(
    request: Request,
    data: str = Body(..., embed=True), 
    target: str = Body("auto", embed=True),
    download: bool = Query(False),
    full: bool = Query(False),
    filter_name: Optional[str] = Query(None),
    exclude_name: Optional[str] = Query(None),
    filter_protocol: Optional[str] = Query(None),
    force_sni: Optional[str] = Query(None),
    udp: Optional[bool] = Query(None),
    remove_expired: bool = Query(False),
    auto_rename: bool = Query(False),
    groups: Optional[List[dict]] = Body(None),
    user_agent: Optional[str] = Header(None)
):
    """Consolidated endpoint for converting configs."""
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

    modifier_options = {
        "filter_name": filter_name,
        "exclude_name": exclude_name,
        "filter_protocol": filter_protocol,
        "force_sni": force_sni,
        "remove_expired": remove_expired,
        "auto_rename": auto_rename
    }
    if udp is not None:
        modifier_options["udp_toggle"] = udp
        
    parsed_list = apply_modifiers(parsed_list, modifier_options)
    
    if not parsed_list:
        raise HTTPException(status_code=400, detail="No links remaining after filters")

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
        content = to_clash(parsed_list, full=full, groups=groups)
        media_type = "application/x-yaml" if download else "text/yaml"
        filename = "config.yaml"
    elif final_target == "singbox":
        content = to_singbox(parsed_list, full=full)
        media_type = "application/json"
        filename = "config.json"
    else:
        raise HTTPException(status_code=400, detail="Unsupported target")

    headers = {}
    if download:
        headers["Content-Disposition"] = f"attachment; filename={filename}"
        return Response(content=content, media_type=media_type, headers=headers)

    # Pretty print logic for JSON output when not downloading
    if final_target == "singbox":
         return PrettyJSONResponse(content=json.loads(content))
    else:
         # For YAML, just return plain text as it is already somewhat readable
         return Response(content=content, media_type=media_type)

@app.get("/qr")
@limiter.limit("100/3seconds")
def get_qr(request: Request, text: str):
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

# VPN Tools API

This project provides a FastAPI-based service for checking IP:Port connectivity and converting VPN configuration links to Clash and Sing-box formats.

## Features

- **IP Checker:** Verify if a specific TCP port is open on a host. **Now includes GeoIP information!** 🌍
- **Config Converter:** Convert `vmess://`, `vless://`, `trojan://`, and `ss://` (Shadowsocks) links into Clash (YAML) or Sing-box (JSON) configurations.
- **QR Code Generator:** Convert any text or config link into a QR Code image. 📱
- **Health Stats:** Monitor API uptime and status via `/stats`.

## Installation

### Option 1: Docker (Recommended) 🐳

This method is perfect for VPS deployment (including Alibaba Cloud).

1. Install Docker & Docker Compose.
2. Clone the repository.
3. Run:
   ```bash
   docker compose up -d
   ```
   
   The API will be available at port **80** (HTTP).

### Option 2: Manual

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the server:
   ```bash
   python -m src.main
   # OR
   uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Deployment with Domain Name 🌐

To use a domain (e.g., `api.example.com`) instead of the VPS IP:

1. **DNS Setup:**
   - Log in to your domain registrar (e.g., Cloudflare, Namecheap).
   - Create an **A Record** pointing `api` (or `@`) to your VPS IP address.

2. **Server Setup:**
   - Just run `docker compose up -d` as usual.
   - The included Nginx is configured to accept requests from **any domain name** pointing to the server.

## Usage

**Note:** If using Docker, the port is `80` (default HTTP), so you don't need to specify it in the URL. If using manual run, default is `8000`.

### 1. Check IP:Port (with GeoIP)

**Endpoint:** `GET /check`

**Parameters:**
- `ip`: Hostname or IP address.
- `port`: Port number.
- `timeout` (optional): Connection timeout in seconds (default: 3).

**Example:**
```bash
curl "http://api.example.com/check?ip=1.1.1.1&port=53"
```

**Response:**
```json
{
  "host": "1.1.1.1",
  "port": 53,
  "status": "open",
  "latency_ms": 12.5,
  "location": {
    "country": "Australia",
    "city": "Sydney",
    "isp": "Cloudflare, Inc.",
    "org": "APNIC and Cloudflare DNS Resolver project"
  }
}
```

### 2. Convert Config

**Endpoint:** `POST /convert`

**Body:**
- `data`: String containing one or more VPN links (separated by newlines). Supported formats: VMess, VLESS, Trojan, Shadowsocks (`ss://`).
- `target`: Target format (`clash` or `singbox`).

**Example:**
```bash
curl -X POST "http://api.example.com/convert" \
     -H "Content-Type: application/json" \
     -d '{
           "target": "clash",
           "data": "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@1.1.1.1:8388#Shadowsocks"
         }'
```

**Response:**
```json
{
  "config": "proxies:\n  - name: Shadowsocks...",
  "format": "yaml"
}
```

### 3. Generate QR Code

**Endpoint:** `GET /qr`

**Parameters:**
- `text`: The text or link to convert to QR code.

**Example:**
```bash
# Returns a PNG image
curl "http://api.example.com/qr?text=Hello%20World" --output qr.png
```

### 4. System Stats

**Endpoint:** `GET /stats`

**Example:**
```bash
curl "http://api.example.com/stats"
```

**Response:**
```json
{
  "status": "running",
  "version": "1.0.0",
  "uptime_seconds": 120.5,
  "uptime_human": "2.01 minutes"
}
```

## Testing

Run tests with pytest:

```bash
PYTHONPATH=. pytest
```

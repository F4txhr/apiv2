# VPN Tools API

This project provides a FastAPI-based service for checking IP:Port connectivity and converting VPN configuration links to Clash and Sing-box formats.

## Features

- **IP Checker:** Verify if a specific TCP port is open on a host. **Now includes GeoIP information!** 🌍
- **Config Converter:** Convert `vmess://`, `vless://`, `trojan://`, and `ss://` (Shadowsocks) links into Clash (YAML) or Sing-box (JSON) configurations.
- **QR Code Generator:** Convert any text or config link into a QR Code image. 📱

## Installation

### Option 1: Docker (Recommended) 🐳

This method is perfect for VPS deployment (including Alibaba Cloud).

1. Install Docker & Docker Compose.
2. Clone the repository.
3. Run:
   ```bash
   docker compose up -d
   ```
   The API will be available at port `8000`.

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

## Usage

### 1. Check IP:Port (with GeoIP)

**Endpoint:** `GET /check`

**Parameters:**
- `ip`: Hostname or IP address.
- `port`: Port number.
- `timeout` (optional): Connection timeout in seconds (default: 3).

**Example:**
```bash
curl "http://localhost:8000/check?ip=1.1.1.1&port=53"
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
curl -X POST "http://localhost:8000/convert" \
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
curl "http://localhost:8000/qr?text=Hello%20World" --output qr.png
```

## Testing

Run tests with pytest:

```bash
PYTHONPATH=. pytest
```

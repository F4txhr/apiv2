# VPN Tools API

This project provides a FastAPI-based service for checking IP:Port connectivity and converting VPN configuration links to Clash and Sing-box formats.

## Features

- **IP Checker:** Verify if a specific TCP port is open on a host. **Now includes GeoIP information!** 🌍 (With smart caching)
- **Smart Subscription:** Convert one or multiple VPN links (VMess, VLESS, Trojan, SS, Hysteria2, Tuic) into a consolidated subscription config.
  - **Auto Import:** Can automatically detect and decode raw Base64 subscription blobs.
  - **Auto-Detect Format:** If `target` is not specified, it detects the requested format based on User-Agent (Clash/Mihomo vs Sing-box). 🪄
  - **Full Config Mode:** Add `?full=true` to generate a complete configuration with Rules, DNS, and Proxy Groups (ready to use). ⚙️
  - **Flexible Output:** Supports direct display or file download.
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
   ```

## Deployment with Domain Name 🌐

To use a domain (e.g., `api.example.com`) instead of the VPS IP:

1. **DNS Setup:**
   - Log in to your domain registrar (e.g., Cloudflare, Namecheap).
   - Create an **A Record** pointing `api` (or `@`) to your VPS IP address.

2. **Server Setup:**
   - Just run `docker compose up -d` as usual.
   - The included Nginx is configured to accept requests from domains starting with `api.` (e.g. `api.yoursite.com`). Requests from other domains or direct IP will return 404.

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

### 2. Subscription / Convert Config

**Endpoint:** `POST /sub`

**Body:**
- `data`: String containing one or more VPN links (separated by newlines). Supported formats: VMess, VLESS, Trojan, Shadowsocks (`ss://`), Hysteria2 (`hy2://`), Tuic (`tuic://`). **Also supports raw Base64 subscription blobs.**
- `target`: Target format (`clash`, `singbox`, or `auto`). Default is `auto`.
- `download`: (Optional) Set to `true` to download as file. Default is `false` (display in browser).
- `full`: (Optional) Set to `true` to return a full ready-to-use config with Rules & DNS. Default is `false`.

**Example 1: Auto-Detect (Magic Link)**
Just put the URL in your app (Clash or Sing-box). The API will detect the app and serve the correct format.
```bash
curl -X POST "http://api.example.com/sub" \
     -H "User-Agent: Clash/1.0" \
     -d '{ "data": "ss://..." }'
# Returns YAML
```

**Example 2: Full Config Download**
```bash
curl -X POST "http://api.example.com/sub?download=true&full=true" \
     -H "Content-Type: application/json" \
     -d '{
           "target": "clash",
           "data": "ss://YWVz...\nvless://uuid..."
         }'
# Returns attachment: config.yaml with Rules, DNS, Proxy Groups
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

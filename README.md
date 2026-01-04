# VPN Tools API

This project provides a FastAPI-based service for checking IP:Port connectivity and converting VPN configuration links to Clash and Sing-box formats.

## Features

- **IP Checker:** Verify if a specific TCP port is open on a host. **Now includes GeoIP information!** 🌍 (With smart caching)
- **Smart Subscription:** Convert one or multiple VPN links (VMess, VLESS, Trojan, SS, Hysteria2, Tuic) into a consolidated subscription config.
  - **Auto Import:** Can automatically detect and decode raw Base64 subscription blobs.
  - **Auto-Detect Format:** If `target` is not specified, it detects the requested format based on User-Agent. 🪄
  - **Full Config Mode:** Add `?full=true` to generate a complete configuration with Rules, DNS, and Proxy Groups. ⚙️
  - **Flexible Output:** Supports direct display or file download.
  - **Powerful Filters:** Regex name filter, exclude, force SNI, UDP toggle, expired remover.
- **Free Account Scraper:** Automatically fetch free VPN accounts from public repositories (`/free`). 🆓
- **QR Code Generator:** Convert any text or config link into a QR Code image. 📱
- **Network Utilities:** Suite of tools for network diagnostics (Ping, Port Scan, CIDR, MyIP). 🛠️
- **Secure Deployment:** Rate Limiting and auto-renewing SSL/HTTPS support via Certbot/Nginx. 🔒

## Installation

### Option 1: Docker (Recommended) 🐳

This method is perfect for VPS deployment (including Alibaba Cloud).

1. Install Docker & Docker Compose.
2. Clone the repository.
3. **Setup HTTPS (Optional but Recommended):**
   - Copy `.env.example` to `.env` and edit your `DOMAIN` and `EMAIL`.
   - Run the initialization script:
     ```bash
     chmod +x init-letsencrypt.sh
     ./init-letsencrypt.sh
     ```
   - This will generate SSL certificates and start the server securely on port 443.

4. **Run (if not using SSL script):**
   ```bash
   docker compose up -d
   ```
   
   The API will be available at port **80** (HTTP) or **443** (HTTPS) if configured.

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
   - Just run the Docker steps above.
   - The included Nginx is configured to accept requests from domains starting with `api.` (e.g. `api.yoursite.com`).

## Usage

### 1. Subscription / Convert Config (`/sub`)

The most powerful endpoint. Consolidates multiple links into one subscription.

**Parameters:**
- `download`: `true` (file) or `false` (text).
- `full`: `true` (full config with rules) or `false` (proxies only).
- `target`: `clash`, `singbox`, or `auto`.

**Filters & Modifiers:**
- `filter_name`: Regex to keep matching accounts (e.g., `Singapore`).
- `exclude_name`: Regex to remove matching accounts (e.g., `Expired`).
- `filter_protocol`: Keep only `vmess`, `vless`, etc.
- `force_sni`: Overwrite SNI/Host for all accounts (e.g., `bug.com`).
- `udp`: `true` or `false` (Force enable/disable UDP).
- `remove_expired`: `true` (Remove accounts with YYYY-MM-DD < today).

**Example:**
```bash
curl -X POST "https://api.example.com/sub?full=true&udp=true&filter_name=Gaming" \
     -H "Content-Type: application/json" \
     -d '{ "data": "ss://..." }'
```

### 2. Free Account Scraper (`/free`)

Get a fresh subscription of free VPN accounts.

```bash
curl "https://api.example.com/free?target=clash"
# Returns YAML config with free accounts
```

### 3. Network Utilities

**ICMP Ping (`/ping`)**
Real ping measurement to a host.
```bash
curl "https://api.example.com/ping?host=1.1.1.1&count=3"
```

**Port Scan (`/scan`)**
Scan multiple ports (max 10).
```bash
curl "https://api.example.com/scan?host=google.com&ports=80,443,22"
```

**My IP Info (`/myip`)**
Check your current IP and User Agent details.
```bash
curl "https://api.example.com/myip"
```

**CIDR Calculator (`/cidr`)**
Get details about a subnet.
```bash
curl "https://api.example.com/cidr?cidr=192.168.1.0/24"
```

### 4. Check IP:Port (`/check`)

Verify TCP port and get GeoIP location.
```bash
curl "https://api.example.com/check?ip=1.1.1.1&port=53"
```

### 5. System Stats (`/stats`)

Monitor server health (CPU, RAM, Traffic).
```bash
curl "https://api.example.com/stats"
```

## Security

Rate limiting is active: **100 requests per 3 seconds**. Exceeding this will return `429 Too Many Requests`.

## Testing

Run tests with pytest:

```bash
PYTHONPATH=. pytest
```

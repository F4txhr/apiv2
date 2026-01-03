import base64
import json
import urllib.parse
from typing import Dict, Any, Optional

def safe_base64_decode(s: str) -> str:
    """Helper to handle padding issues in base64 strings."""
    s = s.strip()
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    
    # Try URL-safe first, then standard
    try:
        return base64.urlsafe_b64decode(s).decode("utf-8")
    except Exception:
        # Replace standard characters with url-safe ones or just try standard decode
        # But base64.b64decode handles standard +/
        return base64.b64decode(s).decode("utf-8")

def decode_if_base64(s: str) -> str:
    """Attempts to decode a string if it's a valid Base64 blob, otherwise returns original."""
    s = s.strip()
    # Basic heuristic: no spaces, length multiple of 4 (with padding), only valid b64 chars
    if " " in s or len(s) < 4:
        return s
        
    try:
        # Try decoding
        decoded = safe_base64_decode(s)
        # Check if the result looks like meaningful text (e.g. contains protocol prefixes)
        if any(p in decoded for p in ["vmess://", "vless://", "trojan://", "ss://", "hy2://", "tuic://"]):
            return decoded
        return s
    except Exception:
        return s

def parse_vmess(link: str) -> Optional[Dict[str, Any]]:
    """Parses a vmess:// link."""
    try:
        if not link.startswith("vmess://"):
            return None
        payload = link[8:]
        decoded = safe_base64_decode(payload)
        data = json.loads(decoded)
        
        # Standardize
        return {
            "type": "vmess",
            "name": data.get("ps", "vmess_proxy"),
            "server": data.get("add"),
            "port": int(data.get("port")),
            "uuid": data.get("id"),
            "alterId": int(data.get("aid", 0)),
            "cipher": data.get("scy", "auto"),
            "network": data.get("net", "tcp"),
            "tls": data.get("tls") == "tls",
            "path": data.get("path", ""),
            "host": data.get("host", ""),
            "sni": data.get("sni", data.get("host", "")),
        }
    except Exception as e:
        print(f"Error parsing vmess: {e}")
        return None

def parse_vless_trojan(link: str) -> Optional[Dict[str, Any]]:
    """Parses vless:// or trojan:// links."""
    try:
        parsed = urllib.parse.urlparse(link)
        scheme = parsed.scheme
        if scheme not in ["vless", "trojan"]:
            return None

        # query params
        query = urllib.parse.parse_qs(parsed.query)
        
        data = {
            "type": scheme,
            "name": urllib.parse.unquote(parsed.fragment) or f"{scheme}_proxy",
            "server": parsed.hostname,
            "port": parsed.port,
            "uuid": parsed.username, # For trojan, this is the password
        }

        # Common params
        data["network"] = query.get("type", ["tcp"])[0]
        data["security"] = query.get("security", [""])[0]
        data["path"] = query.get("path", [""])[0]
        data["host"] = query.get("host", [""])[0]
        data["sni"] = query.get("sni", [""])[0] or data["host"]
        data["flow"] = query.get("flow", [""])[0]
        
        if scheme == "trojan":
             data["password"] = parsed.username
             # Trojan usually implies TLS
             if not data["security"]:
                 data["security"] = "tls"

        return data
    except Exception as e:
        print(f"Error parsing {link}: {e}")
        return None

def parse_ss(link: str) -> Optional[Dict[str, Any]]:
    """Parses ss:// links (both SIP002 and legacy base64)."""
    try:
        parsed = urllib.parse.urlparse(link)
        if parsed.scheme != "ss":
            return None
        
        # Helper to decode base64 if needed
        userinfo = parsed.username
        if not userinfo:
             # Try handling base64 in netloc if username is missing (common in some link formats)
             # structure: ss://BASE64@hostname:port#name
             if parsed.hostname and not parsed.port and '@' not in link:
                  # This is a tricky case, usually ss://BASE64#name
                  # But standard urlparse might fail if no @. 
                  # Let's handle the netloc as the payload if no @ is present
                  pass
        
        # Check if userinfo is base64 encoded (legacy format: method:password in base64)
        # SIP002: ss://method:pass@host:port
        # Legacy: ss://BASE64@host:port
        
        method = password = None
        
        # Logic to detect if username is actually a base64 string of method:pass
        # or if it is just method
        # Standard urllib parser puts everything before @ into username and password fields if present
        
        raw_userinfo = parsed.username
        if parsed.password:
             raw_userinfo += f":{parsed.password}"
             
        # Try decoding raw_userinfo as base64
        try:
            decoded = safe_base64_decode(raw_userinfo)
            if ":" in decoded:
                 method, password = decoded.split(":", 1)
            else:
                 # Fallback, maybe it wasn't base64 or didn't contain :
                 method = parsed.username
                 password = parsed.password
        except:
            # Not base64, assume plain text
            method = parsed.username
            password = parsed.password

        if not method or not password:
             # Handle case where everything is in netloc (ss://BASE64)
             # This happens if the link is ss://YWVz... without @host:port visible to urlparse initially?
             # actually standard is ss://userinfo@host:port.
             # If userinfo is base64(method:pass), urlparse.username takes it.
             method = parsed.username
             password = parsed.password
             
        # Special Case: ss://BASE64#name (where base64 includes host:port)
        if not parsed.hostname and not parsed.port:
             # Decode the whole netloc
             try:
                 decoded = safe_base64_decode(parsed.netloc)
                 # Decoded should be method:pass@host:port
                 parts = urllib.parse.urlparse(f"ss://{decoded}")
                 method = parts.username
                 password = parts.password
                 server = parts.hostname
                 port = parts.port
             except:
                 return None
        else:
             server = parsed.hostname
             port = parsed.port

        data = {
            "type": "ss",
            "name": urllib.parse.unquote(parsed.fragment) or "ss_proxy",
            "server": server,
            "port": port,
            "cipher": method,
            "password": password
        }

        # Parse plugin param from query string
        query = urllib.parse.parse_qs(parsed.query)
        plugin_str = query.get("plugin", [""])[0]
        if plugin_str:
            # Format: plugin_name;opt1=val1;opt2=val2
            # Needs to be URL decoded as well (sometimes double encoded)
            plugin_str = urllib.parse.unquote(plugin_str)
            parts = plugin_str.split(";")
            plugin_name = parts[0]
            plugin_opts = {}
            for part in parts[1:]:
                if "=" in part:
                    k, v = part.split("=", 1)
                    plugin_opts[k] = v
                else:
                    plugin_opts[part] = "" # Handle flags without values
            
            data["plugin"] = plugin_name
            data["plugin_opts"] = plugin_opts

        return data

    except Exception as e:
        print(f"Error parsing ss {link}: {e}")
        return None

def parse_hysteria2(link: str) -> Optional[Dict[str, Any]]:
    """Parses hy2:// links."""
    try:
        parsed = urllib.parse.urlparse(link)
        if parsed.scheme != "hy2":
            return None
        
        query = urllib.parse.parse_qs(parsed.query)
        
        data = {
            "type": "hysteria2",
            "name": urllib.parse.unquote(parsed.fragment) or "hy2_proxy",
            "server": parsed.hostname,
            "port": parsed.port,
            "password": parsed.username, # Hysteria2 auth payload is in username
            "sni": query.get("sni", [""])[0],
            "insecure": query.get("insecure", ["0"])[0] == "1",
            "obfs": query.get("obfs", [""])[0],
            "obfs_password": query.get("obfs-password", [""])[0]
        }
        
        if not data["sni"]:
             data["sni"] = data["server"]

        return data
    except Exception as e:
        print(f"Error parsing hy2 {link}: {e}")
        return None

def parse_tuic(link: str) -> Optional[Dict[str, Any]]:
    """Parses tuic:// links."""
    try:
        parsed = urllib.parse.urlparse(link)
        if parsed.scheme != "tuic":
            return None
        
        query = urllib.parse.parse_qs(parsed.query)
        
        data = {
            "type": "tuic",
            "name": urllib.parse.unquote(parsed.fragment) or "tuic_proxy",
            "server": parsed.hostname,
            "port": parsed.port,
            "uuid": parsed.username, 
            "password": parsed.password, 
            "sni": query.get("sni", [""])[0],
            "congestion_control": query.get("congestion_control", ["bbr"])[0],
            "udp_relay_mode": query.get("udp_relay_mode", ["native"])[0],
            "alpn": query.get("alpn", ["h3"])[0],
            "disable_sni": query.get("disable_sni", ["0"])[0] == "1",
            "insecure": query.get("allow_insecure", ["0"])[0] == "1"
        }
        
        if not data["sni"] and not data["disable_sni"]:
             data["sni"] = data["server"]
             
        return data
    except Exception as e:
        print(f"Error parsing tuic {link}: {e}")
        return None

def parse_link(link: str) -> Optional[Dict[str, Any]]:
    link = link.strip()
    if link.startswith("vmess://"):
        return parse_vmess(link)
    elif link.startswith("vless://") or link.startswith("trojan://"):
        return parse_vless_trojan(link)
    elif link.startswith("ss://"):
        return parse_ss(link)
    elif link.startswith("hy2://"):
        return parse_hysteria2(link)
    elif link.startswith("tuic://"):
        return parse_tuic(link)
    return None

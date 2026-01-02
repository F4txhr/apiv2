from src.parser import parse_link, safe_base64_decode
from src.converter import to_clash, to_singbox
import json
import base64
import urllib.parse

def test_safe_base64_decode():
    # Test standard Base64
    original = "Hello+World/123"
    encoded = base64.b64encode(original.encode()).decode()
    decoded = safe_base64_decode(encoded)
    assert decoded == original
    
    # Test URL-safe Base64
    original_safe = "Hello-World_123"
    encoded_safe = base64.urlsafe_b64encode(original_safe.encode()).decode()
    decoded_safe = safe_base64_decode(encoded_safe)
    assert decoded_safe == original_safe

def test_parse_vmess():
    # Construct a valid vmess link
    data = {
        "v": "2", "ps": "test_vmess", "add": "example.com", "port": "443",
        "id": "uuid-123", "aid": "0", "scy": "auto", "net": "ws",
        "type": "none", "host": "example.com", "path": "/ws", "tls": "tls"
    }
    encoded = base64.b64encode(json.dumps(data).encode()).decode()
    link = f"vmess://{encoded}"
    
    parsed = parse_link(link)
    assert parsed is not None
    assert parsed["type"] == "vmess"
    assert parsed["name"] == "test_vmess"
    assert parsed["network"] == "ws"
    assert parsed["tls"] is True

def test_parse_vless():
    link = "vless://uuid-123@example.com:443?security=tls&type=ws&path=%2Fws#test_vless"
    parsed = parse_link(link)
    assert parsed is not None
    assert parsed["type"] == "vless"
    assert parsed["server"] == "example.com"
    assert parsed["uuid"] == "uuid-123"
    assert parsed.get("tls") is True or parsed["security"] == "tls" # Logic adjustment depending on parser return
    assert parsed["network"] == "ws"

def test_parse_ss():
    # Test SIP002 format
    link = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@1.1.1.1:8388#test_ss"
    parsed = parse_link(link)
    assert parsed is not None
    assert parsed["type"] == "ss"
    assert parsed["server"] == "1.1.1.1"
    assert parsed["port"] == 8388
    assert parsed["cipher"] == "aes-256-gcm"
    assert parsed["password"] == "password"
    assert parsed["name"] == "test_ss"

def test_parse_ss_plugin():
    # Test SS with v2ray-plugin
    # plugin param: v2ray-plugin;mode=websocket;path=/ws;host=example.com
    plugin_data = "v2ray-plugin;mode=websocket;path=/ws;host=example.com"
    encoded_plugin = urllib.parse.quote(plugin_data)
    link = f"ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@1.1.1.1:8388/?plugin={encoded_plugin}#test_ss_plugin"
    
    parsed = parse_link(link)
    assert parsed is not None
    assert parsed["plugin"] == "v2ray-plugin"
    assert parsed["plugin_opts"]["mode"] == "websocket"
    assert parsed["plugin_opts"]["path"] == "/ws"
    assert parsed["plugin_opts"]["host"] == "example.com"

def test_converter_clash():
    proxies = [{
        "type": "vmess", "name": "test", "server": "1.1.1.1", "port": 443,
        "uuid": "u-u-i-d", "alterId": 0, "cipher": "auto", 
        "network": "ws", "path": "/", "host": "h", "tls": True
    }]
    output = to_clash(proxies)
    assert "proxies:" in output
    assert "name: test" in output
    assert "type: vmess" in output

def test_converter_clash_vless_ws():
    proxies = [{
        "type": "vless", "name": "test_vless", "server": "1.1.1.1", "port": 443,
        "uuid": "u-u-i-d", "security": "tls",
        "network": "ws", "path": "/chat", "host": "example.com", "sni": "example.com"
    }]
    output = to_clash(proxies)
    assert "type: vless" in output
    assert "network: ws" in output
    assert "ws-opts:" in output
    assert "path: /chat" in output
    assert "Host: example.com" in output

def test_converter_clash_ss():
    proxies = [{
        "type": "ss", "name": "test_ss", "server": "1.1.1.1", "port": 8388,
        "cipher": "aes-256-gcm", "password": "pass"
    }]
    output = to_clash(proxies)
    assert "type: ss" in output
    assert "cipher: aes-256-gcm" in output
    assert "password: pass" in output

def test_converter_clash_ss_plugin():
    proxies = [{
        "type": "ss", "name": "test_ss_plugin", "server": "1.1.1.1", "port": 8388,
        "cipher": "aes-256-gcm", "password": "pass",
        "plugin": "v2ray-plugin",
        "plugin_opts": {"mode": "websocket", "path": "/ws", "host": "example.com"}
    }]
    output = to_clash(proxies)
    assert "plugin: v2ray-plugin" in output
    assert "plugin-opts:" in output
    assert "mode: websocket" in output
    assert "path: /ws" in output

def test_converter_singbox():
    proxies = [{
        "type": "vmess", "name": "test", "server": "1.1.1.1", "port": 443,
        "uuid": "u-u-i-d", "alterId": 0, "cipher": "auto", 
        "network": "ws", "path": "/", "host": "h", "tls": True
    }]
    output = to_singbox(proxies)
    data = json.loads(output)
    assert "outbounds" in data
    assert data["outbounds"][0]["type"] == "vmess"
    assert data["outbounds"][0]["tag"] == "test"

def test_converter_singbox_ss():
    proxies = [{
        "type": "ss", "name": "test_ss", "server": "1.1.1.1", "port": 8388,
        "cipher": "aes-256-gcm", "password": "pass"
    }]
    output = to_singbox(proxies)
    data = json.loads(output)
    assert data["outbounds"][0]["type"] == "shadowsocks"
    assert data["outbounds"][0]["method"] == "aes-256-gcm"

def test_converter_singbox_ss_plugin():
    proxies = [{
        "type": "ss", "name": "test_ss_plugin", "server": "1.1.1.1", "port": 8388,
        "cipher": "aes-256-gcm", "password": "pass",
        "plugin": "v2ray-plugin",
        "plugin_opts": {"mode": "websocket", "path": "/ws", "host": "example.com"}
    }]
    output = to_singbox(proxies)
    data = json.loads(output)
    ob = data["outbounds"][0]
    assert ob["type"] == "shadowsocks"
    assert "transport" in ob
    assert ob["transport"]["type"] == "ws"
    assert ob["transport"]["path"] == "/ws"
    assert ob["transport"]["headers"]["Host"] == "example.com"

from src.parser import parse_link
from src.converter import to_clash, to_singbox
import json
import base64
import urllib.parse

def test_parse_hysteria2():
    # hy2://password@hostname:port?sni=sni.com&insecure=1&obfs=salamander&obfs-password=pass
    link = "hy2://password@example.com:443?sni=sni.example.com&insecure=1&obfs=salamander&obfs-password=pass#test_hy2"
    parsed = parse_link(link)
    assert parsed["type"] == "hysteria2"
    assert parsed["server"] == "example.com"
    assert parsed["password"] == "password"
    assert parsed["sni"] == "sni.example.com"
    assert parsed["insecure"] is True
    assert parsed["obfs"] == "salamander"
    assert parsed["obfs_password"] == "pass"

def test_parse_tuic():
    # tuic://uuid:password@hostname:port?sni=sni.com&congestion_control=bbr&udp_relay_mode=native&alpn=h3
    link = "tuic://uuid:password@example.com:443?sni=sni.example.com&congestion_control=bbr&alpn=h3#test_tuic"
    parsed = parse_link(link)
    assert parsed["type"] == "tuic"
    assert parsed["server"] == "example.com"
    assert parsed["uuid"] == "uuid"
    assert parsed["password"] == "password"
    assert parsed["sni"] == "sni.example.com"
    assert parsed["congestion_control"] == "bbr"
    assert parsed["alpn"] == "h3"

def test_converter_clash_hy2():
    proxies = [{
        "type": "hysteria2", "name": "test_hy2", "server": "1.1.1.1", "port": 443,
        "password": "pass", "sni": "sni.com", "insecure": True,
        "obfs": "salamander", "obfs_password": "obfs_pass"
    }]
    output = to_clash(proxies)
    assert "type: hysteria2" in output
    assert "password: pass" in output
    assert "sni: sni.com" in output
    assert "skip-cert-verify: true" in output
    assert "obfs: salamander" in output
    
def test_converter_singbox_hy2():
    proxies = [{
        "type": "hysteria2", "name": "test_hy2", "server": "1.1.1.1", "port": 443,
        "password": "pass", "sni": "sni.com", "insecure": True,
        "obfs": "salamander", "obfs_password": "obfs_pass"
    }]
    output = to_singbox(proxies)
    data = json.loads(output)
    ob = data["outbounds"][0]
    assert ob["type"] == "hysteria2"
    assert ob["password"] == "pass"
    assert ob["tls"]["server_name"] == "sni.com"
    assert ob["obfs"]["type"] == "salamander"

def test_converter_clash_tuic():
    proxies = [{
        "type": "tuic", "name": "test_tuic", "server": "1.1.1.1", "port": 443,
        "uuid": "uuid", "password": "pass", "sni": "sni.com", "congestion_control": "bbr"
    }]
    output = to_clash(proxies)
    assert "type: tuic" in output
    assert "uuid: uuid" in output
    assert "congestion-controller: bbr" in output

def test_converter_singbox_tuic():
    proxies = [{
        "type": "tuic", "name": "test_tuic", "server": "1.1.1.1", "port": 443,
        "uuid": "uuid", "password": "pass", "sni": "sni.com", "congestion_control": "bbr"
    }]
    output = to_singbox(proxies)
    data = json.loads(output)
    ob = data["outbounds"][0]
    assert ob["type"] == "tuic"
    assert ob["uuid"] == "uuid"
    assert ob["tls"]["server_name"] == "sni.com"

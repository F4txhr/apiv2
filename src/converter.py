from typing import List, Dict, Any
import yaml
import json
import re

# --- Config Templates ---

CLASH_FULL_TEMPLATE = {
    "port": 7890,
    "socks-port": 7891,
    "allow-lan": False,
    "mode": "rule",
    "log-level": "info",
    "external-controller": "127.0.0.1:9090",
    "dns": {
        "enable": True,
        "listen": "0.0.0.0:53",
        "enhanced-mode": "fake-ip",
        "fake-ip-range": "198.18.0.1/16",
        "nameserver": ["8.8.8.8", "1.1.1.1"],
        "fallback": ["https://dns.google/dns-query", "https://1.1.1.1/dns-query"]
    },
    "proxies": [],
    "proxy-groups": [
        {
            "name": "PROXY",
            "type": "select",
            "proxies": ["AUTO", "DIRECT"] # + all proxy names
        },
        {
            "name": "AUTO",
            "type": "url-test",
            "url": "http://www.gstatic.com/generate_204",
            "interval": 300,
            "proxies": [] # + all proxy names
        }
    ],
    "rules": [
        "GEOIP,ID,DIRECT",
        "GEOIP,CN,DIRECT",
        "MATCH,PROXY"
    ]
}

def _get_singbox_template():
    return {
        "log": {"level": "info", "timestamp": True},
        "dns": {
            "servers": [
                {"tag": "google", "address": "8.8.8.8", "detour": "direct"},
                {"tag": "local", "address": "local", "detour": "direct"}
            ],
            "rules": [
                {"outbound": "any", "server": "google"}
            ]
        },
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "0.0.0.0",
                "listen_port": 2080
            }
        ],
        "outbounds": [
            {
                "type": "selector",
                "tag": "PROXY",
                "outbounds": ["AUTO", "direct"] # + all proxy tags
            },
            {
                "type": "urltest",
                "tag": "AUTO",
                "outbounds": [], # + all proxy tags
                "url": "http://www.gstatic.com/generate_204",
                "interval": "5m",
                "tolerance": 50
            },
            {
                "type": "direct",
                "tag": "direct"
            },
            {
                "type": "block",
                "tag": "block"
            },
            {
                "type": "dns",
                "tag": "dns-out"
            }
        ],
        "route": {
            "rules": [
                {"protocol": "dns", "outbound": "dns-out"},
                {"geoip": ["cn", "private"], "outbound": "direct"},
                {"geosite": ["cn"], "outbound": "direct"}
            ],
            "auto_detect_interface": True
        }
    }

# --- Modifiers ---

def apply_modifiers(proxies: List[Dict[str, Any]], options: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Applies filters and modifiers to the list of proxies.
    Options:
    - filter_name: regex string to include
    - exclude_name: regex string to exclude
    - filter_protocol: string (vmess, vless, etc.)
    - force_sni: string to overwrite sni/host
    - udp_toggle: bool to force enable/disable udp
    - remove_expired: bool (checks regex YYYY-MM-DD in name)
    - add_emoji: bool (requires GeoIP data passed in? Skipping strictly here as it needs async/IP checking which is slow for bulk. Can be done if IP is known or simple lookup)
    """
    result = []
    import datetime

    for p in proxies:
        # 1. Protocol Filter
        if options.get("filter_protocol") and p["type"] != options.get("filter_protocol"):
            continue

        # 2. Name Filter (Include)
        if options.get("filter_name"):
            if not re.search(options["filter_name"], p["name"], re.IGNORECASE):
                continue

        # 3. Name Filter (Exclude)
        if options.get("exclude_name"):
            if re.search(options["exclude_name"], p["name"], re.IGNORECASE):
                continue

        # 4. Remove Expired (YYYY-MM-DD)
        if options.get("remove_expired"):
            match = re.search(r"(\d{4}-\d{2}-\d{2})", p["name"])
            if match:
                try:
                    exp_date = datetime.datetime.strptime(match.group(1), "%Y-%m-%d").date()
                    if exp_date < datetime.date.today():
                        continue # Skip expired
                except ValueError:
                    pass

        # 5. Force SNI/Host
        if options.get("force_sni"):
            sni = options["force_sni"]
            # Apply to known fields based on protocol
            if "sni" in p: p["sni"] = sni
            if "host" in p: p["host"] = sni
            if "servername" in p: p["servername"] = sni # clash vless
            # Also update plugin/transport opts if possible? 
            # Simplified: just top level SNI usually fixes most things.

        # 6. UDP Toggle
        if "udp_toggle" in options:
            p["udp"] = options["udp_toggle"] # For Clash
            # For Sing-box/Internal format, udp isn't always explicit in `p`, but `to_clash` uses it.
            # We add it to internal dict so converters can use it.

        # 7. Add Emoji (Simplified: just mock logic for now or skip if too complex without IP db)
        # Real implementation would need an IP-to-Country DB loaded. 
        # Skipping to keep it fast and synchronous.

        result.append(p)
        
    return result

# --- Converters ---

def to_clash(proxies: List[Dict[str, Any]], full: bool = False) -> str:
    clash_proxies = []
    proxy_names = []
    
    for p in proxies:
        proxy = {
            "name": p["name"],
            "type": p["type"],
            "server": p["server"],
            "port": p["port"],
        }
        
        # Apply generic UDP override if present
        if "udp" in p:
            proxy["udp"] = p["udp"]
        
        if p["type"] == "vmess":
            proxy["uuid"] = p["uuid"]
            proxy["alterId"] = p["alterId"]
            proxy["cipher"] = p["cipher"]
            if p.get("tls"):
                proxy["tls"] = True
            if p.get("network"):
                proxy["network"] = p["network"]
            if p.get("path") and p["network"] in ["ws", "h2", "grpc"]:
                 proxy[f"{p['network']}-opts"] = {"path": p["path"]}
                 if p.get("host"):
                     proxy[f"{p['network']}-opts"]["headers"] = {"Host": p["host"]}
            if "udp" not in proxy: proxy["udp"] = True

        elif p["type"] == "vless":
            proxy["uuid"] = p["uuid"]
            if p.get("security") == "tls":
                proxy["tls"] = True
            if p.get("flow"):
                proxy["flow"] = p["flow"]
            if p.get("network"):
                proxy["network"] = p["network"]
            if p.get("sni"):
                proxy["servername"] = p["sni"]
            
            # Handle transport options
            if p.get("path") and p.get("network") in ["ws", "h2", "grpc"]:
                 proxy[f"{p['network']}-opts"] = {"path": p["path"]}
                 if p.get("host"):
                     proxy[f"{p['network']}-opts"]["headers"] = {"Host": p["host"]}
            
            if "udp" not in proxy: proxy["udp"] = True
            
        elif p["type"] == "trojan":
            proxy["password"] = p["password"]
            if p.get("sni"):
                proxy["sni"] = p["sni"]
            if "udp" not in proxy: proxy["udp"] = True

        elif p["type"] == "ss":
            proxy["cipher"] = p["cipher"]
            proxy["password"] = p["password"]
            if "udp" not in proxy: proxy["udp"] = True
            if p.get("plugin"):
                proxy["plugin"] = p["plugin"]
                if p.get("plugin_opts"):
                    proxy["plugin-opts"] = p["plugin_opts"]

        elif p["type"] == "hysteria2":
             # Clash Meta (Mihomo) uses 'hysteria2'
             proxy["password"] = p["password"]
             if p.get("sni"):
                 proxy["sni"] = p["sni"]
             if p.get("insecure"):
                 proxy["skip-cert-verify"] = True
             if p.get("obfs"):
                 proxy["obfs"] = p["obfs"]
                 proxy["obfs-password"] = p.get("obfs_password")
             if "udp" not in proxy: proxy["udp"] = True

        elif p["type"] == "tuic":
             # Clash Meta (Mihomo) uses 'tuic'
             proxy["uuid"] = p["uuid"]
             proxy["password"] = p["password"]
             if p.get("sni"):
                 proxy["sni"] = p["sni"]
             if p.get("insecure"):
                 proxy["skip-cert-verify"] = True
             proxy["congestion-controller"] = p.get("congestion_control", "bbr")
             proxy["udp-relay-mode"] = p.get("udp_relay_mode", "native")
             if p.get("alpn"):
                 proxy["alpn"] = [p["alpn"]] # Clash expects list
             if p.get("disable_sni"):
                 proxy["disable-sni"] = True
             if "udp" not in proxy: proxy["udp"] = True

        clash_proxies.append(proxy)
        proxy_names.append(proxy["name"])

    if full:
        import copy
        config = copy.deepcopy(CLASH_FULL_TEMPLATE)
        config["proxies"] = clash_proxies
        # Add proxies to groups
        for group in config["proxy-groups"]:
            if group["name"] in ["PROXY", "AUTO"]:
                group["proxies"].extend(proxy_names)
        return yaml.dump(config, sort_keys=False)
    else:
        return yaml.dump({"proxies": clash_proxies}, sort_keys=False)

def to_singbox(proxies: List[Dict[str, Any]], full: bool = False) -> str:
    outbounds = []
    proxy_tags = []
    
    for p in proxies:
        outbound = {
            "type": p["type"],
            "tag": p["name"],
            "server": p["server"],
            "server_port": p["port"],
        }

        if p["type"] == "vmess":
            outbound["uuid"] = p["uuid"]
            outbound["security"] = "auto"
            outbound["alter_id"] = p["alterId"]
            if p.get("tls"):
                outbound["tls"] = {"enabled": True, "server_name": p.get("sni")}
            
            transport = {}
            if p.get("network") == "ws":
                transport["type"] = "ws"
                transport["path"] = p.get("path")
                if p.get("host"):
                     transport["headers"] = {"Host": p.get("host")}
            
            if transport:
                outbound["transport"] = transport

        elif p["type"] == "vless":
             outbound["uuid"] = p["uuid"]
             if p.get("flow"):
                 outbound["flow"] = p["flow"]
             
             tls_conf = {"enabled": False}
             if p.get("security") == "tls":
                 tls_conf["enabled"] = True
                 if p.get("sni"):
                     tls_conf["server_name"] = p.get("sni")
             outbound["tls"] = tls_conf
             
             # simplified transport handling
             if p.get("network") == "ws":
                 outbound["transport"] = {"type": "ws", "path": p.get("path")}

        elif p["type"] == "trojan":
            outbound["password"] = p["password"]
            if p.get("sni"):
                 outbound["tls"] = {"enabled": True, "server_name": p.get("sni")}
            else:
                 outbound["tls"] = {"enabled": True}

        elif p["type"] == "ss":
            outbound["type"] = "shadowsocks" # sing-box uses 'shadowsocks' instead of 'ss'
            outbound["method"] = p["cipher"]
            outbound["password"] = p["password"]
            
            # Map SS plugins to Sing-box transport
            if p.get("plugin") == "v2ray-plugin":
                 opts = p.get("plugin_opts", {})
                 # v2ray-plugin usually implies websocket or quic
                 # mode=websocket is default or explicit
                 mode = opts.get("mode", "websocket")
                 
                 transport = {}
                 if mode == "websocket":
                     transport["type"] = "ws"
                     if opts.get("path"):
                         transport["path"] = opts.get("path")
                     if opts.get("host"):
                         transport["headers"] = {"Host": opts.get("host")}
                         
                 # Only add transport if we successfully mapped it. 
                 # Sing-box doesn't support generic 'plugin' binary execution in the same way.
                 if transport:
                     outbound["transport"] = transport

        elif p["type"] == "hysteria2":
             outbound["password"] = p["password"]
             if p.get("obfs"):
                 outbound["obfs"] = {
                     "type": p["obfs"],
                     "password": p.get("obfs_password")
                 }
             
             tls = {"enabled": True}
             if p.get("sni"):
                 tls["server_name"] = p["sni"]
             if p.get("insecure"):
                 tls["insecure"] = True
             outbound["tls"] = tls

        elif p["type"] == "tuic":
             outbound["uuid"] = p["uuid"]
             outbound["password"] = p["password"]
             outbound["congestion_control"] = p.get("congestion_control", "bbr")
             outbound["udp_relay_mode"] = p.get("udp_relay_mode", "native")
             if p.get("disable_sni"):
                 outbound["disable_sni"] = True
             
             tls = {"enabled": True}
             if p.get("sni"):
                 tls["server_name"] = p["sni"]
             if p.get("insecure"):
                 tls["insecure"] = True
             if p.get("alpn"):
                 tls["alpn"] = [p["alpn"]]
             outbound["tls"] = tls

        outbounds.append(outbound)
        proxy_tags.append(outbound["tag"])
    
    if full:
        config = _get_singbox_template()
        for ob in reversed(outbounds):
            config["outbounds"].insert(0, ob)
            
        for ob in config["outbounds"]:
            if ob["tag"] in ["PROXY", "AUTO"] and "outbounds" in ob:
                ob["outbounds"].extend(proxy_tags)
                
        return json.dumps(config, indent=2)
    else:
        return json.dumps({"outbounds": outbounds}, indent=2)

from typing import List, Dict, Any
import yaml
import json

def to_clash(proxies: List[Dict[str, Any]]) -> str:
    clash_proxies = []
    
    for p in proxies:
        proxy = {
            "name": p["name"],
            "type": p["type"],
            "server": p["server"],
            "port": p["port"],
        }
        
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
            # UDP defaults to true usually for clash
            proxy["udp"] = True

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
            
            proxy["udp"] = True
            
        elif p["type"] == "trojan":
            proxy["password"] = p["password"]
            if p.get("sni"):
                proxy["sni"] = p["sni"]
            proxy["udp"] = True

        elif p["type"] == "ss":
            proxy["cipher"] = p["cipher"]
            proxy["password"] = p["password"]
            proxy["udp"] = True
            if p.get("plugin"):
                proxy["plugin"] = p["plugin"]
                if p.get("plugin_opts"):
                    proxy["plugin-opts"] = p["plugin_opts"]

        clash_proxies.append(proxy)

    return yaml.dump({"proxies": clash_proxies}, sort_keys=False)

def to_singbox(proxies: List[Dict[str, Any]]) -> str:
    outbounds = []
    
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

        outbounds.append(outbound)
    
    return json.dumps({"outbounds": outbounds}, indent=2)

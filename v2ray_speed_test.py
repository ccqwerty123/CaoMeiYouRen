import json
import base64
import subprocess
import time
import requests
import os

def decode_vmess(vmess_url):
    encoded_config = vmess_url.split("://")[1]
    config_json = base64.b64decode(encoded_config).decode('utf-8')
    return json.loads(config_json)

def create_config(vmess_config):
    config = {
        "inbounds": [{
            "port": 1080,
            "protocol": "socks",
            "sniffing": {
                "enabled": True,
                "destOverride": ["http", "tls"]
            },
            "settings": {
                "auth": "noauth"
            }
        }],
        "outbounds": [{
            "protocol": "vmess",
            "settings": {
                "vnext": [{
                    "address": vmess_config["add"],
                    "port": int(vmess_config["port"]),
                    "users": [{
                        "id": vmess_config["id"],
                        "alterId": int(vmess_config["aid"])
                    }]
                }]
            },
            "streamSettings": {
                "network": vmess_config["net"],
                "wsSettings": {
                    "path": vmess_config["path"],
                    "headers": {
                        "Host": vmess_config["host"]
                    }
                }
            }
        }]
    }
    
    with open('config.json', 'w') as f:
        json.dump(config, f)

def get_ip(proxies=None):
    try:
        response = requests.get("http://ip-api.com/json/", proxies=proxies, timeout=10)
        if response.status_code == 200:
            return response.json()["query"]
        else:
            return None
    except requests.exceptions.RequestException:
        return None

def test_node(vmess_url):
    vmess_config = decode_vmess(vmess_url)
    create_config(vmess_config)
    
    print("获取原始 IP...")
    original_ip = get_ip()
    print(f"原始 IP: {original_ip}")
    
    print("启动 Xray...")
    xray_path = os.path.join(os.getcwd(), 'xray')
    xray_process = subprocess.Popen([xray_path, "run", "-c", "config.json"])
    time.sleep(5)  # 给 Xray 一些启动时间
    
    proxies = {
        "http": "socks5://127.0.0.1:1080",
        "https": "socks5://127.0.0.1:1080"
    }
    
    print("通过代理获取 IP...")
    proxy_ip = get_ip(proxies)
    print(f"代理 IP: {proxy_ip}")
    
    if proxy_ip and proxy_ip != original_ip:
        print("节点可用: IP 地址已更改")
    else:
        print("节点不可用或出现错误")
    
    xray_process.terminate()
    xray_process.wait()

# 使用示例
vmess_url = "vmess://ew0KICAidiI6ICIyIiwNCiAgInBzIjogIlx1ODFFQVx1OTAwOSBoYXgtY2xvbmUiLA0KICAiYWRkIjogImNmLjBzbS5jb20iLA0KICAicG9ydCI6ICI4MCIsDQogICJpZCI6ICIzMzgwOWNkNC0zMDk1LTQ0N2QtZGI2Ny0wZTYwN2RkMjNkNWIiLA0KICAiYWlkIjogIjAiLA0KICAic2N5IjogImF1dG8iLA0KICAibmV0IjogIndzIiwNCiAgInR5cGUiOiAibm9uZSIsDQogICJob3N0IjogInZwcy54aW5jZXMwMDEuZmlsZWdlYXItc2cubWUiLA0KICAicGF0aCI6ICIvIiwNCiAgInRscyI6ICIiLA0KICAic25pIjogIiIsDQogICJhbHBuIjogIiIsDQogICJmcCI6ICIiDQp9"

if __name__ == "__main__":
    test_node(vmess_url)

import subprocess
import json
import os
import datetime
import base64
import requests

def get_xray_speed_and_verify():
    vmess_config = {
       "v": "2",
       "ps": "\\u52A0\\u62FF\\u5927",
       "add": "cdn2.bpcdn.cc",
       "port": "2086",
       "id": "6f42cfe5-64f1-466d-8860-859d8e0f0a98",
       "aid": "0",
       "scy": "auto",
       "net": "ws",
       "type": "none",
       "host": "cae3mg9qsg55eo5lhq.lovebaipiao.com",
       "path": "/",
       "tls": "",
       "sni": "",
       "alpn": "",
       "fp": ""
    }

    address = vmess_config["add"]
    port = vmess_config["port"]
    id = vmess_config["id"]
    alterId = vmess_config["aid"]
    security = vmess_config["scy"]
    net = vmess_config["net"]
    type = vmess_config["type"]
    host = vmess_config["host"]
    path = vmess_config["path"]
    tls = vmess_config["tls"]

    config = {
        "log": {
            "loglevel": "warning"
        },
        "inbounds": [
            {
                "port": 0,
                "protocol": "socks",
                "settings": {
                    "auth": "noauth"
                }
            }
        ],
        "outbounds": [
            {
                "protocol": "vmess",
                "settings": {
                    "vnext": [
                        {
                            "address": address,
                            "port": int(port),
                            "users": [
                                {
                                    "id": id,
                                    "alterId": int(alterId),
                                    "security": security
                                }
                            ]
                        }
                    ]
                },
               "streamSettings": {
                   "network": net,
                    "wsSettings": {
                        "path": path,
                        "headers": {
                            "Host": host
                           }
                       }
                  },
                "tag": "proxy"
            }
        ]
    }
    
    config_file = "xray_config.json"
    with open(config_file, "w") as f:
        json.dump(config, f)
    
    try:
         # 1. 测试代理是否正常运行
        print("Testing Proxy...")
        try:
            proxies = {
                "http": "socks5://127.0.0.1:0",
                "https": "socks5://127.0.0.1:0"
            }
            response = requests.get("https://api.ipify.org", proxies=proxies, timeout=10)
            response.raise_for_status() # 如果响应不是 200，会抛出异常
            print(f"Proxy test passed, IP: {response.text.strip()}")
        except requests.exceptions.RequestException as e:
            print(f"Proxy test failed: {e}")
            return None

        # 2. 进行速度测试
        print("Starting speed test...")
        result = subprocess.run(
            ["xctl", "api", "stats.query", "--server=127.0.0.1:10085","inbound.socks.user.traffic","outbound.proxy.user.traffic"],
            capture_output=True,
            text=True,
            check=True,
            env=os.environ.copy(),
        )
        if result.returncode != 0:
           print(f"Error: xctl failed with code {result.returncode}, output: {result.stderr}")
           return None

        initial_stats = json.loads(result.stdout.strip())
        initial_inbound_traffic = initial_stats["stat"][0]["value"] if len(initial_stats["stat"]) > 0 else 0
        initial_outbound_traffic = initial_stats["stat"][1]["value"] if len(initial_stats["stat"]) > 1 else 0

       # 发起一些流量
        test_speed_result = subprocess.run(
            ["curl","-v","https://www.google.com","--proxy","socks5://127.0.0.1:0"],
            capture_output=True,
            text=True,
            check=False,
            env=os.environ.copy(),
        )
        if test_speed_result.returncode != 0:
            print(f"Error: speed test failed with code {test_speed_result.returncode}, output: {test_speed_result.stderr}")
            return None
        
        # 获取结束流量
        result_after = subprocess.run(
            ["xctl", "api", "stats.query", "--server=127.0.0.1:10085","inbound.socks.user.traffic","outbound.proxy.user.traffic"],
            capture_output=True,
            text=True,
            check=True,
            env=os.environ.copy(),
        )
        if result_after.returncode != 0:
            print(f"Error: xctl failed with code {result_after.returncode}, output: {result_after.stderr}")
            return None
        
        after_stats = json.loads(result_after.stdout.strip())
        after_inbound_traffic = after_stats["stat"][0]["value"] if len(after_stats["stat"]) > 0 else 0
        after_outbound_traffic = after_stats["stat"][1]["value"] if len(after_stats["stat"]) > 1 else 0
        
        inbound_diff = after_inbound_traffic - initial_inbound_traffic
        outbound_diff = after_outbound_traffic - initial_outbound_traffic

        return {
           "inbound_traffic_bytes": inbound_diff,
           "outbound_traffic_bytes": outbound_diff,
        }
    except subprocess.CalledProcessError as e:
        print(f"Error: subprocess failed: {e}")
        return None
    except Exception as e:
        print(f"Error:  failed: {e}")
        return None
    finally:
       if os.path.exists(config_file):
        os.remove(config_file)



if __name__ == "__main__":
    speed_data = get_xray_speed_and_verify()
    if speed_data:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Speed Test Result {current_time}:")
        print(f"  Inbound traffic: {speed_data['inbound_traffic_bytes']} bytes")
        print(f"  Outbound traffic: {speed_data['outbound_traffic_bytes']} bytes")

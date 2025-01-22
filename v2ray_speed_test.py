import subprocess
import json
import os
import datetime
import requests
import time

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
    
    xray_socks_port = 1080 # Hardcoded socks proxy port
    xray_config_file = "xray_config.json" # 设置文件名
    
    # 查找 xray_config.json 文件
    print("Searching for xray_config.json...")
    
    found_files = []
    for root, _, files in os.walk(os.getcwd()):
      for file in files:
        if file == xray_config_file:
          found_files.append(os.path.join(root, file))
          
    if len(found_files) == 0:
        print(f"Error: Could not find '{xray_config_file}' in the current directory and its subdirectories.")
        return None
    
    if len(found_files) > 1:
      print(f"Warning: Found multiple '{xray_config_file}' files. Using the first one: '{found_files[0]}'")
    
    xray_config_file = found_files[0] # 更新路径为找到的路径
    print(f"Found '{xray_config_file}'.")


    try:
         # 加载 Xray 配置文件
        print(f"Loading Xray config from: {xray_config_file}...")
        with open(xray_config_file, "r") as f:
            config = json.load(f)
        
        # 修改 outbounds
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
        config["inbounds"][0]["port"] = xray_socks_port
        config["outbounds"][0] =  {
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
        # 保存配置文件
        with open(xray_config_file, "w") as f:
            json.dump(config, f,indent=4)
        print(f"Xray config has been modified at : {xray_config_file}")
        # 获取本机 IP
        print("Getting direct IP...")
        try:
            direct_ip = requests.get("https://api.ipify.org", timeout=10).text.strip()
            print(f"Direct IP: {direct_ip}")
        except requests.exceptions.RequestException as e:
            print(f"Error getting direct IP: {e}")
            return None

         # 1. 测试代理是否正常运行
        print("Testing Proxy...")
        try:
            proxies = {
                "http": f"socks5://127.0.0.1:{xray_socks_port}",
                "https": f"socks5://127.0.0.1:{xray_socks_port}"
            }
            proxy_ip = requests.get("https://api.ipify.org", proxies=proxies, timeout=10).text.strip()
            print(f"Proxy test passed, IP: {proxy_ip}")
            if direct_ip == proxy_ip:
                print("Proxy test failed: direct IP and proxy IP are the same.")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Proxy test failed: {e}")
            return None

        # 2. 进行速度测试
        print("Starting speed test...")
        xctl_path = os.path.join(os.getcwd(), "xctl")  # 获取 xctl 的绝对路径
        result = subprocess.run(
            [xctl_path, "api", "stats.query", "--server=127.0.0.1:10085","outbound.proxy.user.traffic","outbound.direct.user.traffic"],
            capture_output=True,
            text=True,
            check=True,
            env=os.environ.copy(),
        )
        if result.returncode != 0:
           print(f"Error: xctl failed with code {result.returncode}, output: {result.stderr}")
           return None

        initial_stats = json.loads(result.stdout.strip())
        initial_outbound_proxy_traffic = initial_stats["stat"][0]["value"] if len(initial_stats["stat"]) > 0 else 0
        initial_outbound_direct_traffic = initial_stats["stat"][1]["value"] if len(initial_stats["stat"]) > 1 else 0

       # 发起一些流量
        test_speed_result = subprocess.run(
            ["curl","-v","https://www.google.com","--proxy",f"socks5://127.0.0.1:{xray_socks_port}"],
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
            [xctl_path, "api", "stats.query", "--server=127.0.0.1:10085","outbound.proxy.user.traffic","outbound.direct.user.traffic"],
            capture_output=True,
            text=True,
            check=True,
            env=os.environ.copy(),
        )
        if result_after.returncode != 0:
            print(f"Error: xctl failed with code {result_after.returncode}, output: {result_after.stderr}")
            return None
        
        after_stats = json.loads(result_after.stdout.strip())
        after_outbound_proxy_traffic = after_stats["stat"][0]["value"] if len(after_stats["stat"]) > 0 else 0
        after_outbound_direct_traffic = after_stats["stat"][1]["value"] if len(after_stats["stat"]) > 1 else 0
        
        outbound_proxy_diff = after_outbound_proxy_traffic - initial_outbound_proxy_traffic
        outbound_direct_diff = after_outbound_direct_traffic - initial_outbound_direct_traffic
        return {
           "outbound_proxy_bytes": outbound_proxy_diff,
           "outbound_direct_bytes": outbound_direct_diff,
        }
    except subprocess.CalledProcessError as e:
        print(f"Error: subprocess failed: {e}")
        return None
    except Exception as e:
        print(f"Error:  failed: {e}")
        return None


if __name__ == "__main__":
    speed_data = get_xray_speed_and_verify()
    if speed_data:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Speed Test Result {current_time}:")
        print(f"  Outbound proxy traffic: {speed_data['outbound_proxy_bytes']} bytes")
        print(f"  Outbound direct traffic: {speed_data['outbound_direct_bytes']} bytes")

import subprocess
import json
import os
import datetime
import requests
import time
import base64

def get_xray_speed_and_verify():
    vmess_configs = [
    "vmess://ew0KICAidiI6ICIyIiwNCiAgInBzIjogIlx1NTJBMFx1NjJGRlx1NTkyNzIiLA0KICAiYWRkIjogImNkbjIuYnBjZG4uY2MiLA0KICAicG9ydCI6ICIyMDg2IiwNCiAgImlkIjogIjZmNDJjZmU1LTY0ZjEtNDY2ZC04ODYwLTg1OWQ4ZTBmMGE5OCIsDQogICJhaWQiOiAiMCIsDQogICJzY3kiOiAiYXV0byIsDQogICJuZXQiOiAid3MiLA0KICAidHlwZSI6ICJub25lIiwNCiAgImhvc3QiOiAiY2FlM21nOXFzZzU1ZW81bGhxLmxvdmViYWlwaWFvLmNvbSIsDQogICJwYXRoIjogIi8iLA0KICAidGxzIjogIiIsDQogICJzbmkiOiAiIiwNCiAgImFscG4iOiAiIiwNCiAgImZwIjogIiINCn0=",
    "vmess://another_base64_encoded_vmess_config"  # 你可以在这里添加更多的节点
    ]
    results = []
    xray_socks_port = 1080  # Hardcoded socks proxy port
    xray_config_file = os.path.join(os.getcwd(), "config.json")  # 设置文件名和路径
    xray_path = os.path.join(os.getcwd(), "xray")  # 获取 xray 的绝对路径
    xctl_path = os.path.join(os.getcwd(), "xctl")  # 获取 xctl 的绝对路径

    # 确保 xray 可执行文件存在
    if not os.path.exists(xray_path):
      print(f"Error: Could not find 'xray' executable at '{xray_path}'.")
      return None
    
    # 确保 xctl 可执行文件存在
    if not os.path.exists(xctl_path):
      print(f"Error: Could not find 'xctl' executable at '{xctl_path}'.")
      return None
    
    # 启动 Xray
    print("Starting Xray...")
    xray_process = subprocess.Popen(
                [xray_path, "-c", xray_config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                )
    time.sleep(5)


    for vmess_b64 in vmess_configs:
        try:
           vmess_json_str = base64.b64decode(vmess_b64).decode("utf-8")
           vmess_config = json.loads(vmess_json_str)
        except Exception as e:
            print(f"Error: Failed to decode or parse Vmess config: {e}")
            continue # 如果解析失败，跳过这个节点

        print(f"Testing Vmess config: {vmess_config.get('ps','')}")

        # 创建 Xray config.json 文件
        print(f"Creating Xray config file at: {xray_config_file}...")
        
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
                "inbounds": [{
                    "port": xray_socks_port,
                    "protocol": "socks",
                    "settings": {
                        "auth": "noauth"
                    }
                }],
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
                    },
                  {
                      "protocol": "freedom",
                      "settings": {},
                      "tag": "direct"
                   }
                ],
                 "routing": {
                        "rules": [
                            {
                                "type": "field",
                                "outboundTag": "proxy",
                                "domain": [ "geosite:category-ads-all" ],
                            },
                             {
                                "type": "field",
                                "outboundTag": "direct",
                                 "domain": [
                                  "geosite:cn",
                                 ],
                            }
                        ]
                 }
            }
       
        with open(xray_config_file, "w") as f:
            json.dump(config, f, indent=4)
        print(f"Xray config file has been created at : {xray_config_file}")


        try:
             # 获取本机 IP
            print("Getting direct IP...")
            try:
                direct_ip = requests.get("https://api.ipify.org", timeout=10).text.strip()
                print(f"Direct IP: {direct_ip}")
            except requests.exceptions.RequestException as e:
                print(f"Error getting direct IP: {e}")
                continue


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
                     continue
            except requests.exceptions.RequestException as e:
               print(f"Proxy test failed: {e}")
               continue

           # 2. 进行速度测试
            print("Starting speed test...")
            result = subprocess.run(
                [xctl_path, "api", "stats.query", "--server=127.0.0.1:10085","outbound.proxy.user.traffic","outbound.direct.user.traffic"],
                capture_output=True,
                text=True,
                check=True,
                env=os.environ.copy(),
            )
            if result.returncode != 0:
                print(f"Error: xctl failed with code {result.returncode}, output: {result.stderr}")
                continue

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
                continue

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
                continue

            after_stats = json.loads(result_after.stdout.strip())
            after_outbound_proxy_traffic = after_stats["stat"][0]["value"] if len(after_stats["stat"]) > 0 else 0
            after_outbound_direct_traffic = after_stats["stat"][1]["value"] if len(after_stats["stat"]) > 1 else 0

            outbound_proxy_diff = after_outbound_proxy_traffic - initial_outbound_proxy_traffic
            outbound_direct_diff = after_outbound_direct_traffic - initial_outbound_direct_traffic
            results.append(
                {
                    "vmess_config": vmess_config.get('ps',''),
                    "outbound_proxy_bytes": outbound_proxy_diff,
                    "outbound_direct_bytes": outbound_direct_diff,
                 }
            )
        except Exception as e:
           print(f"Error:  failed: {e}")
        finally:
            # 使用API重载配置
            print("Reloading Xray config...")
            try:
               reload_result = subprocess.run(
                [xctl_path, "api", "handler.reload", "--server=127.0.0.1:10085"],
                capture_output=True,
                text=True,
                check=True,
                env=os.environ.copy(),
                )
               if reload_result.returncode != 0:
                   print(f"Error: Xray reload failed with code {reload_result.returncode}, output: {reload_result.stderr}")
            except Exception as e:
               print(f"Error: Reload config failed: {e}")
            if os.path.exists(xray_config_file):
                os.remove(xray_config_file)

    # 停止 Xray
    print("Stopping Xray...")
    xray_process.terminate()
    xray_process.wait()
    return results


if __name__ == "__main__":
   
    speed_data_list = get_xray_speed_and_verify()
    if speed_data_list:
             current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
             print(f"Speed Test Result {current_time}:")
             for data in speed_data_list:
                print(f"  Node: {data['vmess_config']}")
                print(f"  Outbound proxy traffic: {data['outbound_proxy_bytes']} bytes")
                print(f"  Outbound direct traffic: {data['outbound_direct_bytes']} bytes")

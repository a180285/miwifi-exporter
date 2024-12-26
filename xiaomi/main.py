from sys import stdout

import requests
import re
import time
import random
import json
import hashlib
import traceback

from prometheus_client import Gauge
import prometheus_client
from requests.adapters import HTTPAdapter
import configparser

device_download_bytes = Gauge("device_download_bytes", "device download bytes", ["mac", "devname", "isap"])
device_upload_bytes = Gauge("device_upload_bytes", "device upload bytes", ["mac", "devname", "isap"])
device_online_time = Gauge("device_online_time", "device online time", ["mac", "devname", "isap"])

wan_download_bytes = Gauge("wan_download_bytes", "wan download bytes", ["devname"])
wan_upload_bytes = Gauge("wan_upload_bytes", "wan upload bytes", ["devname"])


device_count = Gauge("device_count", "device count", ["type"])

router_mem_usage = Gauge("router_mem_usage", "router mem usage", ["total", "hz", "type"])
router_hardware_version = Gauge("router_hardware_version", "router hardware version", ["version", "displayName"])
router_up_time = Gauge("router_up_time", "router up time")

# 读取配置
config = configparser.ConfigParser()
config.read('config.ini')
password = config.get('config', 'PASSWORD')
route_ip = config.get('config', 'ROUTE_IP')
sleep_time = config.getint('config', 'SLEEP_TIME')
exporter_port = config.getint('config', 'EXPORTER_PORT')
max_retries = config.getint('config', 'MAX_RETRIES')
timeout = config.getint('config', 'TIMEOUT')

# 创建请求对象
s = requests.Session()
s.mount('http://', HTTPAdapter(max_retries=max_retries))
s.mount('https://', HTTPAdapter(max_retries=max_retries))

# 定义根url
route_url = 'http://' + route_ip


# 模拟登陆获取token
def get_token():
    # 获取nonce和mac_addr

    req = s.get(route_url + '/cgi-bin/luci/web', timeout=timeout)
    key = re.findall(r'key: \'(.*)\',', req.text)[0]
    mac_addr = re.findall(r'deviceId = \'(.*)\';', req.text)[0]
    nonce = "0_" + mac_addr + "_" + str(int(time.time())) + "_" + str(random.randint(1000, 10000))

    # 第一次加密 对应CryptoJS.SHA1(pwd + this.key)
    password_encrypt1 = hashlib.sha256((password + key).encode('utf-8')).hexdigest()

    # 第二次加密对应 CryptoJS.SHA1(this.nonce + CryptoJS.SHA1(pwd + this.key).toString()).toString();
    hexpwd = hashlib.sha256((nonce + password_encrypt1).encode('utf-8')).hexdigest()

    data = {
        "logtype": 2,
        "nonce": nonce,
        "password": hexpwd,
        "username": "admin"
    }

    url = route_url + '/cgi-bin/luci/api/xqsystem/login'

    response = s.post(url=url, data=data, timeout=timeout)
    res = json.loads(response.content)
    if res['code'] == 0:
        token = res['token']
        print(f'login token: {token}')
        return token
    else:
        print(f"login failed! {res}")
        raise Exception("login failed!")


def update_route_status(token):
    url = route_url + '/cgi-bin/luci/;stok=' + token + '/api/misystem/status'
    req = s.get(url, timeout=(timeout, timeout))
    route_status = json.loads(req.content)

    for device in route_status["dev"]:
        isap = "1"
        if 'isap' in device:
            isap = device["isap"]
        device_download_bytes.labels(device["mac"], device["devname"], isap).set(device["download"])
        device_upload_bytes.labels(device["mac"], device["devname"], isap).set(device["upload"])
        device_online_time.labels(device["mac"], device["devname"], isap).set(device["online"])

    wan_download_bytes.labels(route_status["wan"]["download"]).set(route_status["wan"]["download"])
    wan_upload_bytes.labels(route_status["wan"]["upload"]).set(route_status["wan"]["upload"])
    
    for device_type in route_status["count"]:
        device_count.labels(device_type).set(route_status["count"][device_type])

    router_mem_usage.labels(route_status["mem"]["total"], route_status["mem"]["hz"], route_status["mem"]["type"]).set(route_status["mem"]["usage"])
    router_hardware_version.labels(route_status["hardware"]["version"], route_status["hardware"]["displayName"]).set(1)
    router_up_time.set(route_status["upTime"])

if __name__ == '__main__':
    prometheus_client.start_http_server(exporter_port)
    print("server start at " + str(exporter_port))
    print("blog: www.bboy.app")

    while True:
        try:
            token = get_token()
            update_route_status(token)
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} update route status success")
        except Exception as e:
            print(f"update route status failed! {e}")
            print(traceback.format_exc())
        stdout.flush()
        time.sleep(sleep_time)

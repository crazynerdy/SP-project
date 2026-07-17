# -*- coding: utf-8 -*-
import time, re, base64, json
import requests
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from core.envutil import require

BASE = require("IDSTE_BASE")
USERNAME = require("IDSTE_USERNAME")
PASSWORD = require("IDSTE_PASSWORD")
PUBKEY_PEM = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDUxDBQSUSqCf9TbhIGTwYvsJ36
V5STG4xeYr19kZhITNnmExWOA2ugkWzKTte3WMTngUJrJZsLK1yUPx5J4mpq0fSH
GG8AowLesnEYUJPnysLJW3TFu4wBu4foUBc/e+kbSAEBpbwnb/3s0u/Zjw0E3nh0
+WmKS2BHV6ptk/EiUQIDAQAB
-----END PUBLIC KEY-----"""

def main():
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0"})
    r = s.get(f"{BASE}/login/?next=/", timeout=20)
    _m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text)
    if not _m:
        raise RuntimeError(f"登录页未找到 csrf token（状态 {r.status_code}），响应前200字: {r.text[:200]}")
    csrf = _m.group(1)
    pub = load_pem_public_key(PUBKEY_PEM.encode())
    en_pwd = base64.b64encode(pub.encrypt(PASSWORD.encode(), padding.PKCS1v15())).decode()
    s.post(f"{BASE}/user_login_check/?next=/",
           data={"csrfmiddlewaretoken": csrf, "username": USERNAME, "pw": en_pwd, "vc": str(int(time.time()*1000))},
           headers={"Referer": f"{BASE}/login/?next=/"}, timeout=25)
    print("sessionid:", s.cookies.get("sessionid"))

    # 试 1: 用 session cookie 直接打 discover
    print("\n=== try1: session cookie ===")
    r = s.get(f"{BASE}/mcp/admin/api/discover", timeout=25)
    print("status:", r.status_code, "ctype:", r.headers.get("Content-Type"), "len:", len(r.text))
    print(r.text[:800])

    # 试 2: 用 API Key（从 .env 读取）
    for key in [require("IDSTE_API_KEY")]:
        print(f"\n=== try2: api key {key[:24]}... ===")
        r = s.get(f"{BASE}/mcp/admin/api/discover", headers={"X-MCP-API-Key": key}, timeout=25)
        print("status:", r.status_code, "ctype:", r.headers.get("Content-Type"), "len:", len(r.text))
        print(r.text[:800])
        if r.headers.get("Content-Type","").startswith("application/json") and r.text.strip().startswith("{"):
            break


if __name__ == "__main__":
    main()

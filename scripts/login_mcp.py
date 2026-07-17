# -*- coding: utf-8 -*-
import time, json, base64, sys
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

    # 1. 取登录页 + csrf cookie
    r = s.get(f"{BASE}/login/?next=/", timeout=20)
    import re
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text)
    if not m:
        raise RuntimeError(f"登录页未找到 csrf token（状态 {r.status_code}），响应前200字: {r.text[:200]}")
    csrf = m.group(1)
    print("[1] 登录页状态:", r.status_code, "csrf:", csrf[:16] + "...")

    # 2. RSA 加密密码 (PKCS1v15, 与 JSEncrypt 默认一致)
    pub = load_pem_public_key(PUBKEY_PEM.encode())
    enc = pub.encrypt(PASSWORD.encode("utf-8"), padding.PKCS1v15())
    en_pwd = base64.b64encode(enc).decode()
    vc = str(int(time.time() * 1000))
    print("[2] 密码已 RSA 加密, vc(时间戳):", vc)

    # 3. 提交登录
    data = {
        "csrfmiddlewaretoken": csrf,
        "username": USERNAME,
        "pw": en_pwd,
        "vc": vc,
    }
    r = s.post(f"{BASE}/user_login_check/?next=/", data=data,
               headers={"Referer": f"{BASE}/login/?next=/"}, timeout=25)
    print("[3] 登录接口状态:", r.status_code, "Content-Type:", r.headers.get("Content-Type"))
    print("    原始响应(前500字):", r.text[:500])
    print("    cookies:", dict(s.cookies))

    # 4. 解析 JSON 响应
    try:
        j = r.json()
        print("[4] JSON:", j)
    except Exception as e:
        print("[4] 非 JSON 响应:", e)
        sys.exit(0)

    if str(j.get("state")) == "200":
        next_url = j.get("next_url", "/")
        print("[5] 登录成功! next_url =", next_url)
        # 跟随到 MCP 管理页
        r = s.get(f"{BASE}/mcp/admin/", timeout=25, allow_redirects=True)
        print("[6] /mcp/admin/ 状态:", r.status_code, "最终URL:", r.url, "长度:", len(r.text))
        with open("mcp_admin.html", "w", encoding="utf-8") as f:
            f.write(r.text)
        print("    已保存到 mcp_admin.html")
    else:
        print("[5] 登录失败:", j.get("message"))


if __name__ == "__main__":
    main()

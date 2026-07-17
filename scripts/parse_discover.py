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
KEY = require("IDSTE_API_KEY")

def main():
    s = requests.Session()
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

    r = s.get(f"{BASE}/mcp/admin/api/discover", headers={"X-MCP-API-Key": KEY}, timeout=25)
    data = r.json()["data"]
    with open("discover.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2))

    st = data["server"]["stats"]
    print(f"服务器: {data['server']['name']} | 工具总数: {st['total_tools']} (只读 {st['read_tools']} / 写 {st['write_tools']})")
    print(f"分类数: {len(data['categories'])}\n")

    lines = []
    for cat in data["categories"]:
        lines.append(f"## {cat['label']} ({cat['id']}) - {len(cat.get('tool_details',[]))} 个工具")
        for t in cat.get("tool_details", []):
            name = t.get("display_name") or t.get("name")
            desc = t.get("description","").replace("\n"," ").strip()
            rw = "写" if t.get("is_write") or t.get("write") else "读"
            lines.append(f"  [{rw}] {t['name']} - {name}")
            if desc:
                lines.append(f"      {desc[:160]}")
        lines.append("")

    txt = "\n".join(lines)
    with open("tools_summary.txt", "w", encoding="utf-8") as f:
        f.write(txt)
    print(txt)


if __name__ == "__main__":
    main()

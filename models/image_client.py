# -*- coding: utf-8 -*-
"""Qwen-Image-2512 图片生成客户端。

POST {QWEN_IMAGE_URL}/v1/images/generations
Headers: XSRF-TOKEN, Content-Type
Body: {"model": "Qwen-Image-2512", "prompt": ..., "n": 1, "size": ...}
Response: {"data": [{"url": "..."}]}
→ 客户端下载 url 的 PNG bytes 返回
"""
import os
import time
import logging
import requests
from core.envutil import env

log = logging.getLogger(__name__)


class QwenImageError(Exception):
    pass


class QwenImageClient:
    def __init__(self, base_url: str = None, model: str = None,
                 token: str = None, timeout: int = 60, size: str = "1024x1024"):
        base = base_url or env("QWEN_IMAGE_URL")
        if not base:
            raise QwenImageError("QWEN_IMAGE_URL 未配置（请在 .env 设置 Qwen-Image 服务地址）")
        self.base_url = base.rstrip("/")
        model = model or env("QWEN_IMAGE_MODEL")
        if not model:
            raise QwenImageError("QWEN_IMAGE_MODEL 未配置")
        self.model = model
        token = token or env("QWEN_IMAGE_TOKEN")
        if not token:
            raise QwenImageError("QWEN_IMAGE_TOKEN 未配置（XSRF-TOKEN）")
        self.token = token
        self.timeout = timeout
        self.size = size

    def _headers(self):
        return {
            "XSRF-TOKEN": self.token,
            "Content-Type": "application/json",
        }

    def generate(self, prompt: str, style: str = "minimal", size: str = None) -> bytes:
        """调 Qwen-Image API，返回 PNG bytes。失败 raise QwenImageError。"""
        size = size or self.size
        url = f"{self.base_url}/v1/images/generations"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "n": 1,
            "size": size,
        }
        # style 仅作为 prompt 后缀附加，不发到 API（API 字段未确认）
        full_prompt = f"{prompt}, style: {style}" if style else prompt
        payload["prompt"] = full_prompt

        log.info(f"[qwen-image] POST {url} prompt={full_prompt[:60]}...")
        t0 = time.time()
        try:
            r = requests.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
        except requests.Timeout as e:
            raise QwenImageError(f"timeout after {self.timeout}s") from e
        except requests.ConnectionError as e:
            raise QwenImageError(f"connection error: {e}") from e

        latency = time.time() - t0

        if r.status_code >= 500:
            raise QwenImageError(f"server error {r.status_code}: {r.text[:200]}")
        if r.status_code >= 400:
            raise QwenImageError(f"client error {r.status_code}: {r.text[:200]}")

        try:
            data = r.json()
        except Exception as e:
            raise QwenImageError(f"invalid json: {e}; body: {r.text[:200]}") from e

        items = data.get("data", [])
        if not items:
            raise QwenImageError(f"no data in response: {data}")
        item = items[0]

        # Qwen-Image 返回 b64_json（base64 编码图片）或 url（需下载）；优先 b64_json
        if item.get("b64_json"):
            import base64
            try:
                png_bytes = base64.b64decode(item["b64_json"])
            except Exception as e:
                raise QwenImageError(f"b64_json decode failed: {e}") from e
            if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
                raise QwenImageError(
                    f"b64_json 解码后非 PNG（前8字节: {png_bytes[:8]!r}），可能返回了错误内容"
                )
            log.info(f"[qwen-image] got b64_json in {latency:.1f}s, {len(png_bytes)} bytes")
            return png_bytes

        img_url = item.get("url")
        if not img_url:
            raise QwenImageError(f"no url/b64_json in response: {data}")
        log.info(f"[qwen-image] got url in {latency:.1f}s, downloading...")
        try:
            img_r = requests.get(
                img_url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=self.timeout,
            )
            img_r.raise_for_status()
            return img_r.content
        except Exception as e:
            raise QwenImageError(f"download failed: {e}") from e

    def save(self, png_bytes: bytes, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(png_bytes)


if __name__ == "__main__":
    import sys
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "minimalist blue gradient, navy and ice blue, professional"
    try:
        client = QwenImageClient()
        png = client.generate(prompt, style="minimal")
        out_path = "output/test_qwen_image.png"
        client.save(png, out_path)
        print(f"OK: {len(png)} bytes saved to {out_path}")
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        sys.exit(1)

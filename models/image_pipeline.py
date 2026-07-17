# -*- coding: utf-8 -*-
"""图片生成 pipeline：把 slide_spec 里需要图的 slide 调 Qwen-Image，
按 cache 命中 / 强制 vs 可选 / 重试 决策，写入本地 cache 并补 local_path。
"""
import os
import time
import json
import hashlib
import logging
from typing import Optional
from core.envutil import env

log = logging.getLogger(__name__)


# 必须有图的关键 layout
KEY_LAYOUTS = {"title", "section", "conclusion"}


def _cache_key(prompt: str, style: str, size: str) -> str:
    raw = f"{prompt}|{style}|{size}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _default_image_for(slide: dict, palette: str = "Midnight Executive") -> dict:
    """为缺失 image 字段的 key layout 生成兜底 image 配置。"""
    title = slide.get("title", "section")
    return {
        "prompt": (
            f"professional minimal illustration for a presentation section "
            f'titled "{title}", {palette} palette, no text, abstract'
        ),
        "zone": 5,
        "aspect": "16:9",
        "style": "minimal",
        "required": True,
    }


def _normalize(slide_spec: dict) -> None:
    """in-place：title/section/conclusion 缺 image 自动注入；required 强制 True。"""
    for slide in slide_spec.get("slides", []):
        layout = slide.get("layout", "")
        if layout in KEY_LAYOUTS and not slide.get("image"):
            slide["image"] = _default_image_for(slide)
        if layout in KEY_LAYOUTS and slide.get("image") is not None:
            slide["image"].setdefault("required", True)


def augment_slide_spec(
    slide_spec: dict,
    client,                       # QwenImageClient 实例
    cache_dir: Optional[str] = None,
    on_progress=None,             # callable(slide_idx, success, cached, latency_ms) -> None
    verbose: bool = True,
) -> dict:
    """遍历 slides，缺图调 Qwen-Image。in-place 修改 slide_spec，返回它。"""
    cache_dir = cache_dir or env("IMAGE_CACHE_DIR", "cache/images")
    os.makedirs(cache_dir, exist_ok=True)
    size = client.size

    _normalize(slide_spec)

    for idx, slide in enumerate(slide_spec.get("slides", [])):
        img = slide.get("image")
        if not img:
            continue
        prompt = img.get("prompt", "")
        style = img.get("style", "minimal")
        required = img.get("required", True)

        key = _cache_key(prompt, style, size)
        png_path = os.path.join(cache_dir, f"{key}.png")
        meta_path = os.path.join(cache_dir, f"{key}.json")

        # 命中 cache（校验 PNG 魔数，防止半截/损坏文件中毒后续渲染）
        if os.path.exists(png_path) and os.path.getsize(png_path) > 8:
            try:
                with open(png_path, "rb") as _f:
                    if _f.read(8) != b"\x89PNG\r\n\x1a\n":
                        if verbose:
                            log.warning(f"[image] slide {idx} cache 损坏（非 PNG），重生成: {key}")
                    else:
                        if verbose:
                            log.info(f"[image] slide {idx} cache hit: {key}")
                        slide["image"]["local_path"] = png_path
                        if on_progress:
                            on_progress(idx, True, True, 0)
                        continue
            except OSError as _e:
                if verbose:
                    log.warning(f"[image] slide {idx} cache 读失败，重生成: {_e}")

        # 调 Qwen-Image（重试 2 次共 3 次）
        png_bytes = None
        last_err = None
        for attempt in (1, 2, 3):
            try:
                t0 = time.time()
                png_bytes = client.generate(prompt, style=style, size=size)
                latency_ms = int((time.time() - t0) * 1000)
                last_err = None
                break
            except Exception as e:
                last_err = e
                if verbose:
                    log.warning(f"[image] slide {idx} attempt {attempt} failed: {e}")
                if attempt < 3:
                    time.sleep(2 ** attempt)

        if png_bytes is None:
            if required:
                raise RuntimeError(
                    f"slide {idx} ({slide.get('title', '')}): required image failed after 3 attempts: {last_err}"
                ) from last_err
            if verbose:
                log.warning(f"[image] slide {idx} optional image skipped: {last_err}")
            del slide["image"]  # 丢掉，避免 render 报空
            if on_progress:
                on_progress(idx, False, False, 0)
            continue

        # 写 cache（tmp + os.replace 原子替换，避免并发/中断产生半截文件）
        tmp_png = png_path + ".tmp"
        tmp_meta = meta_path + ".tmp"
        try:
            with open(tmp_png, "wb") as f:
                f.write(png_bytes)
            with open(tmp_meta, "w", encoding="utf-8") as f:
                json.dump({
                    "prompt": prompt, "style": style, "size": size,
                    "created_at": time.time(), "latency_ms": latency_ms,
                }, f, ensure_ascii=False, indent=2)
            os.replace(tmp_png, png_path)
            os.replace(tmp_meta, meta_path)
        except Exception as e:
            if verbose:
                log.warning(f"[image] cache write failed (continuing): {e}")
            for _p in (tmp_png, tmp_meta):
                try:
                    os.remove(_p)
                except OSError:
                    pass

        slide["image"]["local_path"] = png_path
        if on_progress:
            on_progress(idx, True, False, latency_ms)

    return slide_spec


if __name__ == "__main__":
    from image_client import QwenImageClient
    fake = {
        "slides": [
            {"layout": "title", "title": "Test Cover"},
            {"layout": "bullets", "title": "P1"},
            {"layout": "section", "title": "Test Section"},
            {"layout": "bullets", "title": "P2"},
            {"layout": "conclusion", "title": "End"},
        ]
    }
    print("Before:", json.dumps(fake, ensure_ascii=False, indent=2))
    try:
        client = QwenImageClient()
        result = augment_slide_spec(fake, client, verbose=True)
        print("After:", json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")

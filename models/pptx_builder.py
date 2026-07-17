# -*- coding: utf-8 -*-
"""Python -> Node 桥接：把 slide-spec JSON 转成 .pptx。

用法:
    from pptx_builder import build_pptx
    path = build_pptx(slide_spec_dict, output_dir="output")
    # 或直接传 .json 文件路径
    path = build_pptx("output/20260713_152256_slides.json")
"""
import os
import json
import subprocess
import tempfile
from datetime import datetime

from core.paths import resource

NODE_BIN = os.environ.get("NODE_BIN", "node")
RENDER_JS = resource("render.js")


def build_pptx(slide_spec, output_dir="output", prefix="", verbose=False):
    """slide_spec: dict 或 .json 路径；返回 .pptx 路径。

    Args:
        slide_spec: dict 或 .json 路径。
        output_dir: 输出目录。
        prefix: 文件名前缀（用于区分请求/用户）。
        verbose: 打印过程。
    """
    os.makedirs(output_dir, exist_ok=True)

    if isinstance(slide_spec, str):
        spec = json.load(open(slide_spec, encoding="utf-8"))
    elif isinstance(slide_spec, dict):
        spec = slide_spec
    else:
        raise TypeError(f"slide_spec 必须是 dict 或 str 路径，收到 {type(slide_spec)}")

    if not spec.get("slides"):
        raise ValueError("slide_spec.slides 为空，没法生成 PPT")

    # 临时 JSON
    fd, tmp_json = tempfile.mkstemp(suffix=".json", prefix="slidespec_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{prefix}" if prefix else ""
    out_pptx = os.path.join(output_dir, f"{ts}{suffix}_slides.pptx")

    try:
        if not os.path.exists(RENDER_JS):
            raise FileNotFoundError(
                f"render.js 不存在: {RENDER_JS}\n请确认 D:\\memory 目录完整"
            )
        if verbose:
            print(f"[pptx] spawn: {NODE_BIN} {RENDER_JS} {tmp_json} {out_pptx}")
        r = subprocess.run(
            [NODE_BIN, RENDER_JS, tmp_json, out_pptx],
            capture_output=True, text=True, timeout=180,
        )
        if verbose:
            if r.stdout.strip():
                print("[stdout]", r.stdout.strip())
            if r.stderr.strip():
                print("[stderr]", r.stderr.strip())
        if r.returncode != 0:
            raise RuntimeError(
                f"render.js 失败 (code={r.returncode}): {(r.stderr or r.stdout)[:500]}"
            )
        if not os.path.exists(out_pptx):
            raise RuntimeError(f"render.js 退出 0 但未生成文件: {out_pptx}")
        if verbose:
            sz = os.path.getsize(out_pptx)
            print(f"[pptx] OK {out_pptx}  ({sz / 1024:.1f} KB, {len(spec['slides'])} slides)")
        return out_pptx
    finally:
        try:
            os.unlink(tmp_json)
        except OSError:
            pass


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python pptx_builder.py <slide-spec.json> [output_dir]")
        sys.exit(1)
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    p = build_pptx(sys.argv[1], output_dir=out_dir, verbose=True)
    print(f"PPT 生成完毕: {p}")

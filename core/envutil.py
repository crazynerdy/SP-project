# -*- coding: utf-8 -*-
"""统一的 .env 加载与取值工具。

优先使用 python-dotenv（若已安装），否则用内置的简易解析器，
保证脚本在没有第三方依赖时也能直接运行。
.env 始终从项目根目录读取（经 core.paths.PROJECT_ROOT 定位），与运行时的工作目录无关。
"""
import os

from core.paths import resource

_ENV_PATH = resource(".env")


def _load_dotenv_minimal(path=_ENV_PATH):
    """简易 .env 解析器，无需第三方依赖。"""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            if k.startswith("export "):  # 兼容 shell 风格 export FOO=bar
                k = k[len("export "):].strip()
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)


try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(_ENV_PATH)
except ImportError:
    _load_dotenv_minimal()


def env(key, default=None):
    """读取环境变量。"""
    return os.environ.get(key, default)


def require(key):
    """读取必填环境变量，缺失则抛 RuntimeError（可被上层捕获并给出 traceback）。"""
    v = os.environ.get(key)
    if not v:
        raise RuntimeError(
            f"[env] 缺少必填环境变量: {key}（请在 .env 中配置，参考 .env.example）"
        )
    return v


import concurrent.futures


def run_with_timeout(fn, timeout_sec=120, label="任务"):
    """在子线程中执行 fn，超时则抛 TimeoutError。"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn)
        try:
            return future.result(timeout=timeout_sec)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"{label} 超时（超过 {timeout_sec} 秒）")

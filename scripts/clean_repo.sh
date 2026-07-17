#!/usr/bin/env bash
# clean_repo.sh — 清理仓库里的临时/缓存/调试产物
# 用于 Codex 2026-07 PR1 仓库清理 (see docs/REFACTOR_COEX_2026.md)
set -euo pipefail

echo "==> 清理 __pycache__ 和 .pyc 文件..."
find . -type d -name "__pycache__" -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -not -path "./.git/*" -delete 2>/dev/null || true

echo "==> 清理 output/ 调试产物..."
rm -f output/debug_*.txt output/test_fill_*.xlsx output/regression_test.xlsx 2>/dev/null || true

echo "==> 清理日志文件..."
rm -f agent_run.log ppt_run.log streamlit_stdout.txt streamlit_stderr.txt 2>/dev/null || true

echo "==> 清理 Node 缓存..."
rm -rf node_modules/.cache 2>/dev/null || true

echo "==> 清理 MCP 抓取产物..."
rm -f mcp_admin mcp_admin_text.txt 2>/dev/null || true

echo "==> 清理 IDE 缓存..."
rm -rf .idea/ .vscode/ 2>/dev/null || true

echo "==> 完成"
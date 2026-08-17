"""验证嵌入函数 key 为空时不发送 Authorization 头。

Bug: 上游 generate_*_embeddings / agenerate_*_embeddings 无条件发送
`Authorization: Bearer {key}`，key 为空时仍发 `Bearer `，导致：
1) URL 内嵌 Basic 凭据 (https://user:pass@host) 时 aiohttp/requests
   抛 "Cannot combine AUTHORIZATION header with credentials encoded in URL"
2) 仅 Basic Auth 的端点返回 401 (text/html)，r.json() 抛 ContentTypeError。

修复: 仅当 key 非空才设置 Authorization 头。

实现说明: 直接从源码文件解析目标函数的 AST，避免 import open_webui
(依赖 DB/DB 初始化)。零依赖、任何环境可跑。
"""
import ast
import inspect
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
UTILS_PATH = BACKEND_DIR / 'open_webui' / 'retrieval' / 'utils.py'

TARGET_FUNCS = [
    'generate_openai_batch_embeddings',
    'agenerate_openai_batch_embeddings',
    'generate_ollama_batch_embeddings',
    'agenerate_ollama_batch_embeddings',
]


def _func_source(name):
    """从 utils.py 提取指定函数的源码文本。"""
    tree = ast.parse(UTILS_PATH.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(UTILS_PATH.read_text(encoding='utf-8'), node)
    raise AssertionError(f'函数 {name} 未找到')


def test_no_unconditional_authorization():
    """4 个嵌入函数均不得有无条件 Bearer。"""
    for name in TARGET_FUNCS:
        src = _func_source(name)
        assert "'Authorization': f'Bearer {key}'" not in src, (
            f'{name}: 仍存在无条件 Bearer 头'
        )


def test_conditional_on_key():
    """headers 构造必须含 if key: 条件。"""
    for name in TARGET_FUNCS:
        src = _func_source(name)
        assert 'if key:' in src, f'{name}: 缺少 if key: 条件'
        assert "headers['Authorization'] = f'Bearer {key}'" in src, (
            f'{name}: 缺少条件 Authorization 赋值'
        )


def test_headers_init_content_type():
    """headers 初始化为仅 Content-Type。"""
    for name in TARGET_FUNCS:
        src = _func_source(name)
        # headers 初始化为 dict，仅 Content-Type，不含 Authorization
        assert "headers = {'Content-Type': 'application/json'}" in src, (
            f'{name}: headers 未初始化为仅 Content-Type'
        )

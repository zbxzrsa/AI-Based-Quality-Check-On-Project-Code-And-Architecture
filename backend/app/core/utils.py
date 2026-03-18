"""
通用工具函数
从重复代码中提取的公共函数
"""

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def safe_get_nested_value(data: dict, keys: list[str], default: Any = None) -> Any:
    """安全获取嵌套字典值"""
    try:
        result = data
        for key in keys:
            result = result[key]
        return result
    except (KeyError, TypeError):
        return default


def normalize_string(text: str) -> str:
    """标准化字符串"""
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text.strip())
    text = text.lower()
    return text


def format_error_message(error: Exception, context: str = "") -> str:
    """格式化错误消息"""
    error_type = type(error).__name__
    error_msg = str(error)

    if context:
        return f"[{context}] {error_type}: {error_msg}"
    return f"{error_type}: {error_msg}"


def validate_file_path(file_path: str) -> bool:
    """验证文件路径"""
    try:
        path = Path(file_path)
        return path.exists() and path.is_file()
    except Exception:
        return False


def chunk_list(lst: list, chunk_size: int) -> list[list]:
    """将列表分块"""
    return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]


def merge_dicts(*dicts: dict) -> dict:
    """合并多个字典"""
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result

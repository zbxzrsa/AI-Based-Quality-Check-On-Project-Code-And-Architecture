"""
通用工具函数
从重复代码中提取的公共函数
"""

import re
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

def safe_get_nested_value(data: Dict, keys: List[str], default: Any = None) -> Any:
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
    
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text.strip())
    # 转换为小写
    text = text.lower()
    return text

def validate_file_path(file_path: str) -> bool:
    """验证文件路径"""
    try:
        path = Path(file_path)
        return path.exists() and path.is_file()
    except Exception:
        return False

def format_error_message(error: Exception, context: str = "") -> str:
    """格式化错误消息"""
    error_type = type(error).__name__
    error_msg = str(error)
    
    if context:
        return f"[{context}] {error_type}: {error_msg}"
    else:
        return f"{error_type}: {error_msg}"

def retry_operation(func, max_retries: int = 3, delay: float = 1.0):
    """重试操作装饰器"""
    import time
    
    def wrapper(*args, **kwargs):
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(f"操作失败，{delay}秒后重试 (尝试 {attempt + 1}/{max_retries}): {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"操作最终失败: {e}")
        
        raise last_exception
    
    return wrapper

def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """将列表分块"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def merge_dicts(*dicts: Dict) -> Dict:
    """合并多个字典"""
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result

class ConfigValidator:
    """配置验证器"""
    
    @staticmethod
    def validate_required_fields(config: Dict, required_fields: List[str]) -> List[str]:
        """验证必需字段"""
        missing_fields = []
        for field in required_fields:
            if field not in config or config[field] is None:
                missing_fields.append(field)
        return missing_fields
    
    @staticmethod
    def validate_field_types(config: Dict, field_types: Dict[str, type]) -> List[str]:
        """验证字段类型"""
        type_errors = []
        for field, expected_type in field_types.items():
            if field in config and not isinstance(config[field], expected_type):
                type_errors.append(f"{field} should be {expected_type.__name__}, got {type(config[field]).__name__}")
        return type_errors

"""
Data Masking Module

Provides functionality to mask sensitive data in logs and error messages.
"""

import re
from typing import List, Pattern
from dataclasses import dataclass
from enum import Enum


class SensitiveDataType(Enum):
    """Types of sensitive data that need masking in logs"""
    PASSWORD = "password"
    API_KEY = "api_key"
    TOKEN = "token"
    CONNECTION_STRING = "connection_string"
    JWT_SECRET = "jwt_secret"
    DATABASE_URL = "database_url"
    WEBHOOK_SECRET = "webhook_secret"


@dataclass
class MaskingRule:
    """Rule for masking sensitive data in logs and error messages"""
    pattern: Pattern
    replacement: str
    data_type: SensitiveDataType


# Pre-defined masking rules for common sensitive data patterns
MASKING_RULES: List[MaskingRule] = [
    # Password patterns: password=value, password: value
    MaskingRule(
        pattern=re.compile(r'(?i)(password\s*[=:]\s*)([^\s,;"\']*)(?=[,;\s"\']|$)'),
        replacement=r'\1***',
        data_type=SensitiveDataType.PASSWORD,
    ),
    # API Keys: api_key=value, sk-xxx, pk-xxx
    MaskingRule(
        pattern=re.compile(r'(?i)(sk-|pk-|api[_-]?key\s*[=:]\s*)([a-zA-Z0-9_-]+)'),
        replacement=r'***',
        data_type=SensitiveDataType.API_KEY,
    ),
    # Tokens: token=value, bearer tokens
    MaskingRule(
        pattern=re.compile(r'(?i)(token\s*[=:]\s*|bearer\s+)([^\s,;"\']*)(?=[,;\s"\']|$)'),
        replacement=r'\1***',
        data_type=SensitiveDataType.TOKEN,
    ),
    # JWT Secrets: jwt_secret=value
    MaskingRule(
        pattern=re.compile(r'(?i)(jwt[_-]?secret\s*[=:]\s*)([^\s,;"\']*)(?=[,;\s"\']|$)'),
        replacement=r'\1***',
        data_type=SensitiveDataType.JWT_SECRET,
    ),
    # Connection strings with embedded credentials
    MaskingRule(
        pattern=re.compile(r'(?i)(connection[_-]?string\s*[=:]\s*["\']?)([^"\']*password[^"\']*["\']?)'),
        replacement=r'\1***',
        data_type=SensitiveDataType.CONNECTION_STRING,
    ),
    # Database URLs with credentials
    MaskingRule(
        pattern=re.compile(r'(?i)(postgresql|mysql|mongodb|redis)://([^:]+):([^@]+)@'),
        replacement=r'\1://\2:***@',
        data_type=SensitiveDataType.DATABASE_URL,
    ),
    # Webhook secrets
    MaskingRule(
        pattern=re.compile(r'(?i)(webhook[_-]?secret\s*[=:]\s*)([^\s,;"\']*)(?=[,;\s"\']|$)'),
        replacement=r'\1***',
        data_type=SensitiveDataType.WEBHOOK_SECRET,
    ),
]


def mask_sensitive_data(data: str, rules: List[MaskingRule] = None) -> str:
    """
    Mask sensitive data in a string using provided rules.
    
    Args:
        data: String that may contain sensitive data
        rules: Optional list of masking rules (defaults to MASKING_RULES)
        
    Returns:
        String with sensitive data masked
    """
    if rules is None:
        rules = MASKING_RULES
    
    masked_data = data
    for rule in rules:
        try:
            masked_data = rule.pattern.sub(rule.replacement, masked_data)
        except Exception:
            pass  # Skip failed masking attempts
    
    return masked_data


def add_custom_masking_rule(pattern: str, replacement: str, data_type: SensitiveDataType) -> MaskingRule:
    """
    Create a custom masking rule.
    
    Args:
        pattern: Regex pattern to match
        replacement: Replacement string
        data_type: Type of sensitive data
        
    Returns:
        New MaskingRule instance
    """
    return MaskingRule(
        pattern=re.compile(pattern),
        replacement=replacement,
        data_type=data_type,
    )

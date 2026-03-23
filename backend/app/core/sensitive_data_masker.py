"""
敏感数据掩码器
处理错误消息中的敏感信息掩码
"""

import re
from typing import List, Dict, Any
from .error_types import SensitiveDataType, MaskingRule


class SensitiveDataMasker:
    """敏感数据掩码器"""
    
    def __init__(self):
        self.masking_rules = self._initialize_masking_rules()
    
    def _initialize_masking_rules(self) -> List[MaskingRule]:
        """初始化掩码规则"""
        return [
            # 密码掩码
            MaskingRule(
                pattern=r'password["\s]*[:=]["\s]*([^"\s,}]+)',
                replacement=r'password": "***MASKED***"',
                data_type=SensitiveDataType.PASSWORD,
                description="Password in JSON/config format"
            ),
            MaskingRule(
                pattern=r'pwd["\s]*[:=]["\s]*([^"\s,}]+)',
                replacement=r'pwd": "***MASKED***"',
                data_type=SensitiveDataType.PASSWORD,
                description="Password (pwd) in JSON/config format"
            ),
            
            # API密钥掩码
            MaskingRule(
                pattern=r'api[_-]?key["\s]*[:=]["\s]*([^"\s,}]+)',
                replacement=r'api_key": "***MASKED***"',
                data_type=SensitiveDataType.API_KEY,
                description="API key in various formats"
            ),
            MaskingRule(
                pattern=r'(sk-[a-zA-Z0-9]{20,})',
                replacement=r'sk-***MASKED***',
                data_type=SensitiveDataType.API_KEY,
                description="OpenAI-style API key"
            ),
            
            # JWT密钥掩码
            MaskingRule(
                pattern=r'jwt[_-]?secret["\s]*[:=]["\s]*([^"\s,}]+)',
                replacement=r'jwt_secret": "***MASKED***"',
                data_type=SensitiveDataType.JWT_SECRET,
                description="JWT secret key"
            ),
            
            # 令牌掩码
            MaskingRule(
                pattern=r'token["\s]*[:=]["\s]*([^"\s,}]+)',
                replacement=r'token": "***MASKED***"',
                data_type=SensitiveDataType.TOKEN,
                description="Generic token"
            ),
            MaskingRule(
                pattern=r'bearer\s+([a-zA-Z0-9._-]+)',
                replacement=r'bearer ***MASKED***',
                data_type=SensitiveDataType.TOKEN,
                description="Bearer token"
            ),
            
            # 数据库连接字符串掩码
            MaskingRule(
                pattern=r'postgresql://([^:]+):([^@]+)@([^/]+)/(.+)',
                replacement=r'postgresql://***USER***:***MASKED***@\3/\4',
                data_type=SensitiveDataType.DATABASE_URL,
                description="PostgreSQL connection string"
            ),
            MaskingRule(
                pattern=r'mysql://([^:]+):([^@]+)@([^/]+)/(.+)',
                replacement=r'mysql://***USER***:***MASKED***@\3/\4',
                data_type=SensitiveDataType.DATABASE_URL,
                description="MySQL connection string"
            ),
            MaskingRule(
                pattern=r'redis://([^:]*):([^@]+)@([^/]+)',
                replacement=r'redis://***USER***:***MASKED***@\3',
                data_type=SensitiveDataType.DATABASE_URL,
                description="Redis connection string"
            ),
            
            # Webhook密钥掩码
            MaskingRule(
                pattern=r'webhook[_-]?secret["\s]*[:=]["\s]*([^"\s,}]+)',
                replacement=r'webhook_secret": "***MASKED***"',
                data_type=SensitiveDataType.WEBHOOK_SECRET,
                description="Webhook secret"
            ),
            
            # 通用密钥模式
            MaskingRule(
                pattern=r'secret["\s]*[:=]["\s]*([^"\s,}]+)',
                replacement=r'secret": "***MASKED***"',
                data_type=SensitiveDataType.TOKEN,
                description="Generic secret"
            ),
            MaskingRule(
                pattern=r'key["\s]*[:=]["\s]*([a-zA-Z0-9+/=]{20,})',
                replacement=r'key": "***MASKED***"',
                data_type=SensitiveDataType.API_KEY,
                description="Generic key (base64-like)"
            ),
        ]
    
    def mask_sensitive_data(self, text: str) -> str:
        """
        掩码文本中的敏感数据
        
        Args:
            text: 需要掩码的文本
            
        Returns:
            掩码后的文本
        """
        if not text:
            return text
        
        masked_text = text
        
        for rule in self.masking_rules:
            try:
                masked_text = re.sub(
                    rule.pattern, 
                    rule.replacement, 
                    masked_text, 
                    flags=re.IGNORECASE
                )
            except re.error:
                # 如果正则表达式有问题，跳过这个规则
                continue
        
        return masked_text
    
    def mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        掩码字典中的敏感数据
        
        Args:
            data: 需要掩码的字典
            
        Returns:
            掩码后的字典
        """
        if not isinstance(data, dict):
            return data
        
        masked_data = {}
        sensitive_keys = {
            'password', 'pwd', 'pass', 'secret', 'token', 'key', 'api_key',
            'jwt_secret', 'webhook_secret', 'database_url', 'connection_string'
        }
        
        for key, value in data.items():
            key_lower = key.lower()
            
            if any(sensitive_key in key_lower for sensitive_key in sensitive_keys):
                masked_data[key] = "***MASKED***"
            elif isinstance(value, dict):
                masked_data[key] = self.mask_dict(value)
            elif isinstance(value, str):
                masked_data[key] = self.mask_sensitive_data(value)
            else:
                masked_data[key] = value
        
        return masked_data
    
    def add_custom_rule(self, rule: MaskingRule):
        """添加自定义掩码规则"""
        self.masking_rules.append(rule)
    
    def get_masking_stats(self) -> Dict[str, int]:
        """获取掩码规则统计"""
        stats = {}
        for rule in self.masking_rules:
            data_type = rule.data_type.value
            stats[data_type] = stats.get(data_type, 0) + 1
        return stats
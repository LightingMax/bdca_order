"""
配置管理服务
提供统一的配置访问接口，支持环境变量覆盖和配置验证
"""

import os
from typing import Dict, Any, Optional
from app.config import Config


class ConfigService:
    """配置管理服务类"""
    
    @staticmethod
    def get_print_api_config() -> Dict[str, Any]:
        """获取打印API配置"""
        return {
            'base_url': Config.PRINT_API_BASE_URL,
            'token': Config.PRINT_API_TOKEN,
            'timeout': Config.PRINT_API_TIMEOUT,
            'endpoints': Config.PRINT_API_ENDPOINTS,
            'default_printer': Config.DEFAULT_PRINTER_NAME
        }
    
    @staticmethod
    def get_print_api_url(endpoint: str) -> str:
        """获取打印API完整URL"""
        if endpoint not in Config.PRINT_API_ENDPOINTS:
            raise ValueError(f"未知的API端点: {endpoint}")
        
        return f"{Config.PRINT_API_BASE_URL}{Config.PRINT_API_ENDPOINTS[endpoint]}"
    
    @staticmethod
    def get_auth_headers() -> Dict[str, str]:
        """获取认证头"""
        return {"Authorization": f"Bearer {Config.PRINT_API_TOKEN}"}
    
    @staticmethod
    def validate_print_api_config() -> bool:
        """验证打印API配置"""
        try:
            # 检查必要的配置项
            required_configs = [
                Config.PRINT_API_BASE_URL,
                Config.PRINT_API_TOKEN,
                Config.DEFAULT_PRINTER_NAME
            ]
            
            for config in required_configs:
                if not config:
                    return False
            
            # 检查端点配置
            required_endpoints = ['printers', 'print', 'health']
            for endpoint in required_endpoints:
                if endpoint not in Config.PRINT_API_ENDPOINTS:
                    return False
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def get_environment_info() -> Dict[str, Any]:
        """获取环境信息"""
        return {
            'print_api_base_url': Config.PRINT_API_BASE_URL,
            'print_api_timeout': Config.PRINT_API_TIMEOUT,
            'default_printer': Config.DEFAULT_PRINTER_NAME,
            'available_endpoints': list(Config.PRINT_API_ENDPOINTS.keys())
        }

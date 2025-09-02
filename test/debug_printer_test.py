#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印机测试调试工具
用于诊断API响应问题
"""

import requests
import os
import tempfile
import json
from datetime import datetime

# 打印API服务配置
PRINT_API_BASE_URL = "http://localhost:12346"
API_KEY = "TOKEN_PRINT_API_KEY_9527"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


class PrinterDebugger:
    """打印机调试器"""
    
    def __init__(self, base_url=PRINT_API_BASE_URL):
        self.base_url = base_url
        self.headers = HEADERS
    
    def debug_response(self, response, endpoint_name):
        """调试API响应"""
        print(f"\n{'='*60}")
        print(f"调试 {endpoint_name} 响应")
        print(f"{'='*60}")
        print(f"URL: {response.url}")
        print(f"状态码: {response.status_code}")
        print(f"响应头:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        print(f"\n响应内容 (前500字符):")
        print(f"{'='*30}")
        content = response.text
        print(content[:500])
        if len(content) > 500:
            print(f"... (还有 {len(content) - 500} 个字符)")
        
        print(f"\n响应内容类型: {type(content)}")
        print(f"响应内容长度: {len(content)}")
        
        # 尝试解析JSON
        try:
            if content.strip():
                json_data = response.json()
                print(f"✅ JSON解析成功:")
                print(json.dumps(json_data, indent=2, ensure_ascii=False))
            else:
                print("❌ 响应内容为空")
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print(f"响应内容不是有效的JSON格式")
    
    def test_connection(self):
        """测试API连接"""
        print("测试API连接...")
        try:
            response = requests.get(f"{self.base_url}/printers", headers=self.headers, timeout=10)
            self.debug_response(response, "连接测试")
            
            if response.status_code == 200:
                print("✅ API连接成功")
                return True
            else:
                print(f"❌ API连接失败，状态码: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError as e:
            print(f"❌ 连接错误: {e}")
            print("可能的原因:")
            print("1. 打印API服务没有运行")
            print("2. 端口50003被占用")
            print("3. 防火墙阻止了连接")
            return False
        except requests.exceptions.Timeout as e:
            print(f"❌ 请求超时: {e}")
            return False
        except Exception as e:
            print(f"❌ 其他错误: {e}")
            return False
    
    def test_endpoints(self):
        """测试所有API端点"""
        endpoints = [
            ("/printers", "获取打印机列表"),
            ("/printers/detailed", "获取打印机详细信息"),
            ("/default-printer", "获取默认打印机"),
        ]
        
        for endpoint, description in endpoints:
            print(f"\n测试端点: {endpoint} - {description}")
            try:
                response = requests.get(f"{self.base_url}{endpoint}", headers=self.headers, timeout=10)
                self.debug_response(response, description)
            except Exception as e:
                print(f"❌ 请求失败: {e}")
    
    def check_service_status(self):
        """检查服务状态"""
        print("\n检查服务状态...")
        
        # 检查端口是否开放
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', 12346))
            sock.close()
            
            if result == 0:
                print("✅ 端口12346已开放")
            else:
                print("❌ 端口12346未开放")
                print("请确保打印API服务正在运行")
        except Exception as e:
            print(f"❌ 检查端口失败: {e}")
        
        # 检查进程
        try:
            import subprocess
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            if 'print_api_service' in result.stdout:
                print("✅ 找到打印API服务进程")
            else:
                print("❌ 未找到打印API服务进程")
        except Exception as e:
            print(f"❌ 检查进程失败: {e}")


def main():
    """主函数"""
    debugger = PrinterDebugger()
    
    print("=" * 60)
    print("打印机API调试工具")
    print("=" * 60)
    
    # 1. 检查服务状态
    debugger.check_service_status()
    
    # 2. 测试连接
    if debugger.test_connection():
        # 3. 测试所有端点
        debugger.test_endpoints()
    else:
        print("\n请先启动打印API服务:")
        print("python print_api_service_linux_enhanced.py")


if __name__ == "__main__":
    main()

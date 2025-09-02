#!/usr/bin/env python3
"""
配置测试工具
验证配置的正确性和打印API服务的连接性
"""

import sys
import os
import requests
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.config_service import ConfigService


def test_config_validation():
    """测试配置验证"""
    print("=" * 50)
    print("配置验证测试")
    print("=" * 50)
    
    # 验证配置
    is_valid = ConfigService.validate_print_api_config()
    print(f"配置验证结果: {'✅ 通过' if is_valid else '❌ 失败'}")
    
    if not is_valid:
        print("配置验证失败，请检查环境变量设置")
        return False
    
    # 显示环境信息
    env_info = ConfigService.get_environment_info()
    print("\n环境配置信息:")
    for key, value in env_info.items():
        print(f"  {key}: {value}")
    
    return True


def test_print_api_connection():
    """测试打印API连接"""
    print("\n" + "=" * 50)
    print("打印API连接测试")
    print("=" * 50)
    
    try:
        # 测试健康检查端点
        health_url = ConfigService.get_print_api_url('health')
        headers = ConfigService.get_auth_headers()
        
        print(f"测试健康检查端点: {health_url}")
        response = requests.get(health_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("✅ 健康检查通过")
            health_data = response.json()
            print(f"  服务状态: {health_data.get('status', 'unknown')}")
        else:
            print(f"❌ 健康检查失败，状态码: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到打印API服务")
        print("  请确保打印API服务正在运行")
        return False
    except Exception as e:
        print(f"❌ 连接测试出错: {str(e)}")
        return False
    
    return True


def test_printer_list():
    """测试获取打印机列表"""
    print("\n" + "=" * 50)
    print("打印机列表测试")
    print("=" * 50)
    
    try:
        printers_url = ConfigService.get_print_api_url('printers')
        headers = ConfigService.get_auth_headers()
        
        print(f"获取打印机列表: {printers_url}")
        response = requests.get(printers_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                printers = data.get('printers', [])
                print(f"✅ 成功获取 {len(printers)} 个打印机")
                
                for i, printer in enumerate(printers, 1):
                    print(f"  {i}. {printer}")
                    
                return True
            else:
                print(f"❌ API返回错误: {data.get('message', '未知错误')}")
                return False
        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 获取打印机列表出错: {str(e)}")
        return False


def main():
    """主测试函数"""
    print("配置和连接测试工具")
    print("=" * 50)
    
    # 测试配置验证
    if not test_config_validation():
        print("\n❌ 配置验证失败，请检查环境变量设置")
        return
    
    # 测试API连接
    if not test_print_api_connection():
        print("\n❌ API连接测试失败")
        return
    
    # 测试打印机列表
    if not test_printer_list():
        print("\n❌ 打印机列表测试失败")
        return
    
    print("\n" + "=" * 50)
    print("✅ 所有测试通过！配置正确，服务连接正常")
    print("=" * 50)


if __name__ == "__main__":
    main()

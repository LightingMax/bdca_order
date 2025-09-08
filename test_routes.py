#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试Flask应用路由是否正确注册
"""

import requests
import json

def test_routes():
    """测试主要路由是否可访问"""
    base_url = "http://192.168.20.95:12345"
    
    print("🧪 开始测试Flask应用路由...")
    print(f"📍 目标地址: {base_url}")
    print("-" * 50)
    
    # 测试主页
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ 主页 (/) - 状态码: {response.status_code}")
        if response.status_code == 200:
            print("   📄 页面内容长度:", len(response.text))
        else:
            print("   ❌ 页面访问失败")
    except Exception as e:
        print(f"❌ 主页 (/) - 错误: {str(e)}")
    
    # 测试原始打印上传API
    try:
        response = requests.post(f"{base_url}/api/upload-raw", timeout=5)
        print(f"✅ 原始打印上传API (/api/upload-raw) - 状态码: {response.status_code}")
        if response.status_code == 400:
            print("   📝 正常响应：缺少文件参数（这是预期的）")
        else:
            print("   📝 响应内容:", response.text[:100])
    except Exception as e:
        print(f"❌ 原始打印上传API (/api/upload-raw) - 错误: {str(e)}")
    
    # 测试获取原始文件API
    try:
        data = {"filename": "test.pdf"}
        response = requests.post(f"{base_url}/api/get-raw-file", 
                               json=data, timeout=5)
        print(f"✅ 获取原始文件API (/api/get-raw-file) - 状态码: {response.status_code}")
        if response.status_code == 404:
            print("   📝 正常响应：文件未找到（这是预期的）")
        else:
            print("   📝 响应内容:", response.text[:100])
    except Exception as e:
        print(f"❌ 获取原始文件API (/api/get-raw-file) - 错误: {str(e)}")
    
    # 测试打印原始文件API
    try:
        data = {"filename": "test.pdf", "action": "print"}
        response = requests.post(f"{base_url}/api/print-raw", 
                               json=data, timeout=5)
        print(f"✅ 打印原始文件API (/api/print-raw) - 状态码: {response.status_code}")
        if response.status_code == 200:
            print("   📝 响应内容:", response.text[:100])
        else:
            print("   📝 响应内容:", response.text[:100])
    except Exception as e:
        print(f"❌ 打印原始文件API (/api/print-raw) - 错误: {str(e)}")
    
    # 测试智能处理上传API
    try:
        response = requests.post(f"{base_url}/api/upload", timeout=5)
        print(f"✅ 智能处理上传API (/api/upload) - 状态码: {response.status_code}")
        if response.status_code == 400:
            print("   📝 正常响应：缺少文件参数（这是预期的）")
        else:
            print("   📝 响应内容:", response.text[:100])
    except Exception as e:
        print(f"❌ 智能处理上传API (/api/upload) - 错误: {str(e)}")
    
    print("-" * 50)
    print("🎯 路由测试完成！")
    print("\n📋 测试结果说明：")
    print("• 状态码 200: 路由正常，页面/API可访问")
    print("• 状态码 400: 路由正常，但缺少必要参数（这是预期的）")
    print("• 状态码 404: 路由不存在或未正确注册")
    print("• 连接错误: 应用可能未启动或地址错误")

if __name__ == "__main__":
    test_routes()

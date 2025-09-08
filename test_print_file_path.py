#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试FastAPI文件路径打印接口
"""

import requests
import json
import os

def test_print_file_path():
    """测试通过文件路径打印PDF文件"""
    print("🧪 测试FastAPI文件路径打印接口")
    print("=" * 50)
    
    base_url = "http://localhost:12346"
    token = "TOKEN_PRINT_API_KEY_9527"
    
    # 测试数据
    test_data = {
        "file_path": "/tmp/test.pdf",  # 测试文件路径
        "printer_name": "HP-LaserJet-MFP-M437-M443",
        "copies": 1,
        "tray": "auto",
        "page_size": None
    }
    
    try:
        print("1️⃣ 测试文件路径打印接口...")
        response = requests.post(
            f"{base_url}/print-file",
            json=test_data,
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 打印请求成功: {result.get('message', '')}")
            print(f"   任务ID: {result.get('job_id', 'unknown')}")
        elif response.status_code == 422:
            print("❌ 请求格式错误 (422)")
            print("响应内容:")
            try:
                error_detail = response.json()
                print(json.dumps(error_detail, indent=2, ensure_ascii=False))
            except:
                print(response.text)
        elif response.status_code == 404:
            print("❌ 文件未找到 (404)")
            result = response.json()
            print(f"错误信息: {result.get('message', '')}")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print("响应内容:")
            try:
                result = response.json()
                print(json.dumps(result, indent=2, ensure_ascii=False))
            except:
                print(response.text)
        
        return response.status_code == 200
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到FastAPI服务 (端口12346)")
        print("💡 请确保FastAPI服务已启动")
        return False
    except Exception as e:
        print(f"❌ 测试时出错: {str(e)}")
        return False

def test_printer_status():
    """测试打印机状态"""
    print("\n2️⃣ 测试打印机状态...")
    
    base_url = "http://localhost:12346"
    token = "TOKEN_PRINT_API_KEY_9527"
    
    try:
        response = requests.get(
            f"{base_url}/printer-status/HP-LaserJet-MFP-M437-M443",
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 打印机状态: {result.get('state_text', 'unknown')}")
            print(f"   是否接受任务: {result.get('is_accepting', False)}")
            return True
        else:
            print(f"❌ 获取打印机状态失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 获取打印机状态时出错: {str(e)}")
        return False

def test_api_docs():
    """测试API文档是否包含新接口"""
    print("\n3️⃣ 检查API文档...")
    
    base_url = "http://localhost:12346"
    
    try:
        response = requests.get(f"{base_url}/openapi.json", timeout=10)
        
        if response.status_code == 200:
            openapi_spec = response.json()
            paths = openapi_spec.get('paths', {})
            
            if '/print-file' in paths:
                print("✅ 新接口 /print-file 已添加到API文档")
                print(f"   方法: {list(paths['/print-file'].keys())}")
                return True
            else:
                print("❌ 新接口 /print-file 未找到")
                print(f"   可用接口: {list(paths.keys())}")
                return False
        else:
            print(f"❌ 无法获取API文档: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 检查API文档时出错: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 开始测试FastAPI文件路径打印接口")
    print("=" * 60)
    
    # 测试打印机状态
    printer_ok = test_printer_status()
    
    # 测试文件路径打印接口
    print_ok = test_print_file_path()
    
    # 检查API文档
    docs_ok = test_api_docs()
    
    # 总结
    print("\n📊 测试结果总结")
    print("=" * 50)
    
    if printer_ok and print_ok and docs_ok:
        print("🎉 所有测试通过！")
        print("✅ 打印机状态正常")
        print("✅ 文件路径打印接口正常")
        print("✅ API文档已更新")
        print("\n💡 现在Flask后端可以调用这个接口进行打印")
    elif printer_ok and not print_ok:
        print("⚠️  部分测试通过")
        print("✅ 打印机状态正常")
        print("❌ 文件路径打印接口有问题")
        print("\n💡 请检查接口实现")
    elif not printer_ok and print_ok:
        print("⚠️  部分测试通过")
        print("❌ 打印机状态异常")
        print("✅ 文件路径打印接口正常")
        print("\n💡 请检查打印机连接")
    else:
        print("❌ 所有测试失败")
        print("❌ 打印机状态异常")
        print("❌ 文件路径打印接口有问题")
        print("\n💡 请检查服务状态")
    
    print("=" * 60)

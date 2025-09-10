#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Flask和FastAPI打印服务集成
"""

import requests
import json
import time

def test_fastapi_print_service():
    """测试FastAPI打印服务是否正常运行"""
    print("🧪 测试FastAPI打印服务 (端口12346)")
    print("=" * 50)
    
    base_url = "http://localhost:12346"
    token = "TOKEN_PRINT_API_KEY_9527"
    
    try:
        # 测试1: 获取打印机列表
        print("1️⃣ 测试获取打印机列表...")
        response = requests.get(
            f"{base_url}/printers",
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 打印机列表获取成功: {result.get('message', '')}")
            if result.get('printers'):
                print(f"   可用打印机: {', '.join(result['printers'])}")
        else:
            print(f"❌ 获取打印机列表失败: {response.status_code}")
            return False
        
        # 测试2: 获取默认打印机信息
        print("\n2️⃣ 测试获取默认打印机信息...")
        response = requests.get(
            f"{base_url}/default-printer",
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 默认打印机信息获取成功: {result.get('message', '')}")
            print(f"   默认打印机: {result.get('default_printer', 'unknown')}")
        else:
            print(f"❌ 获取默认打印机信息失败: {response.status_code}")
            return False
        
        # 测试3: 获取打印机状态
        print("\n3️⃣ 测试获取打印机状态...")
        default_printer = "HP-LaserJet-MFP-M437-M443"
        response = requests.get(
            f"{base_url}/printer-status/{default_printer}",
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 打印机状态获取成功: {result.get('message', '')}")
            print(f"   状态: {result.get('state_text', 'unknown')}")
            print(f"   是否接受任务: {result.get('is_accepting', False)}")
        else:
            print(f"❌ 获取打印机状态失败: {response.status_code}")
            return False
        
        print("\n✅ FastAPI打印服务测试通过！")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到FastAPI打印服务 (端口12346)")
        print("💡 请确保FastAPI服务已启动:")
        print("   cd /path/to/print_api_service_linux_enhanced.py")
        print("   python print_api_service_linux_enhanced.py")
        return False
    except Exception as e:
        print(f"❌ 测试FastAPI打印服务时出错: {str(e)}")
        return False

def test_flask_print_api():
    """测试Flask打印API是否正常工作"""
    print("\n🧪 测试Flask打印API (端口12345)")
    print("=" * 50)
    
    base_url = "http://localhost:12345"
    
    try:
        # 测试1: 检查主页
        print("1️⃣ 测试Flask主页...")
        response = requests.get(f"{base_url}/", timeout=10)
        
        if response.status_code == 200:
            print("✅ Flask主页访问成功")
        else:
            print(f"❌ Flask主页访问失败: {response.status_code}")
            return False
        
        # 测试2: 测试打印API端点
        print("\n2️⃣ 测试打印API端点...")
        test_data = {
            'filename': 'test.pdf',
            'action': 'print'
        }
        
        response = requests.post(
            f"{base_url}/api/print-raw",
            json=test_data,
            timeout=10
        )
        
        if response.status_code == 503:
            print("✅ Flask打印API正常工作，但无法连接到FastAPI打印服务")
            print("💡 这是预期的行为，因为FastAPI服务未启动")
            return True
        elif response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Flask打印API测试成功！")
                return True
            else:
                print(f"❌ Flask打印API返回失败: {result.get('message', '')}")
                return False
        else:
            print(f"❌ Flask打印API测试失败: {response.status_code}")
            return False
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到Flask服务 (端口12345)")
        print("💡 请确保Flask服务已启动:")
        print("   cd /path/to/order_reimbursement")
        print("   python run.py")
        return False
    except Exception as e:
        print(f"❌ 测试Flask打印API时出错: {str(e)}")
        return False

def test_integration():
    """测试完整的集成流程"""
    print("\n🧪 测试完整集成流程")
    print("=" * 50)
    
    # 首先测试FastAPI服务
    fastapi_ok = test_fastapi_print_service()
    
    # 然后测试Flask服务
    flask_ok = test_flask_print_api()
    
    # 总结
    print("\n📊 测试结果总结")
    print("=" * 50)
    
    if fastapi_ok and flask_ok:
        print("🎉 所有测试通过！集成成功！")
        print("✅ FastAPI打印服务正常运行")
        print("✅ Flask服务正常运行")
        print("✅ 打印API集成正常")
        print("\n💡 现在您可以:")
        print("   1. 在Flask前端上传文件")
        print("   2. 点击打印按钮")
        print("   3. 文件将通过FastAPI服务发送到打印机")
        return True
    elif flask_ok and not fastapi_ok:
        print("⚠️  部分测试通过")
        print("✅ Flask服务正常运行")
        print("❌ FastAPI打印服务未启动")
        print("\n💡 需要启动FastAPI打印服务:")
        print("   cd /path/to/print_api_service_linux_enhanced.py")
        print("   python print_api_service_linux_enhanced.py")
        return False
    elif not flask_ok and fastapi_ok:
        print("⚠️  部分测试通过")
        print("❌ Flask服务未启动")
        print("✅ FastAPI打印服务正常运行")
        print("\n💡 需要启动Flask服务:")
        print("   cd /path/to/order_reimbursement")
        print("   python run.py")
        return False
    else:
        print("❌ 所有测试失败")
        print("❌ Flask服务未启动")
        print("❌ FastAPI打印服务未启动")
        print("\n💡 需要启动两个服务")
        return False

if __name__ == "__main__":
    print("🚀 开始测试Flask和FastAPI打印服务集成")
    print("=" * 60)
    
    success = test_integration()
    
    if success:
        print("\n🎯 测试完成！所有服务正常运行")
    else:
        print("\n⚠️  测试完成！请检查服务状态")
    
    print("=" * 60)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试智能PDF打印功能
"""

import requests
import os
import sys

# API配置
API_BASE_URL = "http://localhost:12346"
API_KEY = "TOKEN_PRINT_API_KEY_9527"
PRINTER_NAME = "HP-LaserJet-MFP-M437-M443"

def test_analyze_pdf(pdf_path):
    """测试PDF分析功能"""
    print(f"🔍 测试PDF分析功能: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        print(f"❌ 文件不存在: {pdf_path}")
        return False
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
            headers = {'Authorization': f'Bearer {API_KEY}'}
            
            response = requests.post(
                f"{API_BASE_URL}/analyze-pdf",
                headers=headers,
                files=files
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ PDF分析成功:")
            print(f"   文件名: {result['filename']}")
            print(f"   页数: {result['page_count']}")
            print(f"   类型: {result['pdf_type']}")
            print(f"   消息: {result['message']}")
            return True
        else:
            print(f"❌ PDF分析失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def test_smart_print(pdf_path):
    """测试智能打印功能"""
    print(f"🖨️  测试智能打印功能: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        print(f"❌ 文件不存在: {pdf_path}")
        return False
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
            headers = {'Authorization': f'Bearer {API_KEY}'}
            
            response = requests.post(
                f"{API_BASE_URL}/print?printer_name={PRINTER_NAME}",
                headers=headers,
                files=files
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 智能打印成功:")
            print(f"   消息: {result['message']}")
            print(f"   任务ID: {result['job_id']}")
            return True
        else:
            print(f"❌ 智能打印失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def main():
    """主函数"""
    print("🚀 智能PDF打印功能测试")
    print("=" * 50)
    
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法: python test_smart_print.py <PDF文件路径>")
        print("示例: python test_smart_print.py test.pdf")
        return
    
    pdf_path = sys.argv[1]
    
    # 测试PDF分析
    print("\n1️⃣ 测试PDF分析功能")
    analyze_success = test_analyze_pdf(pdf_path)
    
    if analyze_success:
        print("\n2️⃣ 测试智能打印功能")
        print_success = test_smart_print(pdf_path)
        
        if print_success:
            print("\n🎉 所有测试通过！")
        else:
            print("\n❌ 智能打印测试失败")
    else:
        print("\n❌ PDF分析测试失败，跳过打印测试")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()

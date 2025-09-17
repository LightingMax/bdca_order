#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试下载合集功能
"""

import os
import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_pdf_merge_function():
    """测试PDF拼接功能"""
    print("🧪 测试PDF拼接功能")
    print("=" * 50)
    
    try:
        from app.services.pdf_service import merge_processed_pdfs, create_download_collection
        
        # 使用实际存在的文件进行测试
        processed_files = [
            {
                'output_file': 'order_1_70fb35e5.pdf',
                'combined_type': 'hotel_accommodation',
                'amount': 200.0
            },
            {
                'output_file': 'order_1_f19e5c0c.pdf', 
                'combined_type': 'taxi_itinerary',
                'amount': 58.37
            },
            {
                'output_file': 'order_2_05df6ecd.pdf',
                'combined_type': 'taxi_itinerary', 
                'amount': 45.20
            }
        ]
        
        # 检查测试文件是否存在
        from app import Config
        test_files_exist = []
        for file_info in processed_files:
            file_path = os.path.join(Config.OUTPUT_FOLDER, file_info['output_file'])
            if os.path.exists(file_path):
                test_files_exist.append(file_info)
                print(f"✅ 找到测试文件: {file_info['output_file']}")
            else:
                print(f"⚠️ 测试文件不存在: {file_info['output_file']}")
        
        if not test_files_exist:
            print("❌ 没有找到可用的测试文件")
            return False
        
        # 测试拼接功能
        output_path = os.path.join(Config.OUTPUT_FOLDER, "test_merged_collection.pdf")
        print(f"\n🔄 开始测试PDF拼接...")
        print(f"   输入文件数: {len(test_files_exist)}")
        print(f"   输出路径: {output_path}")
        
        success = merge_processed_pdfs(test_files_exist, output_path)
        
        if success and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ PDF拼接测试成功!")
            print(f"   输出文件: {output_path}")
            print(f"   文件大小: {file_size} bytes")
            return True
        else:
            print("❌ PDF拼接测试失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        return False

def test_download_collection_function():
    """测试下载合集创建功能"""
    print("\n🧪 测试下载合集创建功能")
    print("=" * 50)
    
    try:
        from app.services.pdf_service import create_download_collection
        
        # 使用实际存在的文件进行测试
        processed_files = [
            {
                'output_file': 'order_1_70fb35e5.pdf',
                'combined_type': 'hotel_accommodation',
                'amount': 200.0
            },
            {
                'output_file': 'order_1_f19e5c0c.pdf', 
                'combined_type': 'taxi_itinerary',
                'amount': 58.37
            },
            {
                'output_file': 'order_2_05df6ecd.pdf',
                'combined_type': 'taxi_itinerary', 
                'amount': 45.20
            }
        ]
        
        # 检查测试文件是否存在
        from app import Config
        test_files_exist = []
        for file_info in processed_files:
            file_path = os.path.join(Config.OUTPUT_FOLDER, file_info['output_file'])
            if os.path.exists(file_path):
                test_files_exist.append(file_info)
        
        if not test_files_exist:
            print("❌ 没有找到可用的测试文件")
            return False
        
        # 测试合集创建功能
        print(f"\n🔄 开始测试合集创建...")
        result = create_download_collection(test_files_exist, "测试报销单据合集")
        
        if result['success']:
            print(f"✅ 合集创建测试成功!")
            print(f"   文件名: {result['filename']}")
            print(f"   文件路径: {result['file_path']}")
            print(f"   文件数量: {result['file_count']}")
            
            # 验证文件是否存在
            if os.path.exists(result['file_path']):
                file_size = os.path.getsize(result['file_path'])
                print(f"   文件大小: {file_size} bytes")
                return True
            else:
                print("❌ 输出文件不存在")
                return False
        else:
            print(f"❌ 合集创建测试失败: {result['message']}")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        return False

def main():
    """主函数"""
    print("🚀 下载合集功能测试")
    print("=" * 60)
    
    # 检查必要的工具
    import shutil
    if not shutil.which('pdftk'):
        print("❌ pdftk工具不可用，请先安装")
        return False
    
    # 运行测试
    tests = [
        test_pdf_merge_function,
        test_download_collection_function
    ]
    
    success_count = 0
    for test in tests:
        try:
            if test():
                success_count += 1
        except Exception as e:
            print(f"❌ 测试 {test.__name__} 失败: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {success_count}/{len(tests)} 通过")
    
    if success_count == len(tests):
        print("🎉 所有测试完成！下载合集功能已就绪")
        print("\n💡 现在您可以：")
        print("   1. 启动应用程序")
        print("   2. 上传ZIP文件进行处理")
        print("   3. 点击'下载合集'按钮下载所有PDF文件")
    else:
        print("⚠️ 部分测试失败，请检查相关配置")
    
    return success_count == len(tests)

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 程序执行错误: {e}")
        sys.exit(1)
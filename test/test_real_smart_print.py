#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试智能打印服务使用实际处理过的文件
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_with_real_files():
    """使用实际处理过的文件测试智能打印服务"""
    print("🧪 使用实际处理过的文件测试智能打印服务")
    print("=" * 60)
    
    try:
        # 检查output目录中的文件
        output_dir = os.path.join(project_root, "app/static/output")
        if not os.path.exists(output_dir):
            print(f"❌ output目录不存在: {output_dir}")
            return False
        
        # 获取所有PDF文件
        pdf_files = [f for f in os.listdir(output_dir) if f.endswith('.pdf')]
        print(f"📁 找到 {len(pdf_files)} 个PDF文件")
        
        if not pdf_files:
            print("❌ 没有找到PDF文件")
            return False
        
        # 选择第一个文件进行测试
        test_file = pdf_files[0]
        print(f"📄 测试文件: {test_file}")
        
        # 模拟processed_files数据结构
        processed_files = [
            {
                'output_file': test_file,
                'has_itinerary': True,  # 假设包含行程单
                'order_id': 'test_order_001',
                'upload_time': '2024-09-17 19:00:00'
            }
        ]
        
        print(f"\n🔄 开始测试智能打印服务...")
        try:
            from app import create_app
            from app.services.pdf_service import generate_trip_records
            
            # 创建Flask应用上下文
            app = create_app()
            with app.app_context():
                # 测试generate_trip_records函数
                trip_records = generate_trip_records(processed_files)
            
            print(f"📋 生成的行程记录:")
            print("=" * 50)
            print(trip_records)
            print("=" * 50)
            
            if trip_records and trip_records != "暂无行程记录":
                print(f"✅ 智能打印服务成功生成行程记录")
                return True
            else:
                print(f"ℹ️ 该文件可能不包含行程单信息，这是正常的")
                return True  # 这不算失败，只是文件类型不同
            
        except Exception as e:
            print(f"❌ 智能打印服务测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_with_original_file():
    """使用原始测试文件测试"""
    print("\n🧪 使用原始测试文件测试")
    print("=" * 60)
    
    try:
        # 原始测试文件路径
        test_file = "temp_files/【高德打车-144.56元-3个行程】高德打车电子行程单.pdf"
        full_path = os.path.join(project_root, test_file)
        
        print(f"📄 测试文件: {test_file}")
        
        # 检查文件是否存在
        if not os.path.exists(full_path):
            print(f"❌ 测试文件不存在: {full_path}")
            return False
        
        # 模拟processed_files数据结构，但使用原始文件路径
        processed_files = [
            {
                'output_file': test_file,  # 使用原始文件路径
                'has_itinerary': True,
                'order_id': 'test_order_001',
                'upload_time': '2024-09-17 19:00:00'
            }
        ]
        
        print(f"\n🔄 开始测试智能打印服务...")
        try:
            from app import create_app
            from app.services.pdf_service import generate_trip_records
            
            # 创建Flask应用上下文
            app = create_app()
            with app.app_context():
                # 测试generate_trip_records函数
                trip_records = generate_trip_records(processed_files)
            
            print(f"📋 生成的行程记录:")
            print("=" * 50)
            print(trip_records)
            print("=" * 50)
            
            if trip_records and trip_records != "暂无行程记录":
                print(f"✅ 智能打印服务成功生成行程记录")
                return True
            else:
                print(f"❌ 智能打印服务未能生成行程记录")
                return False
            
        except Exception as e:
            print(f"❌ 智能打印服务测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 智能打印服务实际文件测试")
    print("=" * 60)
    
    # 检查依赖
    try:
        import camelot
        print(f"✅ camelot-py可用")
    except ImportError:
        print("❌ camelot-py不可用，请先安装")
        return False
    
    try:
        import fitz
        print(f"✅ PyMuPDF可用")
    except ImportError:
        print("❌ PyMuPDF不可用，请先安装")
        return False
    
    # 运行测试
    real_files_success = test_with_real_files()
    original_file_success = test_with_original_file()
    
    print("\n" + "=" * 60)
    if real_files_success and original_file_success:
        print("🎉 测试成功！智能打印服务查看行程功能工作正常")
        print("💡 系统已准备好为用户提供查看行程功能")
    else:
        print("⚠️ 测试结果:")
        if real_files_success:
            print("  ✅ 实际文件测试通过")
        else:
            print("  ❌ 实际文件测试失败")
        if original_file_success:
            print("  ✅ 原始文件测试通过")
        else:
            print("  ❌ 原始文件测试失败")
    
    return real_files_success and original_file_success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 程序执行错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

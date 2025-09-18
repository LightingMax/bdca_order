#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的行程信息提取和缓存流程
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_new_trip_flow():
    """测试新的行程信息提取和缓存流程"""
    print("🧪 测试新的行程信息提取和缓存流程")
    print("=" * 60)
    
    try:
        # 测试文件路径
        test_file = "temp_files/【高德打车-144.56元-3个行程】高德打车电子行程单.pdf"
        full_path = os.path.join(project_root, test_file)
        
        print(f"📄 测试文件: {test_file}")
        
        # 检查文件是否存在
        if not os.path.exists(full_path):
            print(f"❌ 测试文件不存在: {full_path}")
            return False
        
        print(f"\n🔄 开始测试新的流程...")
        try:
            from app import create_app
            from app.services.pdf_service import extract_trip_info_from_itinerary, generate_trip_records
            
            # 创建Flask应用上下文
            app = create_app()
            with app.app_context():
                # 第一步：模拟文件处理阶段，提取行程信息
                print("📋 第一步：提取行程信息...")
                trip_info = extract_trip_info_from_itinerary(full_path)
                
                if trip_info:
                    print(f"✅ 成功提取到 {len(trip_info)} 个行程信息:")
                    for i, trip in enumerate(trip_info, 1):
                        print(f"  行程{i}: {trip}")
                else:
                    print("❌ 未能提取到行程信息")
                    return False
                
                # 第二步：模拟processed_files数据结构（包含缓存的行程信息）
                print(f"\n📋 第二步：模拟processed_files数据结构...")
                processed_files = [
                    {
                        'output_file': 'test_output.pdf',
                        'has_itinerary': True,
                        'order_id': 'test_order_001',
                        'upload_time': '2024-09-17 19:00:00',
                        'trip_info': trip_info,  # 缓存的行程信息
                        'itinerary_file': full_path
                    }
                ]
                
                # 第三步：测试generate_trip_records函数
                print(f"\n📋 第三步：测试generate_trip_records函数...")
                trip_records = generate_trip_records(processed_files)
                
                print(f"📋 生成的行程记录:")
                print("=" * 50)
                print(trip_records)
                print("=" * 50)
                
                if trip_records and trip_records != "暂无行程记录":
                    print(f"✅ 新的流程成功生成行程记录")
                    return True
                else:
                    print(f"❌ 新的流程未能生成行程记录")
                    return False
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_files():
    """测试多个文件的行程记录生成"""
    print("\n🧪 测试多个文件的行程记录生成")
    print("=" * 60)
    
    try:
        # 测试文件路径
        test_file = "temp_files/【高德打车-144.56元-3个行程】高德打车电子行程单.pdf"
        full_path = os.path.join(project_root, test_file)
        
        if not os.path.exists(full_path):
            print(f"❌ 测试文件不存在: {full_path}")
            return False
        
        print(f"\n🔄 开始测试多个文件流程...")
        try:
            from app import create_app
            from app.services.pdf_service import extract_trip_info_from_itinerary, generate_trip_records
            
            # 创建Flask应用上下文
            app = create_app()
            with app.app_context():
                # 提取行程信息
                trip_info = extract_trip_info_from_itinerary(full_path)
                
                if not trip_info:
                    print("❌ 未能提取到行程信息")
                    return False
                
                # 模拟多个文件的processed_files数据结构
                processed_files = [
                    {
                        'output_file': 'test_output_1.pdf',
                        'has_itinerary': True,
                        'order_id': 'test_order_001',
                        'upload_time': '2024-09-17 19:00:00',
                        'trip_info': trip_info,
                        'itinerary_file': full_path
                    },
                    {
                        'output_file': 'test_output_2.pdf',
                        'has_itinerary': False,  # 这个文件不包含行程单
                        'order_id': 'test_order_002',
                        'upload_time': '2024-09-17 19:05:00'
                    },
                    {
                        'output_file': 'test_output_3.pdf',
                        'has_itinerary': True,
                        'order_id': 'test_order_003',
                        'upload_time': '2024-09-17 19:10:00',
                        'trip_info': trip_info,  # 使用相同的行程信息进行测试
                        'itinerary_file': full_path
                    }
                ]
                
                # 测试generate_trip_records函数
                trip_records = generate_trip_records(processed_files)
                
                print(f"📋 生成的行程记录:")
                print("=" * 50)
                print(trip_records)
                print("=" * 50)
                
                if trip_records and trip_records != "暂无行程记录":
                    print(f"✅ 多个文件流程成功生成行程记录")
                    return True
                else:
                    print(f"❌ 多个文件流程未能生成行程记录")
                    return False
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
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
    print("🚀 新的行程信息提取和缓存流程测试")
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
    single_file_success = test_new_trip_flow()
    multiple_files_success = test_multiple_files()
    
    print("\n" + "=" * 60)
    if single_file_success and multiple_files_success:
        print("🎉 测试成功！新的行程信息提取和缓存流程工作正常")
        print("💡 系统已准备好为用户提供查看行程功能")
        print("💡 支持单个ZIP和批量ZIP的行程查看")
    else:
        print("⚠️ 测试结果:")
        if single_file_success:
            print("  ✅ 单个文件流程测试通过")
        else:
            print("  ❌ 单个文件流程测试失败")
        if multiple_files_success:
            print("  ✅ 多个文件流程测试通过")
        else:
            print("  ❌ 多个文件流程测试失败")
    
    return single_file_success and multiple_files_success


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

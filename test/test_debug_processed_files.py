#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试processed_files数据结构，检查trip_info字段
"""

import os
import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def debug_processed_files():
    """调试processed_files数据结构"""
    print("🔍 调试processed_files数据结构")
    print("=" * 60)
    
    try:
        # 模拟processed_files数据结构
        processed_files = [
            {
                'order_id': 'order_1_272b1397',
                'amount': 144.56,
                'output_file': 'order_1_272b1397.pdf',
                'has_itinerary': True,
                'has_invoice': True,
                'has_hotel_bill': False,
                'page_count': 1,
                'combined_type': 'single_page'
                # 注意：这个文件没有trip_info字段，因为是之前处理的
            }
        ]
        
        print("📋 模拟的processed_files数据结构:")
        print(json.dumps(processed_files, indent=2, ensure_ascii=False))
        
        # 检查每个文件的字段
        print(f"\n🔍 检查文件字段:")
        for i, file_info in enumerate(processed_files):
            print(f"文件 {i+1}:")
            print(f"  - order_id: {file_info.get('order_id')}")
            print(f"  - has_itinerary: {file_info.get('has_itinerary')}")
            print(f"  - trip_info: {file_info.get('trip_info', '❌ 缺失')}")
            print(f"  - itinerary_file: {file_info.get('itinerary_file', '❌ 缺失')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 调试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_generate_trip_records_with_missing_trip_info():
    """测试generate_trip_records函数处理缺失trip_info的情况"""
    print("\n🧪 测试generate_trip_records函数处理缺失trip_info的情况")
    print("=" * 60)
    
    try:
        from app import create_app
        from app.services.pdf_service import generate_trip_records
        
        # 模拟缺失trip_info的processed_files
        processed_files = [
            {
                'order_id': 'order_1_272b1397',
                'amount': 144.56,
                'output_file': 'order_1_272b1397.pdf',
                'has_itinerary': True,
                'has_invoice': True,
                'has_hotel_bill': False,
                'page_count': 1,
                'combined_type': 'single_page'
                # 注意：没有trip_info字段
            }
        ]
        
        # 创建Flask应用上下文
        app = create_app()
        with app.app_context():
            # 测试generate_trip_records函数
            trip_records = generate_trip_records(processed_files)
            
            print(f"📋 生成的行程记录:")
            print("=" * 50)
            print(trip_records)
            print("=" * 50)
            
            if trip_records == "暂无行程记录":
                print("✅ 正确处理了缺失trip_info的情况")
                return True
            else:
                print("❌ 没有正确处理缺失trip_info的情况")
                return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_with_trip_info():
    """测试包含trip_info的情况"""
    print("\n🧪 测试包含trip_info的情况")
    print("=" * 60)
    
    try:
        from app import create_app
        from app.services.pdf_service import generate_trip_records
        
        # 模拟包含trip_info的processed_files
        trip_info = [
            {
                'sequence': '1',
                'service_provider': '旅程易到',
                'car_type': '旅程易到经济型',
                'pickup_time': '2024-06-19 12:32',
                'city': '北京市',
                'start_point': '北京南站-东停车场M层(夹层)-B2~B5通道',
                'end_point': '航天智能院',
                'amount': 53.89
            },
            {
                'sequence': '2',
                'service_provider': '旅程易到',
                'car_type': '旅程易到经济型',
                'pickup_time': '2024-06-20 18:59',
                'city': '北京市',
                'start_point': '航天智能院',
                'end_point': '汉庭优佳北京石景山首钢园酒店',
                'amount': 16.12
            },
            {
                'sequence': '3',
                'service_provider': '旅程易到',
                'car_type': '旅程易到经济型',
                'pickup_time': '2024-06-21 08:18',
                'city': '北京市',
                'start_point': '汉庭优佳酒店(北京石景山首钢园店)',
                'end_point': '北京南站(东进站口)',
                'amount': 74.55
            }
        ]
        
        processed_files = [
            {
                'order_id': 'test_order_001',
                'amount': 144.56,
                'output_file': 'test_output.pdf',
                'has_itinerary': True,
                'has_invoice': True,
                'has_hotel_bill': False,
                'page_count': 1,
                'combined_type': 'single_page',
                'trip_info': trip_info,  # 包含行程信息
                'itinerary_file': 'test_itinerary.pdf'
            }
        ]
        
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
                print("✅ 正确处理了包含trip_info的情况")
                return True
            else:
                print("❌ 没有正确处理包含trip_info的情况")
                return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 调试processed_files数据结构")
    print("=" * 60)
    
    # 运行测试
    debug_success = debug_processed_files()
    missing_trip_info_success = test_generate_trip_records_with_missing_trip_info()
    with_trip_info_success = test_with_trip_info()
    
    print("\n" + "=" * 60)
    print("📊 测试结果:")
    print(f"  - 数据结构调试: {'✅' if debug_success else '❌'}")
    print(f"  - 缺失trip_info处理: {'✅' if missing_trip_info_success else '❌'}")
    print(f"  - 包含trip_info处理: {'✅' if with_trip_info_success else '❌'}")
    
    if debug_success and missing_trip_info_success and with_trip_info_success:
        print("\n🎉 所有测试通过！")
        print("💡 问题分析：")
        print("  - 已存在的文件没有trip_info字段（正常）")
        print("  - generate_trip_records正确处理了缺失trip_info的情况")
        print("  - 包含trip_info的文件能正确生成行程记录")
        print("  - 需要确保新上传的文件正确包含trip_info字段")
    else:
        print("\n⚠️ 部分测试失败，需要进一步调试")
    
    return debug_success and missing_trip_info_success and with_trip_info_success


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

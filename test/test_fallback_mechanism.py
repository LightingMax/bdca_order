#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试回退机制：当没有缓存的trip_info时，从原始行程单文件中提取
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_fallback_mechanism():
    """测试回退机制"""
    print("🧪 测试回退机制")
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
        
        print(f"\n🔄 开始测试回退机制...")
        try:
            from app import create_app
            from app.services.pdf_service import generate_trip_records
            
            # 创建Flask应用上下文
            app = create_app()
            with app.app_context():
                # 模拟没有trip_info但有itinerary_file的processed_files
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
                        # 注意：没有trip_info字段
                        'itinerary_file': full_path  # 但有原始行程单文件路径
                    }
                ]
                
                # 测试generate_trip_records函数
                trip_records = generate_trip_records(processed_files)
                
                print(f"📋 生成的行程记录:")
                print("=" * 50)
                print(trip_records)
                print("=" * 50)
                
                if trip_records and trip_records != "暂无行程记录":
                    print(f"✅ 回退机制成功，生成了行程记录")
                    return True
                else:
                    print(f"❌ 回退机制失败，未能生成行程记录")
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


def test_no_itinerary_file():
    """测试没有itinerary_file的情况"""
    print("\n🧪 测试没有itinerary_file的情况")
    print("=" * 60)
    
    try:
        from app import create_app
        from app.services.pdf_service import generate_trip_records
        
        # 创建Flask应用上下文
        app = create_app()
        with app.app_context():
            # 模拟既没有trip_info也没有itinerary_file的processed_files
            processed_files = [
                {
                    'order_id': 'test_order_001',
                    'amount': 144.56,
                    'output_file': 'test_output.pdf',
                    'has_itinerary': True,
                    'has_invoice': True,
                    'has_hotel_bill': False,
                    'page_count': 1,
                    'combined_type': 'single_page'
                    # 注意：既没有trip_info也没有itinerary_file
                }
            ]
            
            # 测试generate_trip_records函数
            trip_records = generate_trip_records(processed_files)
            
            print(f"📋 生成的行程记录:")
            print("=" * 50)
            print(trip_records)
            print("=" * 50)
            
            if trip_records == "暂无行程记录":
                print("✅ 正确处理了没有itinerary_file的情况")
                return True
            else:
                print("❌ 没有正确处理没有itinerary_file的情况")
                return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mixed_scenarios():
    """测试混合场景：有些文件有trip_info，有些没有"""
    print("\n🧪 测试混合场景")
    print("=" * 60)
    
    try:
        # 测试文件路径
        test_file = "temp_files/【高德打车-144.56元-3个行程】高德打车电子行程单.pdf"
        full_path = os.path.join(project_root, test_file)
        
        if not os.path.exists(full_path):
            print(f"❌ 测试文件不存在: {full_path}")
            return False
        
        from app import create_app
        from app.services.pdf_service import generate_trip_records
        
        # 创建Flask应用上下文
        app = create_app()
        with app.app_context():
            # 模拟混合场景的processed_files
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
                }
            ]
            
            processed_files = [
                {
                    'order_id': 'test_order_001',
                    'amount': 53.89,
                    'output_file': 'test_output_1.pdf',
                    'has_itinerary': True,
                    'has_invoice': True,
                    'has_hotel_bill': False,
                    'page_count': 1,
                    'combined_type': 'single_page',
                    'trip_info': trip_info,  # 有缓存的行程信息
                    'itinerary_file': full_path
                },
                {
                    'order_id': 'test_order_002',
                    'amount': 90.67,
                    'output_file': 'test_output_2.pdf',
                    'has_itinerary': True,
                    'has_invoice': True,
                    'has_hotel_bill': False,
                    'page_count': 1,
                    'combined_type': 'single_page',
                    # 没有trip_info，但有itinerary_file
                    'itinerary_file': full_path
                },
                {
                    'order_id': 'test_order_003',
                    'amount': 0.0,
                    'output_file': 'test_output_3.pdf',
                    'has_itinerary': False,  # 不包含行程单
                    'has_invoice': True,
                    'has_hotel_bill': False,
                    'page_count': 1,
                    'combined_type': 'single_page'
                }
            ]
            
            # 测试generate_trip_records函数
            trip_records = generate_trip_records(processed_files)
            
            print(f"📋 生成的行程记录:")
            print("=" * 50)
            print(trip_records)
            print("=" * 50)
            
            if trip_records and trip_records != "暂无行程记录":
                print("✅ 混合场景测试成功，生成了行程记录")
                return True
            else:
                print("❌ 混合场景测试失败，未能生成行程记录")
                return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 回退机制测试")
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
    fallback_success = test_fallback_mechanism()
    no_itinerary_success = test_no_itinerary_file()
    mixed_success = test_mixed_scenarios()
    
    print("\n" + "=" * 60)
    print("📊 测试结果:")
    print(f"  - 回退机制测试: {'✅' if fallback_success else '❌'}")
    print(f"  - 没有itinerary_file测试: {'✅' if no_itinerary_success else '❌'}")
    print(f"  - 混合场景测试: {'✅' if mixed_success else '❌'}")
    
    if fallback_success and no_itinerary_success and mixed_success:
        print("\n🎉 所有测试通过！")
        print("💡 回退机制工作正常：")
        print("  - 优先使用缓存的trip_info")
        print("  - 如果没有缓存，从原始行程单文件提取")
        print("  - 如果都没有，返回'暂无行程记录'")
        print("  - 支持混合场景（部分文件有缓存，部分没有）")
    else:
        print("\n⚠️ 部分测试失败，需要进一步调试")
    
    return fallback_success and no_itinerary_success and mixed_success


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

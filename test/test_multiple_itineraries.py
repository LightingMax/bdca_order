#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多个行程单的处理逻辑
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_multiple_itineraries():
    """测试多个行程单的处理逻辑"""
    print("🧪 测试多个行程单的处理逻辑")
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
        
        print(f"\n🔄 开始测试多个行程单处理...")
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
                
                print(f"✅ 成功提取到 {len(trip_info)} 个行程信息")
                for i, trip in enumerate(trip_info, 1):
                    print(f"  行程{i}: {trip}")
                
                # 模拟多个行程单的processed_files数据结构
                # 每个行程单都有独立的trip_info
                processed_files = [
                    {
                        'output_file': 'test_output_1.pdf',
                        'has_itinerary': True,
                        'order_id': 'test_order_001',
                        'upload_time': '2024-09-17 19:00:00',
                        'trip_info': trip_info,  # 第一个行程单的行程信息
                        'itinerary_file': full_path
                    },
                    {
                        'output_file': 'test_output_2.pdf',
                        'has_itinerary': True,
                        'order_id': 'test_order_002',
                        'upload_time': '2024-09-17 19:05:00',
                        'trip_info': trip_info,  # 第二个行程单的行程信息（相同内容用于测试）
                        'itinerary_file': full_path
                    },
                    {
                        'output_file': 'test_output_3.pdf',
                        'has_itinerary': True,
                        'order_id': 'test_order_003',
                        'upload_time': '2024-09-17 19:10:00',
                        'trip_info': trip_info,  # 第三个行程单的行程信息
                        'itinerary_file': full_path
                    }
                ]
                
                # 测试generate_trip_records函数
                trip_records = generate_trip_records(processed_files)
                
                print(f"\n📋 生成的行程记录:")
                print("=" * 50)
                print(trip_records)
                print("=" * 50)
                
                # 验证结果
                lines = trip_records.split('\n')
                trip_lines = [line for line in lines if line.strip() and not line.startswith('=') and line != '行程记录']
                
                print(f"\n🔍 验证结果:")
                print(f"  - 总行数: {len(lines)}")
                print(f"  - 行程行数: {len(trip_lines)}")
                print(f"  - 期望行程行数: {len(trip_info) * 3} (3个行程单 × {len(trip_info)}个行程)")
                
                if len(trip_lines) == len(trip_info) * 3:
                    print("✅ 多个行程单处理成功，所有行程都被正确显示")
                    return True
                else:
                    print("❌ 多个行程单处理失败，行程数量不匹配")
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


def test_simplified_format():
    """测试简化后的格式"""
    print("\n🧪 测试简化后的格式")
    print("=" * 60)
    
    try:
        from app import create_app
        from app.services.pdf_service import generate_trip_records
        
        # 创建Flask应用上下文
        app = create_app()
        with app.app_context():
            # 模拟包含raw_data的行程信息
            trip_info = [
                {
                    'raw_data': ['1\n旅程易到', '旅程易到经济型 2024-06-19 12:32', '北京市', '航天智能院', '53.89元'],
                    'sequence': '1\n旅程易到',
                    'pickup_time': '旅程易到经济型 2024-06-19 12:32',
                    'city': '北京市',
                    'location': '航天智能院',
                    'amount': '53.89元'
                },
                {
                    'raw_data': ['2\n旅程易到', '旅程易到经济型 2024-06-20 18:59', '北京市\n航天智能院', '汉庭优佳北京石景山首钢园酒店', '16.12元'],
                    'sequence': '2\n旅程易到',
                    'pickup_time': '旅程易到经济型 2024-06-20 18:59',
                    'city': '北京市\n航天智能院',
                    'location': '汉庭优佳北京石景山首钢园酒店',
                    'amount': '16.12元'
                }
            ]
            
            processed_files = [
                {
                    'output_file': 'test_output.pdf',
                    'has_itinerary': True,
                    'order_id': 'test_order_001',
                    'upload_time': '2024-09-17 19:00:00',
                    'trip_info': trip_info,
                    'itinerary_file': 'test_itinerary.pdf'
                }
            ]
            
            # 测试generate_trip_records函数
            trip_records = generate_trip_records(processed_files)
            
            print(f"📋 生成的行程记录:")
            print("=" * 50)
            print(trip_records)
            print("=" * 50)
            
            # 验证是否使用了raw_data格式
            if '1\n旅程易到, 旅程易到经济型 2024-06-19 12:32, 北京市, 航天智能院, 53.89元' in trip_records:
                print("✅ 简化格式测试成功，使用了raw_data格式")
                return True
            else:
                print("❌ 简化格式测试失败，没有使用raw_data格式")
                return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 多个行程单处理逻辑测试")
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
    multiple_success = test_multiple_itineraries()
    format_success = test_simplified_format()
    
    print("\n" + "=" * 60)
    print("📊 测试结果:")
    print(f"  - 多个行程单处理: {'✅' if multiple_success else '❌'}")
    print(f"  - 简化格式: {'✅' if format_success else '❌'}")
    
    if multiple_success and format_success:
        print("\n🎉 所有测试通过！")
        print("💡 修复内容：")
        print("  - 为每个PDF文件创建唯一的订单ID，避免覆盖")
        print("  - 简化行程信息格式，直接使用camelot提取的原始数据")
        print("  - 支持多个行程单的行程信息正确合并显示")
    else:
        print("\n⚠️ 部分测试失败，需要进一步调试")
    
    return multiple_success and format_success


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

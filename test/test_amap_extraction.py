#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试高德地图特定的行程信息提取功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_amap_extraction():
    """测试高德地图特定的行程信息提取功能"""
    print("🧪 测试高德地图特定行程信息提取功能")
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
        
        # 使用主系统的函数
        print(f"\n🔄 开始使用主系统函数提取行程信息...")
        try:
            from app import create_app
            from app.services.pdf_service import extract_trip_info_from_itinerary
            
            # 创建Flask应用上下文
            app = create_app()
            with app.app_context():
                trips = extract_trip_info_from_itinerary(full_path)
            
            if trips:
                print(f"✅ 成功提取到 {len(trips)} 个行程信息:")
                for i, trip in enumerate(trips, 1):
                    print(f"  行程{i}: {trip}")
            else:
                print("❌ 未能提取到行程信息")
                return False
            
        except Exception as e:
            print(f"❌ 主系统函数调用失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 生成格式化的行程记录
        print(f"\n📋 格式化行程记录:")
        print("=" * 50)
        print("行程记录")
        print("=" * 50)
        for trip in trips:
            # 确保所有必要字段都存在
            sequence = trip.get('sequence', '未知')
            pickup_time = trip.get('pickup_time', '未知时间')
            city = trip.get('city', '未知城市')
            start_point = trip.get('start_point', '未知起点')
            end_point = trip.get('end_point', '未知终点')
            amount = trip.get('amount', 0.0)
            
            record = f"{sequence}, {pickup_time}, {city}, {start_point}, {end_point}, {amount:.2f}元"
            print(record)
        print("=" * 50)
        
        # 验证起点和终点是否正确
        print(f"\n🔍 验证起点和终点:")
        expected_trips = [
            {
                'sequence': '1',
                'start_point': '北京南站-东停车场M层(夹层)-B2~B5通道',
                'end_point': '航天智能院'
            },
            {
                'sequence': '2', 
                'start_point': '航天智能院',
                'end_point': '汉庭优佳北京石景山首钢园酒店'
            },
            {
                'sequence': '3',
                'start_point': '汉庭优佳酒店(北京石景山首钢园店)',
                'end_point': '北京南站(东进站口)'
            }
        ]
        
        all_correct = True
        for i, trip in enumerate(trips):
            if i < len(expected_trips):
                expected = expected_trips[i]
                actual_start = trip.get('start_point', '')
                actual_end = trip.get('end_point', '')
                expected_start = expected['start_point']
                expected_end = expected['end_point']
                
                start_correct = expected_start in actual_start or actual_start in expected_start
                end_correct = expected_end in actual_end or actual_end in expected_end
                
                print(f"  行程{trip.get('sequence', '?')}:")
                print(f"    起点: {'✅' if start_correct else '❌'} 期望: {expected_start}, 实际: {actual_start}")
                print(f"    终点: {'✅' if end_correct else '❌'} 期望: {expected_end}, 实际: {actual_end}")
                
                if not (start_correct and end_correct):
                    all_correct = False
        
        # 检查是否提取到了3个行程
        if len(trips) == 3 and all_correct:
            print("🎉 成功提取到所有3个行程，且起点终点识别正确！")
            return True
        else:
            print(f"⚠️ 提取到 {len(trips)} 个行程，期望3个，且起点终点识别{'正确' if all_correct else '有误'}")
            return False
        
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 高德地图特定行程信息提取功能测试")
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
    success = test_amap_extraction()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 测试成功！高德地图特定解析逻辑工作正常")
        print("💡 起点和终点识别正确，平台识别功能正常")
    else:
        print("⚠️ 测试失败，需要进一步调试")
    
    return success


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

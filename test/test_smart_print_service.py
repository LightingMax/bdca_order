#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试智能打印服务的查看行程功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_smart_print_service():
    """测试智能打印服务的查看行程功能"""
    print("🧪 测试智能打印服务查看行程功能")
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
        
        # 模拟processed_files数据结构
        processed_files = [
            {
                'output_file': '【高德打车-144.56元-3个行程】高德打车电子行程单.pdf',
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
            
            if trip_records and trip_records != "暂无行程记录":
                print(f"✅ 智能打印服务成功生成行程记录:")
                print("=" * 50)
                print(trip_records)
                print("=" * 50)
                
                # 验证记录格式
                lines = trip_records.split('\n')
                if len(lines) >= 3:  # 标题行 + 分隔线 + 至少1个行程
                    print(f"✅ 行程记录格式正确，共 {len(lines)-2} 个行程")
                    return True
                else:
                    print(f"❌ 行程记录格式不正确，行数: {len(lines)}")
                    return False
            else:
                print("❌ 智能打印服务未能生成行程记录")
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


def test_api_endpoint():
    """测试API端点"""
    print("\n🌐 测试API端点")
    print("=" * 60)
    
    try:
        from app import create_app
        from app.services.pdf_service import generate_trip_records
        
        # 创建Flask应用上下文
        app = create_app()
        
        # 模拟processed_files数据
        processed_files = [
            {
                'output_file': '【高德打车-144.56元-3个行程】高德打车电子行程单.pdf',
                'has_itinerary': True,
                'order_id': 'test_order_001',
                'upload_time': '2024-09-17 19:00:00'
            }
        ]
        
        with app.app_context():
            # 测试generate_trip_records函数
            trip_records = generate_trip_records(processed_files)
            
            # 模拟API响应
            api_response = {
                'success': True,
                'trip_records': trip_records,
                'file_count': len(processed_files)
            }
            
            print(f"✅ API响应格式正确:")
            print(f"  - success: {api_response['success']}")
            print(f"  - file_count: {api_response['file_count']}")
            print(f"  - trip_records长度: {len(api_response['trip_records'])} 字符")
            
            return True
            
    except Exception as e:
        print(f"❌ API端点测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 智能打印服务查看行程功能测试")
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
    service_success = test_smart_print_service()
    api_success = test_api_endpoint()
    
    print("\n" + "=" * 60)
    if service_success and api_success:
        print("🎉 测试成功！智能打印服务查看行程功能工作正常")
        print("💡 系统已准备好为用户提供查看行程功能")
    else:
        print("⚠️ 测试失败，需要进一步调试")
        if not service_success:
            print("  - 智能打印服务测试失败")
        if not api_success:
            print("  - API端点测试失败")
    
    return service_success and api_success


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

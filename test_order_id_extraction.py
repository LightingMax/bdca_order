#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试改进的订单ID提取逻辑
"""

import sys
import os

# 添加项目路径到sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_order_id_extraction():
    """测试订单ID提取功能"""
    
    # 模拟文件名列表
    test_filenames = [
        # 阳光出行格式
        "阳光出行-32.13元-3个行程-行程单.pdf",
        "阳光出行-32.13元-3个行程-发票.pdf",
        
        # T3格式
        "T3-77.06-1-行程单.pdf",
        "T3-77.06-1-发票.pdf",
        
        # 其他服务商格式
        "高德打车-45.20元-2个行程-行程单.pdf",
        "滴滴出行-28.50-1-行程单.pdf",
        "美团打车-15.80元-行程单.pdf",
        
        # 订单号格式
        "订单12345-行程单.pdf",
        "trip001-行程单.pdf",
        
        # 数字格式
        "123456789-行程单.pdf",
        
        # 复杂格式
        "阳光出行-29.59元-1个行程-高德打车电子发票.pdf",
    ]
    
    print("🧪 测试改进的订单ID提取逻辑")
    print("=" * 60)
    
    try:
        # 导入PDF服务模块
        from app.services.pdf_service import extract_order_id
        
        print("✅ 成功导入PDF服务模块")
        print()
        
        # 测试每个文件名
        for i, filename in enumerate(test_filenames, 1):
            print(f"测试 {i:2d}: {filename}")
            
            # 模拟文件路径
            file_path = f"/tmp/test/{filename}"
            
            try:
                # 调用订单ID提取函数
                order_id = extract_order_id(file_path)
                print(f"   结果: {order_id}")
                
                # 分析结果
                if '-' in order_id:
                    parts = order_id.split('-')
                    if len(parts) == 3:
                        if '元' in order_id and '个行程' in order_id:
                            print(f"   📊 解析: 服务商={parts[0]}, 金额={parts[1]}, 数量={parts[2]}")
                        else:
                            print(f"   📊 解析: 服务商={parts[0]}, 金额={parts[1]}, 数量={parts[2]}")
                    elif len(parts) == 2:
                        if '元' in order_id:
                            print(f"   📊 解析: 服务商={parts[0]}, 金额={parts[1]}")
                        else:
                            print(f"   📊 解析: 服务商={parts[0]}, 金额={parts[1]}")
                else:
                    print(f"   📊 解析: 订单号={order_id}")
                    
            except Exception as e:
                print(f"   ❌ 错误: {e}")
            
            print()
        
        print("🎉 所有测试完成！")
        
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        print("💡 请确保在正确的目录下运行此脚本")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")


def test_smart_order_id_generation():
    """测试智能订单ID生成功能"""
    
    print("\n🔧 测试智能订单ID生成功能")
    print("=" * 60)
    
    try:
        from app.services.pdf_service import generate_smart_order_id
        
        test_cases = [
            "阳光出行-32.13元-3个行程-行程单.pdf",
            "T3-77.06-1-行程单.pdf",
            "高德打车-45.20-2个行程-发票.pdf",
            "滴滴出行-28.50-行程单.pdf",
            "美团打车-15.80元-1个行程-发票.pdf",
        ]
        
        for filename in test_cases:
            print(f"文件名: {filename}")
            smart_id = generate_smart_order_id(filename)
            if smart_id:
                print(f"智能ID: {smart_id}")
            else:
                print("智能ID: 无法生成")
            print()
            
    except Exception as e:
        print(f"❌ 智能订单ID测试失败: {e}")


if __name__ == "__main__":
    print("🚀 订单ID提取逻辑测试")
    print("=" * 60)
    
    # 测试基本功能
    test_order_id_extraction()
    
    # 测试智能生成功能
    test_smart_order_id_generation()
    
    print("\n📝 测试总结")
    print("=" * 60)
    print("改进后的订单ID提取逻辑支持以下格式：")
    print("1. 服务商-金额元-数量个行程: 阳光出行-32.13元-3个行程")
    print("2. 服务商-金额: T3-77.06")
    print("3. 订单号: 12345")
    print("4. 数字ID: 123456789")
    print("5. 智能生成: 阳光出行-32.13元-3个行程, T3-77.06-1")
    print()
    print("💡 保持自然的表达格式，提高可读性")
    print("💡 避免生成像'T3'这样不完整的订单ID")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的订单ID提取逻辑
支持从发票文件名中提取【】内的内容
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.pdf_service import extract_order_id

def test_order_id_extraction():
    """测试订单ID提取功能"""
    
    # 测试用例
    test_cases = [
        # 发票文件名格式：【(T3出行-77.06元-1个行程)】*发票
        "【(T3出行-77.06元-1个行程)】*发票.pdf",
        "【(阳光出行-32.13元-3个行程)】*发票.pdf",
        "【(高德打车-45.67元-2个行程)】*发票.pdf",
        
        # 普通文件名格式
        "T3出行-77.06元-1个行程.pdf",
        "阳光出行-32.13元-3个行程.pdf",
        "高德打车-45.67元-2个行程.pdf",
        
        # 其他格式
        "订单12345.pdf",
        "trip001.pdf",
        "unknown_file.pdf"
    ]
    
    print("🧪 测试新的订单ID提取逻辑")
    print("=" * 60)
    
    for i, filename in enumerate(test_cases, 1):
        print(f"\n{i}. 测试文件名: {filename}")
        
        try:
            # 模拟文件路径
            file_path = f"/tmp/{filename}"
            
            # 提取订单ID
            order_id = extract_order_id(file_path)
            
            print(f"   ✅ 提取结果: {order_id}")
            
            # 分析结果
            if '【' in filename and '】' in filename:
                if '【' in order_id or '】' in order_id:
                    print(f"   ⚠️  警告: 结果中仍包含【】符号")
                else:
                    print(f"   🎯 成功: 正确提取【】内内容")
            else:
                print(f"   📝 普通文件: 使用常规提取方法")
                
        except Exception as e:
            print(f"   ❌ 错误: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 测试完成！")

if __name__ == "__main__":
    test_order_id_extraction()

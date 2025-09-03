
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的订单ID提取逻辑
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.pdf_service import extract_order_id, generate_smart_order_id

def test_fixed_order_id():
    """测试修复后的订单ID提取"""
    
    test_cases = [
        # 发票文件名格式 - 应该优先提取【】内的内容
        "【T3出行-77.06元-1个行程】*发票.pdf",
        "【阳光出行-32.13元-3个行程】*发票.pdf",
        "【高德打车-45.67元-2个行程】*发票.pdf",
        
        # 普通文件名格式
        "T3出行-77.06元-1个行程.pdf",
        "阳光出行-32.13元-3个行程.pdf",
        "高德打车-45.67元-2个行程.pdf",
        
        # 问题格式 - 订单-53.21-1
        "订单-53.21-1.pdf",
        "订单-94.42-2.pdf",
        
        # 其他格式
        "T3-77.06-1.pdf",
        "YG-32.13-3.pdf"
    ]
    
    print("🧪 测试修复后的订单ID提取逻辑")
    print("=" * 80)
    
    for i, filename in enumerate(test_cases, 1):
        print(f"\n{i}. 测试: {filename}")
        
        try:
            # 模拟文件路径
            file_path = f"/tmp/{filename}"
            
            # 提取订单ID
            order_id = extract_order_id(file_path)
            print(f"   ✅ extract_order_id 结果: {order_id}")
            
            # 测试 generate_smart_order_id
            smart_id = generate_smart_order_id(filename)
            print(f"   🧠 generate_smart_order_id 结果: {smart_id}")
            
            # 分析结果
            if '【' in filename and '】' in filename:
                if '【' in order_id or '】' in order_id:
                    print(f"   ❌ 【】未正确处理")
                else:
                    print(f"   ✅ 【】正确处理")
            elif '订单-' in filename:
                if '订单-' in order_id:
                    print(f"   ✅ 订单格式正确处理")
                else:
                    print(f"   ❌ 订单格式未正确处理")
            else:
                print(f"   📝 普通格式处理")
                
        except Exception as e:
            print(f"   ❌ 错误: {e}")
    
    print("\n" + "=" * 80)
    print("🎉 测试完成！")

if __name__ == "__main__":
    test_fixed_order_id()

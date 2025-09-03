#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的订单格式匹配
"""

import re

def test_new_format():
    """测试新的订单格式"""
    
    test_cases = [
        # 原有格式
        "订单-29.59-1.pdf",
        "订单-94.42-2.pdf",
        
        # 新发现的格式
        "订单T3-77.06-1.pdf",
        "订单T3-45.67-2.pdf",
        
        # 其他格式
        "T3-77.06-1.pdf",
        "YG-32.13-3.pdf"
    ]
    
    print("🧪 测试新的订单格式匹配")
    print("=" * 60)
    
    for filename in test_cases:
        print(f"\n文件名: {filename}")
        
        # 模拟重构后的逻辑
        patterns = [
            (r'([^-]+)-(\d+\.\d+)元?-(\d+)个行程', lambda m: f"{m.group(1)}-{m.group(2)}元-{m.group(3)}个行程"),
            (r'([^-]+)-(\d+\.\d+)-(\d+)', lambda m: f"{m.group(1)}-{m.group(2)}元-{m.group(3)}个行程"),
            (r'订单-(\d+\.\d+)-(\d+)', lambda m: f"T3出行-{m.group(1)}元-{m.group(2)}个行程"),
            (r'订单T3-(\d+\.\d+)-(\d+)', lambda m: f"T3出行-{m.group(1)}元-{m.group(2)}个行程"),
        ]
        
        result = None
        for pattern, formatter in patterns:
            match = re.search(pattern, filename)
            if match:
                result = formatter(match)
                print(f"✅ 匹配模式: {pattern}")
                print(f"✅ 生成结果: {result}")
                break
        
        if not result:
            print(f"❌ 未匹配任何模式")

if __name__ == "__main__":
    test_new_format()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
只测试正则表达式逻辑，不依赖Flask
"""

import re

def test_regex_patterns():
    """测试各种正则表达式模式"""
    
    test_cases = [
        # 发票文件名格式
        "【T3出行-77.06元-1个行程】*发票.pdf",
        "【阳光出行-32.13元-3个行程】*发票.pdf",
        "【高德打车-45.67元-2个行程】*发票.pdf",
        
        # 问题格式
        "订单-53.21-1.pdf",
        "订单-94.42-2.pdf",
        
        # 其他格式
        "T3-77.06-1.pdf",
        "YG-32.13-3.pdf"
    ]
    
    print("🧪 测试正则表达式模式")
    print("=" * 60)
    
    for filename in test_cases:
        print(f"\n文件名: {filename}")
        
        # 测试【】提取
        bracket_pattern = r'【([^】]+)】'
        bracket_match = re.search(bracket_pattern, filename)
        if bracket_match:
            bracket_content = bracket_match.group(1)
            print(f"✅ 【】提取: {bracket_content}")
        else:
            print(f"❌ 【】提取: 未找到")
        
        # 测试订单格式
        order_pattern = r'订单-(\d+\.\d+)-(\d+)'
        order_match = re.search(order_pattern, filename)
        if order_match:
            amount, count = order_match.groups()
            print(f"✅ 订单格式提取: 金额={amount}, 数量={count}")
        else:
            print(f"❌ 订单格式提取: 未找到")
        
        # 测试标准格式
        standard_pattern = r'([^-]+)-(\d+\.\d+)元?-(\d+)个行程'
        standard_match = re.search(standard_pattern, filename)
        if standard_match:
            service, amount, count = standard_match.groups()
            print(f"✅ 标准格式提取: 服务商={service}, 金额={amount}, 数量={count}")
        else:
            print(f"❌ 标准格式提取: 未找到")

if __name__ == "__main__":
    test_regex_patterns()

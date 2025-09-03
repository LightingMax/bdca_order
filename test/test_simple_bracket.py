#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试【】提取逻辑
"""

import re

def test_bracket_extraction():
    """测试【】提取"""
    test_cases = [
        "【T3出行-77.06元-1个行程】*发票.pdf",
        "【阳光出行-32.13元-3个行程】*发票.pdf",
        "【高德打车-45.67元-2个行程】*发票.pdf",
        "【T3-77.06-1】*发票.pdf",
        "普通文件名.pdf"
    ]
    
    print("🧪 测试【】提取逻辑")
    print("=" * 50)
    
    for filename in test_cases:
        print(f"\n文件名: {filename}")
        
        # 提取【】内的内容
        bracket_pattern = r'【([^】]+)】'
        bracket_match = re.search(bracket_pattern, filename)
        
        if bracket_match:
            bracket_content = bracket_match.group(1)
            print(f"✅ 提取结果: {bracket_content}")
        else:
            print(f"❌ 未找到【】格式")

if __name__ == "__main__":
    test_bracket_extraction()

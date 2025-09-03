#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试订单ID提取逻辑
检查为什么没有正确提取【】内的内容
"""

import re
import os

def debug_extract_order_id(filename):
    """调试订单ID提取逻辑"""
    print(f"\n🔍 调试文件名: {filename}")
    
    # 方法0: 优先从发票文件名中提取【】内的内容
    print("📋 方法0: 检查【】格式")
    bracket_pattern = r'【([^】]+)】'
    bracket_match = re.search(bracket_pattern, filename)
    if bracket_match:
        bracket_content = bracket_match.group(1)
        print(f"   ✅ 找到【】内容: {bracket_content}")
        
        # 进一步解析【】内的内容
        # 格式：(T3出行-77.06元-1个行程)
        if bracket_content.startswith('(') and bracket_content.endswith(')'):
            inner_content = bracket_content[1:-1]  # 去掉括号
            print(f"   ✅ 【】内括号内容: {inner_content}")
            return inner_content
        else:
            print(f"   ✅ 【】内内容: {bracket_content}")
            return bracket_content
    else:
        print(f"   ❌ 未找到【】格式")
    
    # 方法1: 尝试从文件名中提取完整的订单信息
    print("📋 方法1: 检查标准格式")
    order_patterns = [
        r'([^-]+)-(\d+\.\d+)元?-(\d+)个行程',  # 阳光出行-32.13元-3个行程
        r'([^-]+)-(\d+\.\d+)-(\d+)',           # T3-77.06-1
        r'([^-]+)-(\d+\.\d+)',                 # 服务商-金额
        r'订单(\d+)',                           # 订单12345
        r'trip(\d+)',                           # trip001
    ]
    
    for i, pattern in enumerate(order_patterns):
        match = re.search(pattern, filename)
        if match:
            print(f"   ✅ 模式{i+1}匹配: {pattern}")
            if len(match.groups()) == 3:
                service, amount, count = match.groups()
                order_id = f"{service}-{amount}-{count}"
                print(f"   ✅ 提取结果: {order_id}")
                return order_id
            elif len(match.groups()) == 2:
                service, amount = match.groups()
                order_id = f"{service}-{amount}"
                print(f"   ✅ 提取结果: {order_id}")
                return order_id
            elif len(match.groups()) == 1:
                order_id = match.group(1)
                print(f"   ✅ 提取结果: {order_id}")
                return order_id
        else:
            print(f"   ❌ 模式{i+1}不匹配: {pattern}")
    
    # 方法2: 尝试查找6位以上的数字作为订单ID
    print("📋 方法2: 查找数字")
    order_id_match = re.search(r'(\d{6,})', filename)
    if order_id_match:
        order_id = order_id_match.group(1)
        print(f"   ✅ 找到数字订单ID: {order_id}")
        return order_id
    else:
        print(f"   ❌ 未找到6位以上数字")
    
    print(f"   ❌ 所有方法都失败，使用文件名: {filename}")
    return filename

def test_various_formats():
    """测试各种文件名格式"""
    test_cases = [
        # 发票文件名格式
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
        "unknown_file.pdf",
        
        # 实际可能遇到的格式
        "订单-53.21-1.pdf",  # 这是您提到的格式
        "T3-77.06-1.pdf",
        "YG-32.13-3.pdf"
    ]
    
    print("🧪 测试各种文件名格式的订单ID提取")
    print("=" * 80)
    
    results = []
    for i, filename in enumerate(test_cases, 1):
        print(f"\n{i}. 测试: {filename}")
        result = debug_extract_order_id(filename)
        results.append((filename, result))
        print(f"   最终结果: {result}")
    
    print("\n" + "=" * 80)
    print("📊 测试结果总结:")
    for filename, result in results:
        if '【' in filename and '】' in filename:
            if '【' in result or '】' in result:
                print(f"❌ {filename} -> {result} (【】未正确处理)")
            else:
                print(f"✅ {filename} -> {result} (【】正确处理)")
        else:
            print(f"📝 {filename} -> {result}")

if __name__ == "__main__":
    test_various_formats()

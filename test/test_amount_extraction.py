#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试金额提取功能
"""

import re
from pathlib import Path

def test_amount_extraction_from_filename():
    """测试从文件名提取金额的功能"""
    print("🧪 测试金额提取功能")
    print("=" * 50)
    
    # 测试文件名
    test_filenames = [
        "【优e出行-58.37元-1个行程】高德打车电子行程单.pdf",
        "【优e出行-58.37元-1个行程】高德打车电子发票.pdf",
        "【阳光出行-32.13元-3个行程】高德打车电子发票.pdf",
        "【T3出行-32.62元-1个行程】高德打车电子发票.pdf",
        "【曹操出行-19.85元-1个行程】高德打车电子发票.pdf",
        "【及时用车-28.86元-1个行程】高德打车电子发票.pdf",
        "【风韵出行-40.26元-2个行程】高德打车电子发票.pdf",
        "dzfp_25114000000003462819_杭州大数云智科技有限公司_20250831201746.pdf",
        "结账单20250831.pdf"
    ]
    
    # 当前的正则表达式模式
    current_patterns = [
        r'(\d+\.\d+)元',           # 匹配 58.37元
        r'-(\d+\.\d+)元?-',        # 匹配 -58.37元-
        r'-(\d+\.\d+)-',           # 匹配 -58.37-
    ]
    
    # 改进的正则表达式模式
    improved_patterns = [
        # 模式1: 【优e出行-58.37元-1个行程】
        r'【.*?-(\d+\.\d+)元-.*?】',
        # 模式2: 通用模式 - 任何包含"元"的格式
        r'(\d+\.\d+)元',
        # 模式3: 通用模式 - 数字.数字格式（在特定位置）
        r'-(\d+\.\d+)-',
        # 模式4: 通用模式 - 数字.数字格式（更宽松）
        r'(\d+\.\d+)',
    ]
    
    print("📋 测试当前的正则表达式模式:")
    print("-" * 30)
    for filename in test_filenames:
        print(f"\n文件名: {filename}")
        found_amount = False
        
        for i, pattern in enumerate(current_patterns):
            match = re.search(pattern, filename)
            if match:
                amount = float(match.group(1))
                print(f"  ✅ 模式{i+1} '{pattern}' 匹配成功: {amount}元")
                found_amount = True
                break
        
        if not found_amount:
            print(f"  ❌ 所有模式都未匹配")
    
    print("\n" + "=" * 50)
    print("📋 测试改进的正则表达式模式:")
    print("-" * 30)
    
    for filename in test_filenames:
        print(f"\n文件名: {filename}")
        found_amount = False
        
        for i, pattern in enumerate(improved_patterns):
            match = re.search(pattern, filename)
            if match:
                amount = float(match.group(1))
                # 验证金额合理性
                if 1.0 <= amount <= 1000.0:
                    print(f"  ✅ 模式{i+1} '{pattern}' 匹配成功: {amount}元")
                    found_amount = True
                    break
                else:
                    print(f"  ⚠️ 模式{i+1} '{pattern}' 匹配到金额 {amount}元，但超出合理范围")
        
        if not found_amount:
            print(f"  ❌ 所有模式都未匹配")

def test_extract_amount_from_filename_function():
    """测试新的extract_amount_from_filename函数"""
    print("\n" + "=" * 50)
    print("🧪 测试新的extract_amount_from_filename函数:")
    print("-" * 30)
    
    # 模拟新的函数逻辑
    def extract_amount_from_filename(filename):
        """从文件名中提取金额 - 支持网约车和酒店文件"""
        try:
            # 网约车文件名金额提取模式（优先级从高到低）
            ride_patterns = [
                # 模式1: 【优e出行-58.37元-1个行程】高德打车电子发票.pdf
                r'【.*?-(\d+\.\d+)元-.*?】',
                # 模式2: 通用模式 - 任何包含"元"的格式
                r'(\d+\.\d+)元',
                # 模式3: 通用模式 - 数字.数字格式（在特定位置）
                r'-(\d+\.\d+)-',
                # 模式4: 通用模式 - 数字.数字格式（更宽松）
                r'(\d+\.\d+)',
            ]
            
            # 酒店文件名金额提取模式
            hotel_patterns = [
                r'(\d+\.\d+)元',
                r'-(\d+\.\d+)-',
            ]
            
            # 首先尝试网约车模式
            for pattern in ride_patterns:
                match = re.search(pattern, filename)
                if match:
                    amount = float(match.group(1))
                    # 验证金额合理性（1-1000元，网约车通常在这个范围）
                    if 1.0 <= amount <= 1000.0:
                        print(f"  ✅ 网约车模式 '{pattern}' 匹配成功: {amount}元")
                        return amount
            
            # 如果网约车模式失败，尝试酒店模式
            for pattern in hotel_patterns:
                match = re.search(pattern, filename)
                if match:
                    amount = float(match.group(1))
                    # 验证金额合理性（1-10000元，酒店可能更贵）
                    if 1.0 <= amount <= 10000.0:
                        print(f"  ✅ 酒店模式 '{pattern}' 匹配成功: {amount}元")
                        return amount
            
            print(f"  ❌ 无法从文件名中提取金额")
            return 0
            
        except Exception as e:
            print(f"  ❌ 从文件名提取金额时出错: {e}")
            return 0
    
    # 测试文件名
    test_filenames = [
        "【优e出行-58.37元-1个行程】高德打车电子行程单.pdf",
        "【优e出行-58.37元-1个行程】高德打车电子发票.pdf",
        "【阳光出行-32.13元-3个行程】高德打车电子发票.pdf",
        "【T3出行-32.62元-1个行程】高德打车电子发票.pdf",
        "【曹操出行-19.85元-1个行程】高德打车电子发票.pdf",
        "【及时用车-28.86元-1个行程】高德打车电子发票.pdf",
        "【风韵出行-40.26元-2个行程】高德打车电子发票.pdf",
        "dzfp_25114000000003462819_杭州大数云智科技有限公司_20250831201746.pdf",
        "结账单20250831.pdf"
    ]
    
    for filename in test_filenames:
        print(f"\n文件名: {filename}")
        amount = extract_amount_from_filename(filename)
        if amount > 0:
            print(f"  🎯 最终提取金额: {amount}元")
        else:
            print(f"  ❌ 未能提取到金额")

if __name__ == "__main__":
    test_amount_extraction_from_filename()
    test_extract_amount_from_filename_function()

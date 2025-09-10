#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试发票查找功能
"""

import os
import sys
import re
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def identify_pdf_type(filename):
    """识别PDF类型（发票/行程单）"""
    if '发票' in filename:
        return 'invoice'
    elif '行程单' in filename:
        return 'itinerary'
    else:
        return 'unknown'

def find_corresponding_invoice_test(itinerary_path):
    """测试发票查找功能"""
    try:
        # 从行程单文件名中提取订单信息
        filename = os.path.basename(itinerary_path)
        print(f"🔍 查找行程单对应的发票: {filename}")
        
        # 提取订单ID或关键信息
        order_patterns = [
            r'(\d+个行程)',           # 高德打车：2个行程
            r'(订单\d+)',             # 通用订单格式
            r'(trip\d+)',             # 英文trip格式
            r'(\d+\.\d+元)',          # 金额格式：53.21元
            r'(\d+-\d+)',             # 数字-数字格式
            r'([A-Za-z0-9]{8,})',    # 8位以上字母数字组合
        ]
        
        order_key = None
        for pattern in order_patterns:
            match = re.search(pattern, filename)
            if match:
                order_key = match.group(1)
                print(f"🔑 提取到订单标识: {order_key}")
                break
        
        if not order_key:
            print(f"⚠️ 无法从文件名提取订单标识: {filename}")
            order_key = filename.split('.')[0]  # 去掉扩展名
            print(f"🔑 使用文件名作为订单标识: {order_key}")
        
        # 搜索目录
        search_dirs = [
            "temp",                                    # Flask临时目录
            "app/static/uploads",                       # Flask上传目录
            "app/static/outputs",                       # Flask输出目录
            "temp_files",                               # 其他临时目录
        ]
        
        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                print(f"⚠️ 目录不存在: {search_dir}")
                continue
                
            print(f"🔍 在目录中搜索发票: {search_dir}")
            
            # 递归搜索PDF文件
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    if file.endswith('.pdf'):
                        file_lower = file.lower()
                        
                        # 检查是否是发票文件
                        is_invoice = any(keyword in file_lower for keyword in [
                            '发票', 'invoice', 'receipt', 'bill', '电子发票'
                        ])
                        
                        if is_invoice:
                            print(f"  📄 找到发票文件: {file}")
                            # 检查是否包含订单标识
                            if order_key in file:
                                invoice_path = os.path.join(root, file)
                                print(f"✅ 找到对应发票: {invoice_path}")
                                return invoice_path
                            else:
                                print(f"  ⚠️ 发票文件不包含订单标识: {file}")
        
        print(f"❌ 未找到对应的发票文件，订单标识: {order_key}")
        return None
        
    except Exception as e:
        print(f"❌ 查找对应发票失败: {e}")
        return None

def main():
    """主测试函数"""
    print("🧪 测试发票查找功能")
    print("=" * 50)
    
    # 测试文件路径
    test_itinerary = "temp/46b9918f-d733-4f37-bce1-01657eca819e/extracted/zip/高德打车电子发票 (1)/【及时用车-53.21元-2个行程】高德打车电子行程单.pdf"
    
    if os.path.exists(test_itinerary):
        print(f"✅ 测试文件存在: {test_itinerary}")
        invoice_path = find_corresponding_invoice_test(test_itinerary)
        
        if invoice_path:
            print(f"\n🎉 测试成功！找到发票: {invoice_path}")
        else:
            print(f"\n❌ 测试失败！未找到发票")
    else:
        print(f"❌ 测试文件不存在: {test_itinerary}")
        print("请先上传ZIP文件到网页")

if __name__ == "__main__":
    main()

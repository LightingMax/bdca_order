#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试XML文件缺失时的金额提取修复
"""

import re
from pathlib import Path

def extract_amount_from_pdf(pdf_path):
    """从PDF文件中提取金额（轻量级方法）"""
    try:
        # 首先尝试从文件名提取金额
        filename = Path(pdf_path).name
        amount_match = re.search(r'(\d+\.\d+)元', filename)
        if not amount_match:
            amount_match = re.search(r'-(\d+\.\d+)元?-', filename)
        if not amount_match:
            amount_match = re.search(r'-(\d+\.\d+)-', filename)
            
        if amount_match:
            amount = float(amount_match.group(1))
            print(f"  ✅ 从PDF文件名中提取到金额: {amount}元")
            return amount
        
        print(f"  ❌ 无法从PDF文件名提取金额")
        return 0
        
    except Exception as e:
        print(f"  ❌ 从PDF文件提取金额时出错: {e}")
        return 0

def test_xml_missing_scenario():
    """测试XML文件缺失场景"""
    print("🧪 测试XML文件缺失时的金额提取修复")
    print("=" * 60)
    
    # 模拟XML文件缺失的网约车订单
    test_orders = {
        "优e出行-58.37元-1个行程": {
            'xml': None,  # XML文件缺失
            'amount': 0,  # 初始金额为0
            'pdfs': {
                'invoice': '【优e出行-58.37元-1个行程】高德打车电子发票.pdf',
                'itinerary': '【优e出行-58.37元-1个行程】高德打车电子行程单.pdf'
            }
        },
        "阳光出行-32.13元-3个行程": {
            'xml': None,  # XML文件缺失
            'amount': 0,  # 初始金额为0
            'pdfs': {
                'invoice': '【阳光出行-32.13元-3个行程】高德打车电子发票.pdf',
                'itinerary': '【阳光出行-32.13元-3个行程】高德打车电子行程单.pdf'
            }
        },
        "T3出行-32.62元-1个行程": {
            'xml': None,  # XML文件缺失
            'amount': 0,  # 初始金额为0
            'pdfs': {
                'invoice': '【T3出行-32.62元-1个行程】高德打车电子发票.pdf',
                'itinerary': '【T3出行-32.62元-1个行程】高德打车电子行程单.pdf'
            }
        }
    }
    
    print("📋 修复前的订单状态:")
    for order_id, order_data in test_orders.items():
        print(f"\n订单ID: {order_id}")
        print(f"  XML文件: {'存在' if order_data['xml'] else '缺失'}")
        print(f"  当前金额: {order_data['amount']}元")
        print(f"  发票文件: {order_data['pdfs']['invoice']}")
        print(f"  行程单文件: {order_data['pdfs']['itinerary']}")
    
    print("\n" + "=" * 60)
    print("🔧 应用修复逻辑:")
    print("-" * 30)
    
    xml_missing_warnings = []
    
    for order_id, order_data in test_orders.items():
        print(f"\n处理订单: {order_id}")
        
        if order_data['xml'] is None:
            # XML文件缺失时，尝试从PDF文件名中提取金额
            print(f"  🔍 网约车订单 {order_id} 缺少XML文件，尝试从PDF文件名提取金额")
            
            # 尝试从发票PDF文件名提取金额
            if order_data['pdfs'].get('invoice'):
                print(f"  📄 尝试从发票文件名提取金额: {order_data['pdfs']['invoice']}")
                invoice_amount = extract_amount_from_pdf(order_data['pdfs']['invoice'])
                if invoice_amount > 0:
                    order_data['amount'] = invoice_amount
                    print(f"  ✅ 从发票文件名成功提取金额: {invoice_amount}元")
                else:
                    # 如果发票文件名提取失败，尝试从行程单文件名提取
                    if order_data['pdfs'].get('itinerary'):
                        print(f"  📄 尝试从行程单文件名提取金额: {order_data['pdfs']['itinerary']}")
                        itinerary_amount = extract_amount_from_pdf(order_data['pdfs']['itinerary'])
                        if itinerary_amount > 0:
                            order_data['amount'] = itinerary_amount
                            print(f"  ✅ 从行程单文件名成功提取金额: {itinerary_amount}元")
            
            # 如果仍然没有提取到金额，记录警告
            if order_data['amount'] == 0:
                xml_missing_warnings.append({
                    'order_id': order_id,
                    'reason': 'XML文件缺失且无法从PDF文件名提取金额',
                    'impact': '金额统计为0，可能不准确',
                    'type': 'taxi'
                })
                print(f"  ⚠️ 网约车订单 {order_id} 缺少XML文件且无法从PDF文件名提取金额")
            else:
                print(f"  ✅ 网约车订单 {order_id} 从PDF文件名成功提取金额: {order_data['amount']}元")
    
    print("\n" + "=" * 60)
    print("📊 修复后的订单状态:")
    print("-" * 30)
    
    total_amount = 0
    for order_id, order_data in test_orders.items():
        print(f"\n订单ID: {order_id}")
        print(f"  XML文件: {'存在' if order_data['xml'] else '缺失'}")
        print(f"  最终金额: {order_data['amount']}元")
        total_amount += order_data['amount']
    
    print(f"\n📈 统计结果:")
    print(f"  总订单数: {len(test_orders)}")
    print(f"  总金额: {total_amount}元")
    print(f"  XML缺失警告数: {len(xml_missing_warnings)}")
    
    if xml_missing_warnings:
        print(f"\n⚠️ XML缺失警告:")
        for warning in xml_missing_warnings:
            print(f"  - {warning['order_id']}: {warning['reason']}")

if __name__ == "__main__":
    test_xml_missing_scenario()

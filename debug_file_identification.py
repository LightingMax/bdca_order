#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试文件识别问题
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def debug_file_identification():
    """调试文件识别问题"""
    print("🔍 调试文件识别问题...")
    
    # 测试目录
    test_dir = Path("temp_files/extracted_test/高德打车电子发票 (1)")
    
    if not test_dir.exists():
        print(f"❌ 测试目录不存在: {test_dir}")
        return False
    
    try:
        from print_api_service_linux_enhanced import identify_pdf_type, find_corresponding_invoice
        
        # 遍历测试文件
        for pdf_file in test_dir.glob("*.pdf"):
            print(f"\n📄 测试文件: {pdf_file.name}")
            print(f"   完整路径: {pdf_file.absolute()}")
            
            # 逐步分析文件名识别
            filename = pdf_file.name
            filename_lower = filename.lower()
            print(f"   文件名(小写): {filename_lower}")
            
            # 检查关键词
            keywords_invoice = ['发票', 'invoice', 'receipt', 'bill']
            keywords_itinerary = ['行程', 'itinerary', 'trip', '订单']
            
            print(f"   发票关键词检查:")
            for keyword in keywords_invoice:
                if keyword in filename_lower:
                    print(f"     ✅ 包含 '{keyword}'")
                else:
                    print(f"     ❌ 不包含 '{keyword}'")
            
            print(f"   行程关键词检查:")
            for keyword in keywords_itinerary:
                if keyword in filename_lower:
                    print(f"     ✅ 包含 '{keyword}'")
                else:
                    print(f"     ❌ 不包含 '{keyword}'")
            
            # 调用函数识别
            pdf_type = identify_pdf_type(str(pdf_file))
            print(f"   函数识别结果: {pdf_type}")
            
            # 如果是行程单，查找对应发票
            if pdf_type == 'itinerary':
                print(f"   🔍 查找对应发票...")
                invoice_path = find_corresponding_invoice(str(pdf_file))
                if invoice_path:
                    print(f"   ✅ 找到发票: {os.path.basename(invoice_path)}")
                else:
                    print(f"   ❌ 未找到对应发票")
            elif pdf_type == 'invoice':
                print(f"   🧾 这是发票文件")
            else:
                print(f"   ❓ 未知类型")
                
        return True
        
    except ImportError as e:
        print(f"❌ 导入函数失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🚀 调试文件识别问题")
    print("=" * 60)
    
    success = debug_file_identification()
    
    if success:
        print("\n🎉 调试完成！")
    else:
        print("\n❌ 调试失败！")

if __name__ == "__main__":
    main()

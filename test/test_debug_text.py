#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试PDF文本提取
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz  # PyMuPDF

def debug_pdf_text():
    """调试PDF文本内容"""
    test_file = "temp_files/【高德打车-144.56元-3个行程】高德打车电子行程单.pdf"
    
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return
    
    print(f"🧪 调试PDF文本内容")
    print(f"📁 测试文件: {test_file}")
    print("=" * 60)
    
    try:
        doc = fitz.open(test_file)
        
        if len(doc) == 0:
            print("❌ PDF文件没有页面")
            doc.close()
            return
        
        full_text = ""
        for page_num in range(len(doc)):
            try:
                page = doc.load_page(page_num)
                page_text = page.get_text()
                if page_text:
                    full_text += page_text + "\n"
            except Exception as e:
                print(f"⚠️ 提取第{page_num+1}页文本失败: {e}")
                continue
        
        doc.close()
        
        print(f"📄 提取的文本内容:")
        print("-" * 40)
        print(full_text)
        print("-" * 40)
        
        # 分析文本行
        lines = full_text.split('\n')
        print(f"\n📊 文本分析:")
        print(f"总行数: {len(lines)}")
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line:  # 只显示非空行
                print(f"第{i+1:2d}行: '{line}'")
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_pdf_text()
